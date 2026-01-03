from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse
import json
import math
import os
import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import joblib
import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score


def _read_csv_dicts(path: Path) -> List[Dict]:
    import csv

    rows: List[Dict] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def _parse_json_field(value: str):
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return json.loads(value)


def _to_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _to_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def build_feature_dict(row: Dict) -> Dict[str, float]:
    tpl_counts = _parse_json_field(row.get("template_counts_json", "")) or {}
    kw_counts = _parse_json_field(row.get("keyword_counts_json", "")) or {}

    feat: Dict[str, float] = {}
    for tpl_id, cnt in tpl_counts.items():
        feat[f"tpl_{tpl_id}"] = float(cnt)
    for kw, cnt in kw_counts.items():
        feat[f"kw_{kw}"] = float(cnt)

    error_cnt = _to_int(row.get("error_cnt", "0"))
    warn_cnt = _to_int(row.get("warn_cnt", "0"))
    info_cnt = _to_int(row.get("info_cnt", "0"))
    total_records = _to_int(row.get("total_records", "0"))
    error_ratio = _to_float(row.get("error_ratio", "0"))

    feat["error_cnt"] = float(error_cnt)
    feat["warn_cnt"] = float(warn_cnt)
    feat["info_cnt"] = float(info_cnt)
    feat["total_records"] = float(total_records)
    feat["error_ratio"] = float(error_ratio)

    # Optional stabilizer: log-scale counts
    feat["log_total_records"] = math.log1p(max(total_records, 0))
    feat["log_error_cnt"] = math.log1p(max(error_cnt, 0))

    return feat


def _stable_hash_to_index(text: str, dim: int) -> int:
    # Deterministic across runs/machines (do not use Python's built-in hash()).
    digest = hashlib.blake2b(text.encode("utf-8", errors="ignore"), digest_size=8).digest()
    return int.from_bytes(digest, "little") % dim


def build_hashed_dense_matrix(X_dicts: List[Dict[str, float]], dim: int) -> np.ndarray:
    """
    Convert feature dicts to a fixed-size dense matrix via feature hashing.
    This is used by the PyTorch backend to avoid sparse-XPU limitations.
    """
    X = np.zeros((len(X_dicts), dim), dtype=np.float32)
    for i, feats in enumerate(X_dicts):
        for k, v in feats.items():
            if not v:
                continue
            j = _stable_hash_to_index(k, dim)
            X[i, j] += float(v)
    return X


def stratified_group_split(
    rows: List[Dict],
    group_key: str,
    label_key: str,
    train_ratio: float,
    val_ratio: float,
    seed: int,
) -> Tuple[List[int], List[int], List[int]]:
    """
    Deterministic split by groups, stratified by label at group level.

    Returns indices for (train, val, test).
    """
    import random

    # Map group -> label, and group -> row indices
    group_to_label: Dict[str, int] = {}
    group_to_indices: Dict[str, List[int]] = {}

    for i, r in enumerate(rows):
        g = r.get(group_key, "")
        if not g:
            continue
        y = _to_int(r.get(label_key, "0"))
        group_to_indices.setdefault(g, []).append(i)
        group_to_label.setdefault(g, y)

    label_to_groups: Dict[int, List[str]] = {}
    for g, y in group_to_label.items():
        label_to_groups.setdefault(y, []).append(g)

    rng = random.Random(seed)
    train_groups, val_groups, test_groups = set(), set(), set()

    for y, groups in label_to_groups.items():
        rng.shuffle(groups)
        n = len(groups)
        n_train = int(round(n * train_ratio))
        n_val = int(round(n * val_ratio))
        n_train = min(n_train, n)
        n_val = min(n_val, n - n_train)

        train_groups.update(groups[:n_train])
        val_groups.update(groups[n_train : n_train + n_val])
        test_groups.update(groups[n_train + n_val :])

    train_idx: List[int] = []
    val_idx: List[int] = []
    test_idx: List[int] = []

    for g, idxs in group_to_indices.items():
        if g in train_groups:
            train_idx.extend(idxs)
        elif g in val_groups:
            val_idx.extend(idxs)
        else:
            test_idx.extend(idxs)

    return train_idx, val_idx, test_idx


@dataclass(frozen=True)
class TrainConfig:
    seed: int
    train_ratio: float
    val_ratio: float
    backend: str
    device: str
    model: str
    class_weight: str
    max_iter: int
    hash_dim: int
    epochs: int
    batch_size: int
    lr: float
    weight_decay: float
    patience: int


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _save_json(path: Path, obj) -> None:
    _ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)


def _maybe_plot_confusion_matrix(cm, labels: List[str], outpath: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return

    _ensure_dir(outpath.parent)
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.imshow(cm, interpolation="nearest")
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_yticklabels(labels)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")

    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center")

    fig.tight_layout()
    fig.savefig(outpath)
    plt.close(fig)


def _try_import_torch():
    try:
        import torch  # type: ignore
        return torch
    except Exception:
        return None


def _pick_device(torch_mod, device_arg: str) -> str:
    if device_arg == "cpu":
        return "cpu"
    if device_arg == "xpu":
        if hasattr(torch_mod, "xpu") and torch_mod.xpu.is_available():
            return "xpu"
        raise RuntimeError("Requested device=xpu but torch.xpu is not available. Install an XPU-enabled PyTorch build.")
    # auto
    if hasattr(torch_mod, "xpu") and torch_mod.xpu.is_available():
        return "xpu"
    return "cpu"


def _torch_train_eval(
    torch_mod,
    X_train: np.ndarray,
    y_train: List[int],
    X_val: np.ndarray,
    y_val: List[int],
    X_test: np.ndarray,
    y_test: List[int],
    num_classes: int,
    device: str,
    epochs: int,
    batch_size: int,
    lr: float,
    weight_decay: float,
    seed: int,
    patience: int,
) -> Tuple[Dict, object]:
    torch = torch_mod

    torch.manual_seed(seed)
    if device == "xpu":
        torch.xpu.manual_seed(seed)

    d = X_train.shape[1]
    model = torch.nn.Linear(d, num_classes)
    model.to(device)

    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    loss_fn = torch.nn.CrossEntropyLoss()

    def _predict_logits(X: np.ndarray) -> np.ndarray:
        model.eval()
        with torch.no_grad():
            tX = torch.from_numpy(X).to(device)
            logits = model(tX).float()
            logits_cpu = logits.detach().to("cpu").numpy()
            return logits_cpu

    best_state = None
    best_val = -1.0
    bad_epochs = 0

    n = len(y_train)
    indices = np.arange(n)

    for epoch in range(1, epochs + 1):
        model.train()
        np.random.shuffle(indices)

        for start in range(0, n, batch_size):
            batch_idx = indices[start : start + batch_size]
            xb = torch.from_numpy(X_train[batch_idx]).to(device)
            yb = torch.tensor([y_train[i] for i in batch_idx], dtype=torch.long, device=device)

            opt.zero_grad(set_to_none=True)
            logits = model(xb).float()
            loss = loss_fn(logits, yb)
            loss.backward()
            opt.step()

        val_logits = _predict_logits(X_val)
        val_pred = val_logits.argmax(axis=1).tolist()
        val_macro_f1 = float(f1_score(y_val, val_pred, average="macro"))

        if val_macro_f1 > best_val:
            best_val = val_macro_f1
            best_state = {k: v.detach().to("cpu") for k, v in model.state_dict().items()}
            bad_epochs = 0
        else:
            bad_epochs += 1
            if bad_epochs >= patience:
                break

    if best_state is not None:
        model.load_state_dict(best_state)

    test_logits = _predict_logits(X_test)
    test_pred = test_logits.argmax(axis=1).tolist()

    return {
        "val_macro_f1": float(best_val),
        "test_macro_f1": float(f1_score(y_test, test_pred, average="macro")),
        "y_test_pred": test_pred,
        "confusion_matrix_test": confusion_matrix(y_test, test_pred).tolist(),
    }, model


def main() -> None:
    p = argparse.ArgumentParser(description="Train a multiclass model from Plan-A instance dataset.")
    p.add_argument("--data", type=Path, required=True, help="Path to dataset_instance.csv")
    p.add_argument("--outdir", type=Path, required=True, help="Output directory, e.g. label&train/output")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--train-ratio", type=float, default=0.7)
    p.add_argument("--val-ratio", type=float, default=0.15)
    p.add_argument("--backend", choices=["auto", "sklearn", "torch"], default="auto", help="Training backend.")
    p.add_argument("--device", choices=["auto", "cpu", "xpu"], default="auto", help="Device for torch backend.")
    p.add_argument("--hash-dim", type=int, default=8192, help="Feature hashing dimension for torch backend.")
    p.add_argument("--epochs", type=int, default=50, help="Epochs for torch backend.")
    p.add_argument("--batch-size", type=int, default=256, help="Batch size for torch backend.")
    p.add_argument("--lr", type=float, default=1e-3, help="Learning rate for torch backend.")
    p.add_argument("--weight-decay", type=float, default=1e-4, help="Weight decay for torch backend.")
    p.add_argument("--patience", type=int, default=7, help="Early-stopping patience (val Macro-F1) for torch backend.")
    args = p.parse_args()

    rows = _read_csv_dicts(args.data)
    if not rows:
        raise ValueError("Dataset is empty.")

    # Build features/labels/groups.
    X_dicts: List[Dict[str, float]] = []
    y: List[int] = []
    groups: List[str] = []
    for r in rows:
        X_dicts.append(build_feature_dict(r))
        y.append(_to_int(r.get("label_id", "0")))
        groups.append(r.get("entity_key", ""))

    train_idx, val_idx, test_idx = stratified_group_split(
        rows,
        group_key="entity_key",
        label_key="label_id",
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        seed=args.seed,
    )

    vec = DictVectorizer(sparse=True)
    y_train = [y[i] for i in train_idx]
    y_val = [y[i] for i in val_idx]
    y_test = [y[i] for i in test_idx]

    labels_sorted = sorted(set(y))
    label_names = {
        0: "normal",
        1: "fault_vm_destroy_after_create",
        2: "fault_network_dhcpoff",
        3: "fault_libvirt_domain_undefine",
    }
    target_names = [label_names.get(i, str(i)) for i in labels_sorted]

    reports_dir = args.outdir / "reports"
    artifacts_dir = args.outdir / "artifacts"
    _ensure_dir(reports_dir)
    _ensure_dir(artifacts_dir)

    torch_mod = _try_import_torch()
    use_torch = False
    chosen_device: Optional[str] = None
    if args.backend == "torch":
        if torch_mod is None:
            raise RuntimeError("backend=torch requested but torch is not installed.")
        use_torch = True
        chosen_device = _pick_device(torch_mod, args.device)
    elif args.backend == "auto":
        if torch_mod is not None:
            try:
                chosen_device = _pick_device(torch_mod, "auto")
                use_torch = chosen_device == "xpu"
            except Exception:
                use_torch = False
                chosen_device = None

    if use_torch:
        X_train = build_hashed_dense_matrix([X_dicts[i] for i in train_idx], dim=args.hash_dim)
        X_val = build_hashed_dense_matrix([X_dicts[i] for i in val_idx], dim=args.hash_dim)
        X_test = build_hashed_dense_matrix([X_dicts[i] for i in test_idx], dim=args.hash_dim)

        torch_metrics, torch_model = _torch_train_eval(
            torch_mod,
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            X_test=X_test,
            y_test=y_test,
            num_classes=len(labels_sorted),
            device=chosen_device or "cpu",
            epochs=args.epochs,
            batch_size=args.batch_size,
            lr=args.lr,
            weight_decay=args.weight_decay,
            seed=args.seed,
            patience=args.patience,
        )
        y_test_pred = torch_metrics["y_test_pred"]
        cm = confusion_matrix(y_test, y_test_pred, labels=labels_sorted)
        val_macro_f1 = float(torch_metrics["val_macro_f1"])
        test_macro_f1 = float(torch_metrics["test_macro_f1"])

        # Save torch model
        torch_mod.save(
            {"state_dict": torch_model.state_dict(), "hash_dim": args.hash_dim, "labels": labels_sorted},
            artifacts_dir / "model.pt",
        )
        _save_json(artifacts_dir / "feature_hasher.json", {"type": "blake2b_mod", "dim": args.hash_dim})
        backend_name = "torch"
        device_name = chosen_device or "cpu"
        model_name = f"TorchLinear(dim={args.hash_dim})"
        vec_obj = None
        clf_obj = None
    else:
        # sklearn backend (CPU)
        X_train = vec.fit_transform([X_dicts[i] for i in train_idx])
        X_val = vec.transform([X_dicts[i] for i in val_idx])
        X_test = vec.transform([X_dicts[i] for i in test_idx])

        clf = LogisticRegression(
            multi_class="multinomial",
            max_iter=2000,
            class_weight="balanced",
            n_jobs=1,
            random_state=args.seed,
        )
        clf.fit(X_train, y_train)

        y_val_pred = clf.predict(X_val)
        y_test_pred = clf.predict(X_test)
        val_macro_f1 = float(f1_score(y_val, y_val_pred, average="macro"))
        test_macro_f1 = float(f1_score(y_test, y_test_pred, average="macro"))
        cm = confusion_matrix(y_test, y_test_pred, labels=labels_sorted)

        joblib.dump(clf, artifacts_dir / "model.joblib")
        joblib.dump(vec, artifacts_dir / "vectorizer.joblib")
        backend_name = "sklearn"
        device_name = "cpu"
        model_name = "LogisticRegression(multinomial)"
        vec_obj = vec
        clf_obj = clf

    cfg = TrainConfig(
        seed=args.seed,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        backend=backend_name,
        device=device_name,
        model=model_name,
        class_weight="balanced",
        max_iter=2000,
        hash_dim=args.hash_dim,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        weight_decay=args.weight_decay,
        patience=args.patience,
    )

    metrics = {
        "val_macro_f1": val_macro_f1,
        "test_macro_f1": test_macro_f1,
        "labels": labels_sorted,
        "label_names": {str(k): v for k, v in label_names.items()},
        "classification_report_test": classification_report(
            y_test, y_test_pred, labels=labels_sorted, target_names=target_names, output_dict=True, zero_division=0
        ),
        "confusion_matrix_test": cm.tolist(),
        "n_train": len(train_idx),
        "n_val": len(val_idx),
        "n_test": len(test_idx),
        "feature_dim": int(len(vec.feature_names_)) if (not use_torch and vec_obj is not None) else int(args.hash_dim),
    }

    _save_json(reports_dir / "metrics.json", metrics)
    _maybe_plot_confusion_matrix(cm, labels=target_names, outpath=reports_dir / "confusion_matrix.png")
    _save_json(artifacts_dir / "label_map.json", metrics["label_names"])
    _save_json(artifacts_dir / "train_config.json", asdict(cfg))

    # Avoid accidental bytecode writes in constrained environments.
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

    print(f"Saved artifacts to: {artifacts_dir}")
    print(f"Saved reports to: {reports_dir}")
    print(f"val_macro_f1={val_macro_f1:.4f} test_macro_f1={test_macro_f1:.4f}")


if __name__ == "__main__":
    main()

