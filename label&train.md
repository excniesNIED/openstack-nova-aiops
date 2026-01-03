# OpenStack 日志：标注 & 训练方案（面向 4 类场景）

> 目标：按照现有方案（“日志解析 → 模板化 → 窗口/实体聚合特征 → 监督分类 → 告警阈值”），对以下 4 份日志进行**可复现的标注与训练**，产出可用于在线推理的模型与配套工件。
>
> - `openstack-nova-normal-vm-create.log`
> - `openstack-vm-destroy-immediately-after-create.log`
> - `openstack-nova-dhcpoff.log`
> - `openstack-nova-undefine-vm-after-create.log`
>
> 备注：`openstack-nova-sample.log` 更适合作为“在线回放/演示数据”，不强制参与离线监督训练与指标计算。

---

## 1. 标签体系（Label Schema）

### 1.1 类别定义（4 类）

| label_id | label_name | 语义解释 | 典型日志特征（可用于人工验收/弱标注辅助） |
|---:|---|---|---|
| 0 | `normal` | 正常创建虚拟机流程 | `Instance spawned successfully`、`Took X seconds to build instance` 且无 ERROR/BuildAbort |
| 1 | `fault_vm_destroy_after_create` | 创建后立即失败/中止并触发销毁（构建/资源失败导致 abort） | `FlavorDiskSmallerThanImage`、`BuildAbortException`、`Instance failed to spawn`、`Terminating instance` |
| 2 | `fault_network_dhcpoff` | 网络/DHCP 相关导致端口/网卡创建失败 | `VirtualInterfaceCreateException`、`Failed to allocate network(s)` |
| 3 | `fault_libvirt_domain_undefine` | libvirt/qemu 相关：已定义 domain 但启动失败/异常退出（或 domain 相关异常） | `qemu unexpectedly closed the monitor`、`Failed to start libvirt guest`、`Error launching a defined domain` |

### 1.2 文件到标签的映射（本次标注的“强标签”来源）

> **强约定**：同一个文件属于同一故障场景（强标签），该文件内抽取的窗口/实体样本默认继承该标签。

| 文件 | dataset_id | label_id |
|---|---|---:|
| `openstack-nova-normal-vm-create.log` | `normal` | 0 |
| `openstack-vm-destroy-immediately-after-create.log` | `fault1` | 1 |
| `openstack-nova-dhcpoff.log` | `fault2` | 2 |
| `openstack-nova-undefine-vm-after-create.log` | `fault3` | 3 |

---

## 2. 标注粒度与数据集形态（推荐：按 instance_id 聚合 + 可选滑窗增强）

现有方案主线是“窗口聚合特征 → 监督分类”。在这 4 份日志中，**`instance_id` 非常丰富**，可以天然作为 `entity_key`，得到更稳定、可解释的训练样本。

### 2.1 两种训练样本粒度（建议都支持）

#### A) “按 instance_id 聚合”的实体样本（首推，最稳定）

- **样本定义**：同一 `instance_id` 的所有日志记录聚合成 1 条样本。
- **优点**：不依赖真实时间戳；语义上对应一次 VM 生命周期/创建尝试；非常利于避免数据泄漏（按 instance_id 分组切分）。
- **缺点**：在线推理通常按时间窗，因此需保证在线侧使用同样的聚合方式（例如 60s 窗口按 instance_id 分组）。

#### B) “固定行数滑窗”的窗口样本（增强，贴近在线 60s 滑窗）

- **样本定义**：在每个 `instance_id` 的记录序列上做固定长度滑窗（例如 30 行窗口，15 行步长），每个窗口 1 条样本。
- **优点**：样本数更多；更贴近在线“窗口”的概念；对早期故障更敏感（窗口包含关键 ERROR 即可分辨）。
- **缺点**：相邻窗口高度相关，切分时必须按 `instance_id` 分组，不能随机打散。

> 建议：离线训练优先用 A（实体样本），在需要提升效果/贴近在线时再叠加 B（滑窗增强）。

---

## 3. 日志解析（Parsing）与多行合并（必须）

这些日志里存在 **XML/Traceback 等多行块**（例如 libvirt domain XML、Python Traceback）。如果不合并，多行会被误当成独立事件，模板化与窗口统计会被污染。

### 3.1 记录开始行（record head）判定

将以下模式视为“新日志记录”的开始（前置空格可有可无）：

- `^(DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL)\b`

否则视为上一条记录的 continuation，并拼接到上一条 `raw_message`（用 `\n` 连接）。

### 3.2 字段抽取（建议字段）

对每条合并后的记录，抽取这些字段（抽不到就置空）：

- `level`：`INFO/WARNING/ERROR/...`
- `component`：如 `nova.compute.manager`、`nova.virt.libvirt.driver`、`os_vif` 等
- `request_id`：`req-[0-9a-f-]{36}`
- `instance_id`：`instance: [0-9a-f-]{36}`
- `message`：去掉前缀后的正文（用于模板化）
- `dataset_id`：来自文件名映射（见 1.2）
- `line_no`：原始行号（便于回溯证据）

### 3.3 一个足够鲁棒的抽取策略（正则思路）

记录头大致长这样（变体很多：`[None req-...]`、`[-]`、`[req-...]` 等）：

```
LEVEL component [context...] [instance: ...] message...
```

建议实现上“**先粗分，再细抽**”：

1. 先用 `level` 和 `component` 从行首切出来；
2. 在整行中用独立正则搜索 `request_id`、`instance_id`；
3. `message` 取最后一个 `]` 之后的文本（若不存在 `]`，则取剩余部分）。

---

## 4. 模板化（Templating）：把噪声变量变成稳定“症状模板”

方案主线要求输出 `template_id` 并统计 Top 模板。模板化目标是把 UUID/IP/路径/数字等变量归一化，提升泛化与可解释性。

### 4.1 归一化规则（建议最小集合）

对 `message`（含 continuation 的多行块）按顺序替换：

1. UUID：`[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}` → `<UUID>`
2. request_id：`req-[0-9a-f-]{36}` → `req-<UUID>`
3. IPv4：`\b(?:\d{1,3}\.){3}\d{1,3}\b` → `<IPV4>`
4. IPv6（宽松）：`\b[0-9a-fA-F:]{2,}\b`（可选，注意误伤）→ `<IPV6>`
5. MAC：`\b(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\b` → `<MAC>`
6. 绝对路径：`/(?:[A-Za-z0-9._-]+/)+[A-Za-z0-9._-]+` → `<PATH>`
7. 长整型数字（字节数/时间等）：`\b\d{4,}\b` → `<NUM>`
8. 小数字（可选）：`\b\d+\b` → `<NUM>`

> 实战建议：如果你发现“数字本身是强区分信号（比如磁盘大小）”，可以只替换长数字（规则 7），保留 1～3 位小数字。

### 4.2 template_id 生成（可解释且稳定）

对归一化后的 `normalized_message`：

- `template_id = sha1(normalized_message).hexdigest()[:8]`（或 md5 也行）
- 同时保留 `template_text = normalized_message`（用于可视化展示 Top 模板含义）

---

## 5. 样本构建：entity_key、窗口与标签继承

### 5.1 entity_key 规则（和方案保持一致）

```
entity_key = instance_id if exists else request_id if exists else "global"
```

### 5.2 实体样本（A 方案）

对每个 `entity_key`（通常是 `instance_id`）聚合：

- `template_counts`：每个 `template_id` 的计数（稀疏字典）
- `level_counts`：`ERROR/WARN/INFO` 计数
- `component_counts`：组件计数（可选）
- `top_templates`：按次数 TopK 的 `template_id` 列表（K=10）
- `label_id`：继承自文件映射（1.2）

### 5.3 滑窗样本（B 方案）

在每个 `entity_key` 的记录序列上滑窗：

- `window_size_lines = 30`（建议起点）
- `stride_lines = 15`
- 每个窗口做与 5.2 同样的聚合特征，并继承 `label_id`

> 经验：`openstack-nova-dhcpoff.log` 每个实例行数较少，30 行窗口基本是“一实例一窗口”；`normal` 文件实例更多，窗口会更丰富。

---

## 6. 特征工程（Features）：最小可验收 + 易解释

### 6.1 必做特征（与方案一致）

1. **Bag-of-Templates**：`template_counts`（核心）
2. **错误强度**：`error_cnt`、`warn_cnt`、`total_cnt`、`error_ratio = error_cnt/total_cnt`
3. **TopK 模板**：用于解释与告警证据展示（不一定直接喂模型，但要落库/可视化）

### 6.2 建议加分特征（不复杂，但提升区分度）

> 这些特征不依赖时间戳，也不依赖外部知识库。

- `keyword_flags / keyword_counts`：对原始 message（或 normalized_message）做关键词计数/二值化，例如：
  - `FlavorDiskSmallerThanImage`
  - `BuildAbortException`
  - `VirtualInterfaceCreateException`
  - `Failed to allocate network`
  - `qemu unexpectedly closed the monitor`
  - `Failed to start libvirt guest`
  - `Error launching a defined domain`
- `component_entropy`（可选）：组件分布的熵，反映“是否集中在某个子系统”

> 注意：关键词特征建议在模板化前/后都试一下；有些关键字在异常栈里更容易出现。

---

## 7. 训练/验证/测试切分（避免泄漏的关键点）

### 7.1 必须按 entity_key 分组切分

原因：同一 `instance_id` 的相邻窗口/记录高度相关，如果随机打散，会出现“训练集看过同一个实例的上下文”，导致评估虚高。

建议切分策略：

- `group = entity_key`
- `train/val/test = 70% / 15% / 15%`（或 80/20）
- 若 sklearn 版本支持：`StratifiedGroupKFold` 或 `StratifiedGroupShuffleSplit`
- 否则：先按 `label_id` 分桶，再在桶内按 group 抽样

### 7.2 类别不平衡处理

从日志规模看，`normal` 样本会显著多于 3 类故障。建议：

- 模型使用 `class_weight="balanced"`（或 `"balanced_subsample"`）
- 或对 `normal` 下采样（例如最多保留与故障样本同量级的实体/窗口）

---

## 8. 模型选择与训练流程（可落地、可解释）

### 8.1 推荐基线（首推）

**Logistic Regression（多分类） + 稀疏向量**：

- 输入：`template_counts`（可拼上 `keyword_counts`、`level_counts` 等）
- 向量化：`DictVectorizer`（把稀疏字典变成稀疏矩阵）
- 分类器：`LogisticRegression(multi_class="multinomial", max_iter=2000, class_weight="balanced")`

优点：对稀疏高维的计数特征非常合适；训练快；可用权重解释“哪些模板推动了某类故障”。

### 8.2 备选模型（按需）

- `LinearSVC`（通常更强，但无原生概率；可用 `CalibratedClassifierCV` 校准概率）
- `RandomForestClassifier`（与方案一致的“经典小模型”，但对高维稀疏可能不如线性模型）

### 8.3 训练输出工件（必须固定格式，便于上线）

建议产出目录结构（示例）：

- `artifacts/model.joblib`：训练好的分类模型
- `artifacts/vectorizer.joblib`：DictVectorizer（或 CountVectorizer）
- `artifacts/label_map.json`：`{"0":"normal","1":"fault_vm_destroy_after_create",...}`
- `artifacts/template_rules.json`：模板化规则（正则/替换表），保证线上线下一致
- `reports/metrics.json`：Macro-F1、per-class F1、support、阈值等
- `reports/confusion_matrix.png`：混淆矩阵图（答辩友好）

---

## 9. 评估指标与验收口径（和答辩一致）

### 9.1 离线评估（训练/验证集）

必须输出：

- `Macro-F1`（主指标，避免被 normal 类压制）
- `Confusion Matrix`
- 每类 `precision/recall/F1/support`

### 9.2 阈值与告警策略（上线口径）

在线推理输出 `pred_class` + `prob` 后：

- 若 `pred_class != normal` 且 `prob >= 0.7` → 触发告警
- 或 `P(normal) < 0.5` → 触发“unknown/abnormal”告警（可选）

同时把告警证据写清楚：

- `top_templates`
- 窗口内 TopN 条 `ERROR` 原始日志（line_no + raw_line）

---

## 10. 弱标注/质检（可选，但很加分）

因为 “文件级强标签” 可能包含少量噪声（例如 `fault_vm_destroy_after_create` 文件中也可能混入网络/卷相关 abort），建议做两步质检：

1. **每类抽样 50 个 entity/window**，人工快速核对是否符合语义；
2. （可选）使用关键字规则做弱标注对齐：
   - 若窗口包含 `VirtualInterfaceCreateException`，但文件标签是 `fault_vm_destroy_after_create`，可以：
     - 方案 A：仍保持文件级标签（简单、稳定）
     - 方案 B：把此窗口改标为 `fault_network_dhcpoff`（更“纯”，但会改变任务定义）

> 建议答辩版本优先“稳定可复现”的方案 A；若追求更高指标，再做方案 B 的“弱标注清洗”并说明策略。

---

## 11. 最小实现的脚本接口（建议你按这个做成可运行脚本）

即使你暂时不写全链路，也建议把离线部分做成 2 个脚本，方便复现与验收：

1. `build_dataset.py`
   - 输入：4 个 `.log` 文件路径 + 配置（是否按 instance 聚合/滑窗、窗口大小等）
   - 输出：`dataset_windows.parquet` 或 `dataset_windows.csv`
2. `train_model.py`
   - 输入：`dataset_windows.*`
   - 输出：`artifacts/*` + `reports/*`

### 11.1 dataset 的最小字段建议（CSV/Parquet）

- `sample_id`：唯一 ID（可用 `dataset_id#entity_key#idx`）
- `dataset_id`：`normal/fault1/fault2/fault3`
- `label_id`：0/1/2/3
- `entity_key`：instance_id/request_id/global
- `start_line_no`、`end_line_no`：证据回溯
- `template_counts_json`：模板计数字典（JSON 字符串）
- `level_counts_json`、`keyword_counts_json`（可选）

---

## 12. 建议的默认超参数（先跑通，再调参）

### 12.1 模板化

- UUID/IP/MAC/路径/长数字替换开启（见 4.1）

### 12.2 样本构建

- 首推：按 `instance_id` 聚合（A）
- 增强：`window_size_lines=30`、`stride_lines=15`（B）

### 12.3 模型

- `LogisticRegression`（multinomial） + `class_weight="balanced"`
- 指标以 `Macro-F1` 为主
- 告警阈值：`0.7`（可在验证集上调整）

---

## 13. 与“在线流式方案”的对齐说明（防止线上线下不一致）

为了让线上推理真正可用，必须保证：

- **同一套解析 + 多行合并规则**
- **同一套模板化规则**
- **同一套 entity_key 规则**
- **同一套窗口构建方式（60s 时间窗或 N 行窗）**

离线训练如果用“按 instance 聚合”，线上也应尽量按 `instance_id` 聚合窗口（例如 60s 内同 instance 的日志聚合成一个 window feature），这样特征分布一致、效果更稳定。

