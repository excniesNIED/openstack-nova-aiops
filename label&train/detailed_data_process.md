# 方案 A（按 `instance_id` 聚合）说明书：detailed_data_process.md

本文对应“日志解析 → 模板化 →（按实体）聚合特征 → 监督分类”的方案，**明确采用方案 A：按 `instance_id` 聚合成训练样本**。配套可运行代码在 `label&train/`。

---

## 0. 目标与输入输出

### 0.1 目标

用 4 个 OpenStack 日志文件构建一个监督分类数据集并训练一个多分类模型，输出：

- 数据集文件：每条样本对应一个 `instance_id`（实体样本）
- 模型与向量化器：可用于在线推理（输入同样的特征字典）
- 评估报告：Macro-F1、混淆矩阵、每类 Precision/Recall/F1

### 0.2 输入（本次固定 4 类）

| 文件 | dataset_id | label_id | label_name |
|---|---|---:|---|
| `openstack-nova-normal-vm-create.log` | `normal` | 0 | `normal` |
| `openstack-vm-destroy-immediately-after-create.log` | `fault1` | 1 | `fault_vm_destroy_after_create` |
| `openstack-nova-dhcpoff.log` | `fault2` | 2 | `fault_network_dhcpoff` |
| `openstack-nova-undefine-vm-after-create.log` | `fault3` | 3 | `fault_libvirt_domain_undefine` |

> 标签来源：文件级强标签（每个文件代表一个场景）。样本（instance）标签继承该文件标签。

### 0.3 输出（建议目录）

运行后得到：

- `label&train/dataset_instance.csv`：实体样本数据集
- `label&train/output/artifacts/`：模型工件
- `label&train/output/reports/`：评估报告

---

## 1. 任务定义（严谨）

### 1.1 监督学习形式化

给定日志记录集合 `R = {r_1, r_2, ...}`，每条记录解析得到：

- `instance_id(r)`：若存在则为 UUID，否则为空
- `message(r)`：文本正文
- `level(r)`：日志级别

方案 A 把同一 `instance_id` 的记录聚合为一个样本：

- `G_k = { r ∈ R | instance_id(r) = k }`
- `x_k = φ(G_k)`（特征提取函数）
- `y_k` 为文件级强标签（见 0.2）

学习一个多分类模型：

- `f(x) → P(y|x)`, `y ∈ {0,1,2,3}`

### 1.2 为什么选择按 `instance_id` 聚合（方案 A 的必要性）

1. **语义自然**：OpenStack VM 的创建/失败行为以 `instance_id` 贯穿，聚合后样本对应一次创建尝试（或生命周期片段）。
2. **降低时间依赖**：这些日志未必每行都有可解析的时间戳；按实体聚合不依赖事件时间。
3. **避免评估泄漏**：同一实例的日志高度相似，如果按行/窗口随机切分，训练和测试会共享同一实例的信息，导致指标虚高。

---

## 2. 原始日志预处理：多行合并 + 字段解析

### 2.1 多行合并（必须）

日志中存在多行块（domain XML、Traceback 等）。若不合并，会产生大量“伪事件”，污染模板和计数。

**记录起始行（head）定义**：

- `^(DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL)\b`

处理规则：

- 匹配 head：开始新记录
- 不匹配 head：拼接到上一条记录（用 `\n` 连接）
- 每条记录保留：`start_line_no`、`end_line_no`（用于证据回溯）

### 2.2 字段解析（Parsing）

对合并后的记录抽取：

- `level`：行首第 1 个 token
- `component`：行首第 2 个 token（如 `nova.compute.manager`）
- `request_id`：全记录中搜索 `req-[0-9a-f-]{36}`
- `instance_id`：全记录中搜索 `instance: [0-9a-f-]{36}`
- `message`：优先取“最后一个 `] ` 后面”的内容（适配多种 context 格式）；找不到则取去掉前两个 token 后的剩余文本

> 解析目标：在“尽量不假设日志格式完全统一”的前提下，稳定抽取 instance_id 与正文 message。

---

## 3. 模板化（Templating）：从原文到“稳定事件模板”

### 3.1 原理

同类运维事件通常是“固定句式 + 变量参数”。直接用原文会把变量当作特征，造成过拟合、泛化差。模板化将变量归一化，使模型学习“事件类型”而非“具体值”。

### 3.2 规则（默认启用）

对 `message`（含多行内容）按顺序替换：

1. UUID：`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` → `<UUID>`
2. request_id：`req-xxxxxxxx-....` → `req-<UUID>`
3. IPv4：`a.b.c.d` → `<IPV4>`
4. MAC：`aa:bb:cc:dd:ee:ff` → `<MAC>`
5. 绝对路径：`/opt/stack/...` → `<PATH>`
6. 长数字（≥4 位）：`12345` → `<NUM>`

### 3.3 template_id 定义

对 `normalized_message` 取 hash 得到 `template_id`：

- `template_id = sha1(normalized_message)[:8]`

同时保留 `template_text = normalized_message`，用于 Top 模板解释与告警证据展示。

---

## 4. 特征构建（按 instance 聚合）

对每个 `instance_id = k` 的记录集合 `G_k`，构造特征：

### 4.1 模板计数（Bag-of-Templates）

- `template_counts[t] = |{ r ∈ G_k : template_id(r) = t }|`

模板计数是核心特征，能把一个实例的行为序列压缩为可学习的稀疏向量。

### 4.2 日志级别强度（数值特征）

- `error_cnt` / `warn_cnt` / `info_cnt`
- `total_records`
- `error_ratio = error_cnt / total_records`

这些特征对 “normal vs fault” 具有强区分度，并能为告警阈值提供直观指标。

### 4.3 关键词计数（可解释补强）

对 `message` 或 `normalized_message` 统计关键短语次数（默认列表在代码里，可扩展）：

- `FlavorDiskSmallerThanImage`、`BuildAbortException`
- `VirtualInterfaceCreateException`、`Failed to allocate network`
- `qemu unexpectedly closed the monitor`、`Failed to start libvirt guest`

关键词计数能在异常栈很长、模板分裂时保持稳定信号。

### 4.4 证据（用于告警详情/人工验收）

为每个 instance 保留：

- `top_templates`：TopK 模板列表（K=10）
- `error_examples`：最多 N 条 ERROR 原文（含行号、组件、原文），用于回放/解释

---

## 5. 数据集文件格式：`dataset_instance.csv`

每行一个 instance 样本（字段精简但可复现）：

- `sample_id`：`dataset_id#<instance_uuid>`
- `dataset_id`：`normal/fault1/fault2/fault3`
- `label_id`、`label_name`
- `entity_key`：instance_uuid
- `start_line_no`、`end_line_no`
- `total_records`、`error_cnt`、`warn_cnt`、`info_cnt`、`error_ratio`
- `template_counts_json`：JSON 字符串（稀疏 dict）
- `keyword_counts_json`：JSON 字符串（可为空）
- `top_templates_json`：JSON 数组
- `error_examples_json`：JSON 数组（证据）

---

## 6. 切分策略（严谨：按 entity_key 分组）

### 6.1 核心要求

不能随机按样本行打散切分（尤其当你未来扩展为滑窗样本时更严重）。必须按 `entity_key`（instance）分组切分，保证：

- 同一 instance 的信息不会同时出现在训练集和测试集

### 6.2 分层组切分（Stratified Group Split）

因为 4 类样本数可能不均衡，切分时需要“尽量保持各类比例”：

1. 按 `label_id` 把 group（instance）分桶；
2. 每个桶内随机打乱；
3. 按比例切到 train/val/test；
4. 合并得到三份 group 列表，再过滤样本行。

训练脚本 `label&train/train_model.py` 已实现该逻辑。

---

## 7. 模型与训练原理（严谨但可落地）

### 7.1 向量化：`DictVectorizer`

把特征字典映射为稀疏向量 `x ∈ R^d`：

- 模板计数：键名形如 `tpl_<template_id>`
- 关键词计数：键名形如 `kw_<keyword>`
- 数值特征：`error_ratio`、`error_cnt` 等直接作为 float

`DictVectorizer` 会学习特征空间并输出稀疏矩阵 `X`。

### 7.2 分类器：多项式逻辑回归（Multinomial Logistic Regression）

对 4 类分类，使用 softmax：

- `P(y=c|x) = exp(w_c^T x) / Σ_j exp(w_j^T x)`

训练目标（交叉熵 + 正则）：

- `min_W  Σ_i -log P(y_i|x_i) + λ||W||_2^2`

选择理由：

- 对稀疏高维计数向量非常适配；
- 训练快、可解释（权重可分析“哪些模板区分某类故障”）；
- 可输出概率，用于线上告警阈值。

### 7.3 类别不平衡

启用 `class_weight="balanced"`，按类别频率自动加权，避免模型只偏向 `normal`。

---

## 8. 评估与上线口径

### 8.1 离线评估（必须输出）

- `Macro-F1`（主指标，抵抗类别不平衡）
- `confusion_matrix`
- 每类 Precision / Recall / F1 / Support

### 8.2 上线告警策略（与方案一致）

推理输出 `pred_class` 与 `prob` 后：

- `pred_class != normal` 且 `prob >= 0.7` → 告警

并附带证据：

- `top_templates`
- `error_examples`（行号 + 原文）

---

## 9. 使用方法（完整、可复现）

> 目录名包含 `&`，在 shell 中请使用引号。

### 9.1 安装依赖

```bash
pip install scikit-learn joblib
```

可选（不影响核心训练）：

```bash
pip install pandas matplotlib
```

### 9.2 构建数据集（方案 A）

在仓库根目录执行：

```bash
python "label&train/build_dataset.py" \
  --normal openstack-nova-normal-vm-create.log \
  --fault1 openstack-vm-destroy-immediately-after-create.log \
  --fault2 openstack-nova-dhcpoff.log \
  --fault3 openstack-nova-undefine-vm-after-create.log \
  --out "label&train/dataset_instance.csv"
```

### 9.3 训练与评估

```bash
python "label&train/train_model.py" \
  --data "label&train/dataset_instance.csv" \
  --outdir "label&train/output" \
  --seed 42
```

### 9.4 产物位置

- 模型工件：`label&train/output/artifacts/`
- 报告：`label&train/output/reports/`

---

## 10. GPU（Intel Arc / XPU）训练：如何“真正跑在 GPU 上”

### 10.1 背景与约束（为什么需要 torch backend）

本项目的核心特征是“模板计数的稀疏向量”。传统 sklearn 线性模型对稀疏 CSR 很友好，但主要跑 CPU。为让训练能用 Intel Arc（XPU），本项目在 `label&train/train_model.py` 中提供了 **PyTorch 后端**：

- 把稀疏 dict 特征通过 **Feature Hashing** 映射到固定维度的 **dense float32** 向量（`--hash-dim`）
- 用一个线性层 `Linear(hash_dim → 4)` 做 softmax 多分类
- 训练时把张量放到 `torch.xpu` 上执行（如果 XPU 可用）

这套设计的关键点是：**避免稀疏矩阵在 XPU 上的兼容性问题**，同时保持“模板计数 → 线性分类”的主线不变。

### 10.2 前置条件（你需要在 conda 环境里做的事）

1. 安装一个“支持 XPU 的 PyTorch”（不同系统/驱动的具体安装方式不同，请以 Intel/PyTorch XPU 官方说明为准）
2. 验证 XPU 可用：

```bash
python -c "import torch; print(torch.__version__); print(torch.xpu.is_available())"
```

当输出为 `True` 时，才表示脚本可以使用 `--device xpu`。

### 10.3 使用 torch+XPU 训练（推荐命令）

```bash
python "label&train/train_model.py" \
  --data "label&train/dataset_instance.csv" \
  --outdir "label&train/output_xpu" \
  --backend torch \
  --device xpu \
  --hash-dim 8192 \
  --epochs 50 \
  --batch-size 512 \
  --lr 1e-3 \
  --weight-decay 1e-4 \
  --patience 7
```

### 10.4 产物差异（CPU vs XPU）

- sklearn(CPU)：
  - `artifacts/model.joblib`
  - `artifacts/vectorizer.joblib`
- torch(XPU)：
  - `artifacts/model.pt`（state_dict + hash_dim + labels）
  - `artifacts/feature_hasher.json`（hash 规则与维度）

> 共同产物：`artifacts/label_map.json`、`artifacts/train_config.json`、`reports/metrics.json`

### 10.5 如何确认“确实在用 GPU”

最直接的确认方式：

- 训练时指定 `--backend torch --device xpu`
- 同时确保 `torch.xpu.is_available() == True`

如果 XPU 不可用，脚本在你指定 `--device xpu` 时会直接报错，避免“以为在用 GPU 实际跑 CPU”的情况。

### 9.5 常见问题（快速排查）

- 数据集样本数太少：检查是否过滤了无 `instance_id` 的记录；默认只保留包含 `instance_id` 的记录以保证方案 A 语义稳定。
- 类别比例极端：可在 `build_dataset.py` 启用 `--max-instances-per-class` 对 normal 下采样。
- 指标不稳定：提高故障样本数量（允许的话）或扩展关键词列表（不改变主线）。
