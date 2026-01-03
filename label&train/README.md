# label&train/

- 说明书：`label&train/detailed_data_process.md`
- 构建数据集（方案 A）：`label&train/build_dataset.py`
- 训练与评估：`label&train/train_model.py`

快速开始（仓库根目录）：

```bash
python "label&train/build_dataset.py" \
  --normal openstack-nova-normal-vm-create.log \
  --fault1 openstack-vm-destroy-immediately-after-create.log \
  --fault2 openstack-nova-dhcpoff.log \
  --fault3 openstack-nova-undefine-vm-after-create.log \
  --out "label&train/dataset_instance.csv"

python "label&train/train_model.py" \
  --data "label&train/dataset_instance.csv" \
  --outdir "label&train/output" \
  --seed 42
```

GPU（Intel Arc / XPU）：

- 训练脚本支持 `--backend torch --device xpu`（需要你在 conda 环境里安装“支持 XPU 的 PyTorch”）。
- 安装完成后先验证：`python -c "import torch; print(torch.xpu.is_available())"`
- 使用示例：

```bash
python "label&train/train_model.py" \
  --data "label&train/dataset_instance.csv" \
  --outdir "label&train/output_xpu" \
  --backend torch \
  --device xpu \
  --hash-dim 8192 \
  --epochs 50 \
  --batch-size 512
```

安装命令：`pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/xpu`
