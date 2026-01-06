# Scheme 全链路说明书（可直接写进报告/答辩）

本说明书对应 `pipeline/` 下的全链路实现，目标是把离线训练产物（`label&train/output/artifacts/`）接入在线链路，实现“回放 → 流式特征 → 在线推理 → 告警落库 → API 查询”的闭环。

---

## 1. 总体架构与数据流

**数据流（端到端）**：

1) `replay_to_kafka.py` 读取 `.log`，先做**多行合并**（Traceback/XML 等），每条“合并后记录”写入 Kafka `openstack.raw`  
2) `openstack_streaming_job.py`（Spark Structured Streaming）消费 `openstack.raw`：
   - 解析 `level/component/request_id/instance_id`
   - 归一化/模板化得到 `template_id`
   - 以 `entity_key`（优先 instance_id）进行窗口聚合统计特征
   - 把窗口特征写入 Kafka `openstack.features`
3) FastAPI 服务启动时同时启动 `InferenceWorker`：
   - 消费 `openstack.features`
   - 加载 `label&train/output/artifacts/model.joblib + vectorizer.joblib`
   - 推理得到 `pred_class + prob`
   - 按阈值触发告警，写入 SQLite
4) API 提供：
   - `/alerts` 告警列表
   - `/alerts/{id}` 告警详情（含 evidence，可用于前端展示）

---

## 2. 关键设计点（原理 + 工程原因）

### 2.1 多行合并（必须）

OpenStack/Nova 日志常出现多行块（Traceback、domain XML、长 dump）。如果逐行进入流式处理，会导致：

- 模板化被连续“脏行”污染（同一 traceback 会产生大量无意义模板）
- 统计特征膨胀（total_records、error_cnt 失真）
- 告警证据难以回溯（一条错误被拆散）

因此回放阶段先做合并：以 `^(DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL)`（忽略前导空格）作为新记录起点，其余行拼接到上一条记录。

### 2.2 模板化（提升泛化 + 可解释）

模板化把 UUID/IP/MAC/路径/长数字替换为占位符，然后对归一化消息做 hash 得到 `template_id`：

- 把“可变参数”从特征中移除，减少稀疏噪声
- `template_id` 可作为“事件模板”，TopK 模板可解释（症状证据）

本实现与离线训练保持一致（规则见 `label&train/openstack_log_pipeline.py` 与 `pipeline/streaming/openstack_streaming_job.py`）。

### 2.3 窗口聚合（把日志序列变成可学习样本）

模型并非对“单条日志”判断故障，而是对一个窗口（window）内的统计特征判断：

- `template_counts`：模板计数（核心）
- `error_cnt/warn_cnt/info_cnt/total_records`
- `error_ratio = error_cnt / total_records`
- `keyword_counts`：关键短语计数（辅助）
- `error_examples`：窗口内 ERROR 证据（用于前端详情）

这样告警不仅有“预测类别”，还有“证据模板与 ERROR 原文”。

### 2.4 在线推理（与离线特征一致）

在线推理必须复用离线同一套特征定义，否则就是**特征漂移**，线上效果会崩。

本实现复用了训练时的 feature 字段命名（`tpl_...`、`kw_...`、`error_cnt`、`error_ratio`、`log_error_cnt` 等），并直接加载：

- `model.joblib`：`LogisticRegression(multinomial)`
- `vectorizer.joblib`：`DictVectorizer`

### 2.5 告警阈值 + 去重（工程必需）

规则：

- `pred_label_id != 0` 且 `prob >= threshold` 触发告警
- 去重：同一 `(entity_key, pred_label_id)` 在 `dedup_ttl_sec` 内只产生一次告警（避免刷屏）

阈值由环境变量 `APP_ALERT_THRESHOLD` 控制（默认 0.7）。

---

## 3. 消息格式（Topic Schema）

### 3.1 `openstack.raw`

回放器写入，JSON 字段：

- `dataset_id`：`sample`（或 normal/fault1/fault2/fault3）
- `ingest_ts`：回放写入时间（毫秒），作为 Spark 的事件时间
- `start_line_no` / `end_line_no`：合并记录在源文件中的行号范围
- `raw_record`：合并后的原始文本（可能包含 `\n`）

### 3.2 `openstack.features`

Spark 输出，JSON 字段：

- `entity_key`
- `dataset_id`
- `window_start` / `window_end`
- `template_counts`：`{template_id: count}`
- `keyword_counts`：`{keyword: count}`
- `top_templates`：Top10 模板 id
- `error_examples`：最多 5 条 ERROR 原文片段（含行号）
- `error_cnt/warn_cnt/info_cnt/total_records/error_ratio`

### 3.3 `openstack.alerts`

Worker 输出，JSON 字段（与 `/alerts` API 一致）：

- `alert_id/created_at`
- `entity_key/window_start/window_end`
- `pred_class/pred_label_id/prob/threshold`
- `severity/status`
- `evidence`（JSON）

---

## 4. 存储（SQLite）

表：`alerts`

- `alert_id`：主键（由 `entity_key + window_end + pred_id` hash）
- `created_at`
- `entity_key/window_start/window_end`
- `pred_class/pred_label_id/prob/threshold`
- `severity/status`
- `evidence`（JSON：top_templates/template_counts/error_examples/...）

---

## 5. 运行步骤（最小可复现）

1) 启动基础设施：

```bash
docker compose -f pipeline/docker-compose.yml up -d
```

可选：启动 Hadoop(HDFS) 持久化（用于落 Parquet）：

```bash
docker compose -f pipeline/docker-compose.yml --profile hadoop up -d
```

2) Kafka topics（自动创建）：

`pipeline/docker-compose.yml` 已包含 `kafka-init`，启动 compose 后会自动创建并校验：
- `openstack.raw`
- `openstack.features`
- `openstack.alerts`

> 注意：`kafka-init` 是一次性初始化容器，创建 topic 后会以 `Exited (0)` 结束（正常现象），Kafka Broker 容器本身应保持 `Up`。

你也可以手动验证：

```bash
docker compose -f pipeline/docker-compose.yml exec kafka kafka-topics --bootstrap-server kafka:9092 --list
```

3) Spark Streaming（raw→features）（自动运行）：

`pipeline/docker-compose.yml` 已包含 `spark-streaming` 服务，默认会自动运行：

```bash
docker compose -f pipeline/docker-compose.yml ps spark-streaming
docker compose -f pipeline/docker-compose.yml logs -f spark-streaming
```

如果启用了 Hadoop profile（HDFS），`spark-streaming` 会自动探测 `namenode:8020` 并把明细与窗口特征写入 HDFS（Parquet）：

> 注意：Hadoop profile 会启动 `hdfs-init`（一次性初始化容器）创建 `/tmp/openstack/*` 并设置权限；完成后会以 `Exited (0)` 结束（正常现象），NameNode/DataNode 容器本身应保持 `Up`。

默认落地路径：

- `hdfs://namenode:8020/tmp/openstack/records`
- `hdfs://namenode:8020/tmp/openstack/features`

如需手动重跑（一般不需要；且首次运行会下载 Spark Kafka connector，容器需能联网）：

```bash
docker compose -f pipeline/docker-compose.yml exec spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.3,org.apache.spark:spark-token-provider-kafka-0-10_2.12:3.5.3 /opt/pipeline/streaming/openstack_streaming_job.py --bootstrap kafka:9092 --raw-topic openstack.raw --features-topic openstack.features --window 60 --slide 30 --checkpoint /tmp/checkpoints/openstack_streaming_job --hdfs-records-path hdfs://namenode:8020/tmp/openstack/records --hdfs-features-path hdfs://namenode:8020/tmp/openstack/features
```

4) 回放日志（写入 `openstack.raw`）：

- **方式 A（推荐）**：通过后端控制接口（也可在前端欢迎页点击「开始」）：

```bash
curl -X POST "http://localhost:8000/control/start" -H "Content-Type: application/json" -d '{"dataset_id":"sample","rate":80,"loop":false,"max_records":0}'
```

- **方式 B（可选）**：使用独立回放脚本：

```bash
pip install -r pipeline/replayer/requirements-replayer.txt

python pipeline/replayer/replay_to_kafka.py --bootstrap localhost:29092 --topic openstack.raw --dataset sample --log openstack-nova-sample.log --rate 200
```

5) 查告警：

```bash
curl http://localhost:8000/health
curl "http://localhost:8000/alerts?limit=20"
```

---

## 6. 调参建议（用于演示）

- `--rate`（回放速度）：200～500 records/s 适合演示吞吐
- `--window/--slide`（Spark）：60s/30s 是折中；想更快触发告警可用 30s/10s
- `APP_ALERT_THRESHOLD`：0.6（更敏感）～0.8（更保守）
- `APP_DEDUP_TTL_SEC`：300（5min）避免刷屏
