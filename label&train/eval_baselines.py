from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


LABEL_NAMES: Dict[int, str] = {
    0: "normal",
    1: "fault_vm_destroy_after_create",
    2: "fault_network_dhcpoff",
    3: "fault_libvirt_domain_undefine",
}


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _save_json(path: Path, obj) -> None:
    _ensure_dir(path.parent)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _read_rows(path: Path) -> List[Dict]:
    rows: List[Dict] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def _to_int(v: str, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def _to_float(v: str, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _parse_json_field(value: str):
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    return json.loads(value)


def stratified_group_split(
    rows: List[Dict],
    group_key: str,
    label_key: str,
    train_ratio: float,
    val_ratio: float,
    seed: int,
) -> Tuple[List[int], List[int], List[int]]:
    import random

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


def confusion_matrix(y_true: List[int], y_pred: List[int], labels: List[int]) -> List[List[int]]:
    idx = {lab: i for i, lab in enumerate(labels)}
    cm = [[0 for _ in labels] for _ in labels]
    for t, p in zip(y_true, y_pred):
        cm[idx[t]][idx[p]] += 1
    return cm


def macro_f1(y_true: List[int], y_pred: List[int], labels: List[int]) -> float:
    f1s: List[float] = []
    for lab in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == lab and p == lab)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != lab and p == lab)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == lab and p != lab)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0
        f1s.append(f1)
    return float(sum(f1s) / len(f1s)) if f1s else 0.0


def _template_counts(row: Dict) -> Dict[str, int]:
    d = _parse_json_field(row.get("template_counts_json", "")) or {}
    return {str(k): int(v) for k, v in d.items()}


def _keyword_counts(row: Dict) -> Dict[str, int]:
    d = _parse_json_field(row.get("keyword_counts_json", "")) or {}
    return {str(k): int(v) for k, v in d.items()}


KEYWORD_RULES: List[Tuple[int, List[str]]] = [
    (1, ["FlavorDiskSmallerThanImage", "BuildAbortException"]),
    (2, ["Failed to allocate network", "VirtualInterfaceCreateException"]),
    (3, ["Error launching a defined domain", "Failed to start libvirt guest", "qemu unexpectedly closed the monitor"]),
]


def predict_keyword_rules(rows: List[Dict], indices: List[int]) -> List[int]:
    preds: List[int] = []
    for i in indices:
        r = rows[i]
        kw = _keyword_counts(r)
        y = 0
        for cls, keys in KEYWORD_RULES:
            if any(kw.get(k, 0) > 0 for k in keys):
                y = cls
                break
        preds.append(y)
    return preds


@dataclass
class MultinomialNB:
    alpha: float = 1.0
    class_log_prior: Dict[int, float] = None  # type: ignore[assignment]
    feat_log_prob: Dict[int, Dict[str, float]] = None  # type: ignore[assignment]
    default_log_prob: Dict[int, float] = None  # type: ignore[assignment]

    def fit(self, rows: List[Dict], indices: List[int], labels: List[int]) -> "MultinomialNB":
        class_counts = Counter()
        feat_counts: Dict[int, Counter] = defaultdict(Counter)
        total_feat_counts: Dict[int, int] = defaultdict(int)

        for i in indices:
            r = rows[i]
            y = _to_int(r.get("label_id", "0"))
            class_counts[y] += 1
            counts = _template_counts(r)
            for tpl, c in counts.items():
                feat_counts[y][tpl] += c
                total_feat_counts[y] += c

        n = sum(class_counts.values())
        self.class_log_prior = {c: math.log(class_counts[c] / n) for c in labels}

        vocab = set()
        for c in labels:
            vocab.update(feat_counts[c].keys())
        vocab_size = len(vocab) if vocab else 1

        self.feat_log_prob = {}
        self.default_log_prob = {}
        for c in labels:
            denom = total_feat_counts[c] + self.alpha * vocab_size
            self.feat_log_prob[c] = {}
            for f in vocab:
                num = feat_counts[c][f] + self.alpha
                self.feat_log_prob[c][f] = math.log(num / denom)
            self.default_log_prob[c] = math.log(self.alpha / denom)

        return self

    def predict(self, rows: List[Dict], indices: List[int], labels: List[int]) -> List[int]:
        preds: List[int] = []
        for i in indices:
            r = rows[i]
            counts = _template_counts(r)
            best_c = labels[0]
            best_s = -1e100
            for c in labels:
                s = self.class_log_prior[c]
                lp = self.feat_log_prob[c]
                dlp = self.default_log_prob[c]
                for f, v in counts.items():
                    s += v * lp.get(f, dlp)
                if s > best_s:
                    best_s = s
                    best_c = c
            preds.append(best_c)
        return preds


def _l2_normalize_sparse(d: Dict[str, float]) -> Dict[str, float]:
    norm = math.sqrt(sum(v * v for v in d.values()))
    if norm <= 0:
        return d
    return {k: v / norm for k, v in d.items()}


def _dot_sparse(a: Dict[str, float], b: Dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    s = 0.0
    for k, v in a.items():
        s += v * b.get(k, 0.0)
    return s


def centroid_classifier_train(rows: List[Dict], indices: List[int], labels: List[int]) -> Dict[int, Dict[str, float]]:
    sums: Dict[int, Counter] = {c: Counter() for c in labels}
    counts: Dict[int, int] = {c: 0 for c in labels}
    for i in indices:
        r = rows[i]
        y = _to_int(r.get("label_id", "0"))
        v = {f"tpl_{k}": float(v) for k, v in _template_counts(r).items()}
        v["error_ratio"] = _to_float(r.get("error_ratio", "0"))
        v = _l2_normalize_sparse(v)
        for k, val in v.items():
            sums[y][k] += val
        counts[y] += 1
    centroids: Dict[int, Dict[str, float]] = {}
    for c in labels:
        if counts[c] <= 0:
            centroids[c] = {}
        else:
            centroids[c] = {k: v / counts[c] for k, v in sums[c].items()}
    return centroids


def centroid_classifier_predict(
    rows: List[Dict], indices: List[int], labels: List[int], centroids: Dict[int, Dict[str, float]]
) -> List[int]:
    preds: List[int] = []
    for i in indices:
        r = rows[i]
        v = {f"tpl_{k}": float(v) for k, v in _template_counts(r).items()}
        v["error_ratio"] = _to_float(r.get("error_ratio", "0"))
        v = _l2_normalize_sparse(v)
        best_c = labels[0]
        best_s = -1e18
        for c in labels:
            s = _dot_sparse(v, centroids.get(c, {}))
            if s > best_s:
                best_s = s
                best_c = c
        preds.append(best_c)
    return preds


def centroid_tpl_only_train(rows: List[Dict], indices: List[int], labels: List[int]) -> Dict[int, Dict[str, float]]:
    sums: Dict[int, Counter] = {c: Counter() for c in labels}
    counts: Dict[int, int] = {c: 0 for c in labels}
    for i in indices:
        r = rows[i]
        y = _to_int(r.get("label_id", "0"))
        v = {f"tpl_{k}": float(v) for k, v in _template_counts(r).items()}
        v = _l2_normalize_sparse(v)
        for k, val in v.items():
            sums[y][k] += val
        counts[y] += 1
    centroids: Dict[int, Dict[str, float]] = {}
    for c in labels:
        if counts[c] <= 0:
            centroids[c] = {}
        else:
            centroids[c] = {k: v / counts[c] for k, v in sums[c].items()}
    return centroids


def centroid_tpl_only_predict(
    rows: List[Dict], indices: List[int], labels: List[int], centroids: Dict[int, Dict[str, float]]
) -> List[int]:
    preds: List[int] = []
    for i in indices:
        r = rows[i]
        v = {f"tpl_{k}": float(v) for k, v in _template_counts(r).items()}
        v = _l2_normalize_sparse(v)
        best_c = labels[0]
        best_s = -1e18
        for c in labels:
            s = _dot_sparse(v, centroids.get(c, {}))
            if s > best_s:
                best_s = s
                best_c = c
        preds.append(best_c)
    return preds


def main() -> None:
    p = argparse.ArgumentParser(description="Evaluate lightweight baselines on dataset_instance.csv (no sklearn training).")
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--out", type=Path, default=Path("label&train/output/reports/baselines.json"))
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--train-ratio", type=float, default=0.7)
    p.add_argument("--val-ratio", type=float, default=0.15)
    args = p.parse_args()

    rows = _read_rows(args.data)
    train_idx, val_idx, test_idx = stratified_group_split(
        rows, group_key="entity_key", label_key="label_id", train_ratio=args.train_ratio, val_ratio=args.val_ratio, seed=args.seed
    )

    labels = sorted({int(r.get("label_id", "0")) for r in rows})
    y_test = [_to_int(rows[i].get("label_id", "0")) for i in test_idx]

    results: Dict[str, Dict] = {}

    pred_kw = predict_keyword_rules(rows, test_idx)
    results["keyword_rules"] = {
        "test_macro_f1": macro_f1(y_test, pred_kw, labels=labels),
        "confusion_matrix_test": confusion_matrix(y_test, pred_kw, labels=labels),
    }

    nb = MultinomialNB(alpha=1.0).fit(rows, train_idx, labels=labels)
    pred_nb = nb.predict(rows, test_idx, labels=labels)
    results["template_multinomial_nb"] = {
        "alpha": 1.0,
        "test_macro_f1": macro_f1(y_test, pred_nb, labels=labels),
        "confusion_matrix_test": confusion_matrix(y_test, pred_nb, labels=labels),
    }

    centroids = centroid_classifier_train(rows, train_idx, labels=labels)
    pred_centroid = centroid_classifier_predict(rows, test_idx, labels=labels, centroids=centroids)
    results["template_centroid_cosine"] = {
        "test_macro_f1": macro_f1(y_test, pred_centroid, labels=labels),
        "confusion_matrix_test": confusion_matrix(y_test, pred_centroid, labels=labels),
    }

    centroids_tpl_only = centroid_tpl_only_train(rows, train_idx, labels=labels)
    pred_centroid_tpl_only = centroid_tpl_only_predict(rows, test_idx, labels=labels, centroids=centroids_tpl_only)
    results["template_centroid_tpl_only"] = {
        "test_macro_f1": macro_f1(y_test, pred_centroid_tpl_only, labels=labels),
        "confusion_matrix_test": confusion_matrix(y_test, pred_centroid_tpl_only, labels=labels),
    }

    out = {
        "seed": args.seed,
        "train_ratio": args.train_ratio,
        "val_ratio": args.val_ratio,
        "n_train": len(train_idx),
        "n_val": len(val_idx),
        "n_test": len(test_idx),
        "labels": labels,
        "label_names": {str(k): LABEL_NAMES.get(k, str(k)) for k in labels},
        "baselines": results,
    }

    _save_json(args.out, out)
    print(f"Saved: {args.out}")


if __name__ == "__main__":
    main()
