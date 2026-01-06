# Full Pipeline (Scheme) — Kafka → Spark → Inference → Alerts → API

本目录提供“按 `scheme/` 方案的全链路可运行实现”，把你已经训练好的模型（`label&train/output/artifacts/`）接入在线链路，完成：

1) 回放器把日志（已合并多行）写入 Kafka `openstack.raw`  
2) Spark Structured Streaming 消费 `openstack.raw`，做解析/模板化/窗口聚合，产出 `openstack.features`  
3) FastAPI 内置 Worker 消费 `openstack.features`，加载离线模型推理，生成告警写入 SQLite  
4) 通过 HTTP API 查询告警（前端可按需接入）

说明：为了与离线特征一致，本链路使用与 `label&train/openstack_log_pipeline.py` 同风格的解析/模板化，并在特征里输出 `template_counts`、`error_cnt`、`error_ratio`、`keyword_counts` 等。

---

## 0. 目录结构

- `pipeline/docker-compose.yml`：Kafka + Spark + FastAPI(含Worker) + SQLite 数据卷
- `pipeline/replayer/replay_to_kafka.py`：日志回放器（合并多行后发送）
- `pipeline/streaming/openstack_streaming_job.py`：Spark Structured Streaming 任务（raw → features）
- `pipeline/service/requirements-service.txt`：后端服务依赖（容器内 pip install）
- `pipeline/service/service/app.py`：FastAPI API 服务（启动时会拉起 Worker）
- `pipeline/service/service/worker.py`：Kafka features 消费 + 模型推理 + 告警落库
- `pipeline/service/service/db.py`：SQLite/SQLAlchemy
- `pipeline/service/service/model.py`：加载离线模型 + 特征一致性
- `pipeline/full_pipeline.md`：更详细的全链路说明书（架构/原理/Schema/运行步骤）

---

## 1. 前置条件

- Docker + Docker Compose
- 你的离线模型工件已经生成：
  - `label&train/output/artifacts/model.joblib`
  - `label&train/output/artifacts/vectorizer.joblib`
  - `label&train/output/artifacts/label_map.json`

---

## 2. 一键启动（Docker Compose）

在仓库根目录执行：

```bash
docker compose -f pipeline/docker-compose.yml up -d
```

检查服务：

```bash
docker compose -f pipeline/docker-compose.yml ps
```

默认启用 MariaDB（用于告警库）；可选启用 Hadoop(HDFS)：

```bash
docker compose -f pipeline/docker-compose.yml --profile hadoop up -d
```

MariaDB 默认配置：
- host: `localhost:13306`（容器内为 `mariadb:3306`）
- db/user/password: `aiops/aiops/aiops`

---

## 3. 创建 Kafka Topics

默认使用三个 topic：
- `openstack.raw`
- `openstack.features`
- `openstack.alerts`（Worker 推理后“同步广播”的告警流，便于后续扩展）

`pipeline/docker-compose.yml` 已内置 `kafka-init`，启动 compose 后会自动创建；也可以手动创建：

```bash
docker compose -f pipeline/docker-compose.yml exec kafka kafka-topics --bootstrap-server kafka:9092 --create --if-not-exists --topic openstack.raw --partitions 3 --replication-factor 1
docker compose -f pipeline/docker-compose.yml exec kafka kafka-topics --bootstrap-server kafka:9092 --create --if-not-exists --topic openstack.features --partitions 3 --replication-factor 1
docker compose -f pipeline/docker-compose.yml exec kafka kafka-topics --bootstrap-server kafka:9092 --create --if-not-exists --topic openstack.alerts --partitions 3 --replication-factor 1
docker compose -f pipeline/docker-compose.yml exec kafka kafka-topics --bootstrap-server kafka:9092 --list
```

---

## 4. 启动 Spark Streaming 任务（raw → features）

此任务会在 Spark 里消费 `openstack.raw`，解析/模板化并按窗口聚合，产出到 `openstack.features`。

默认情况下，`pipeline/docker-compose.yml` 已包含 `spark-streaming` 服务，会自动运行该任务；你只需确认它在运行：

```bash
docker compose -f pipeline/docker-compose.yml ps spark-streaming
docker compose -f pipeline/docker-compose.yml logs -f spark-streaming
```

如果需要手动启动/重跑（一般不需要），可执行（注意：首次运行会通过 Maven 下载依赖，需要容器能联网）：

```bash
docker compose -f pipeline/docker-compose.yml exec spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.3,org.apache.spark:spark-token-provider-kafka-0-10_2.12:3.5.3 /opt/pipeline/streaming/openstack_streaming_job.py --bootstrap kafka:9092 --raw-topic openstack.raw --features-topic openstack.features --window 60 --slide 30 --checkpoint /tmp/checkpoints/openstack_streaming_job
```

如果启用了 HDFS（`--profile hadoop`），`spark-streaming` 会自动探测 `namenode:8020` 并启用 Parquet 落地；也可以手动指定：

```bash
docker compose -f pipeline/docker-compose.yml exec spark-master /opt/spark/bin/spark-submit --master spark://spark-master:7077 --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.3,org.apache.spark:spark-token-provider-kafka-0-10_2.12:3.5.3 /opt/pipeline/streaming/openstack_streaming_job.py --bootstrap kafka:9092 --raw-topic openstack.raw --features-topic openstack.features --window 60 --slide 30 --checkpoint /tmp/checkpoints/openstack_streaming_job --hdfs-records-path hdfs://namenode:8020/data/openstack/records --hdfs-features-path hdfs://namenode:8020/data/openstack/features
```

备注：`--packages ...` 首次会从 Maven 下载依赖（需要容器能联网）。如果你所在网络受限，可以改成把 jar 预置到镜像里（后续我也可以帮你做“离线 jar 镜像”版）。

---

## 5. 回放日志进 Kafka（模拟在线）

本项目提供两种回放方式：

### 5.1 方式 A：通过后端控制接口（推荐）

后端已内置回放器（`/control/*`），并在 `pipeline/docker-compose.yml` 中将仓库根目录挂载为只读目录，可直接回放这些日志：

可直接用前端欢迎页点击「开始」，或用 curl：

```bash
curl -X POST "http://localhost:8000/control/start" -H "Content-Type: application/json" -d '{"dataset_id":"sample","rate":80,"loop":false,"max_records":0}'
```

查看状态 / 停止：

```bash
curl "http://localhost:8000/control/status"
curl -X POST "http://localhost:8000/control/stop"
```

注意：回放只负责写入 `openstack.raw`；仍需先启动 Spark Streaming（第 4 节）才能产生 `openstack.features` 并触发告警。

### 5.2 方式 B：使用独立回放脚本（可选）

在宿主机（你的 conda 环境）执行（先安装回放器依赖）：

```bash
pip install -r pipeline/replayer/requirements-replayer.txt
```

然后回放：

```bash
python pipeline/replayer/replay_to_kafka.py --bootstrap localhost:29092 --topic openstack.raw --dataset sample --log openstack-nova-sample.log --rate 200
```

参数说明：
- `--rate`：每秒发送的“合并后记录数”（不是原始行数）

---

## 6. FastAPI 查询告警

FastAPI 在 compose 中默认暴露 `http://localhost:8000`：

```bash
curl http://localhost:8000/health
curl "http://localhost:8000/alerts?limit=20"
curl "http://localhost:8000/metrics/overview?minutes=15"
```

查看某条告警详情：

```bash
curl "http://localhost:8000/alerts/<alert_id>"
```

告警闭环（确认/关闭/评论，可用于答辩演示）：

```bash
curl -X POST "http://localhost:8000/alerts/<alert_id>/ack" -H "Content-Type: application/json" -d '{"comment":"已确认，开始排查"}'
curl -X POST "http://localhost:8000/alerts/<alert_id>/close" -H "Content-Type: application/json" -d '{"comment":"已恢复，关闭告警"}'
```

实时推送（SSE，前端已自动订阅；也可用 curl 看连接是否成功）：

```bash
curl -N "http://localhost:8000/events/alerts"
```

---

## 6.1 前端看板（Vue + DevUI + vue-data-ui）

前端位于 `pipeline/frontend/`，默认通过 Vite 代理对接后端：

```bash
cd pipeline/frontend
bun install
bun run dev
```

- 前端默认请求 `GET /api/alerts`（Vite 会转发到 `http://localhost:8000/alerts`）
- 也可以在页面右上角「设置」里把 `API Base URL` 改成 `http://localhost:8000` 直连后端

---

## 7. 原理（严谨版，答辩可用）

### 7.1 为什么要“模板化”

OpenStack 日志里大量变量（UUID/IP/MAC/路径/长数字）会导致同一类事件产生海量不同的“表面文本”，直接用原文会让特征空间极度稀疏、泛化差。模板化的目标是把：

- `instance: 6db...`、`10.0.0.12`、`/var/lib/nova/...`  
归一化为：
- `<UUID>`、`<IPV4>`、`<PATH>`

从而把“同类型事件”映射到稳定的 `template_id`，实现：

1) 特征可泛化（跨实例/跨运行）  
2) Top 模板可解释（“症状模板”）  

### 7.2 监督分类为何可解释

离线训练时，模型输入是“模板计数向量（Bag-of-Templates）+ 错误强度特征（error_cnt/error_ratio）+ 关键词计数”，模型学习的是：

- 某些模板/关键词组合更倾向于某个故障类
- ERROR/WARN 强度分布对故障类有区分度

在线推理时输出：

- `pred_class`：预测故障类型  
- `prob`：置信度  
- `evidence`：窗口 Top 模板 + 若干条 ERROR 记录（可追溯）  

这就是“从日志到告警”的可解释闭环。

---

## 8. 常见问题

### Q1：为什么在线用 `ingest_ts` 做窗口，而不是日志里的时间？

因为很多 OpenStack 日志样例未必带统一/可靠的时间戳，且离线训练不依赖时间戳。在线演示使用回放写入时刻 `ingest_ts` 可获得稳定的窗口边界，适合演示实时链路。

### Q2：窗口分类与离线“按 instance 聚合”特征不完全一致，会影响效果吗？

会有影响，但在演示场景下通常仍能稳定触发故障告警，因为关键故障模板/关键词往往在一个较短窗口内就会出现。若你希望严格一致，可以把 Spark 侧改为“按 instance 的累积状态聚合”（需要 stateful 设计）。
