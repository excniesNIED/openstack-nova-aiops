from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse
import csv
from pathlib import Path
from typing import Dict, List

from openstack_log_pipeline import (
    DATASET_LABELS,
    DEFAULT_KEYWORDS,
    build_instance_dataset,
    downsample_by_instances,
    infer_dataset_id_from_filename,
)


def _write_csv(path: Path, rows: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("No rows generated; check input logs and parsing rules.")

    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    p = argparse.ArgumentParser(description="Build Plan-A dataset: one sample per instance_id.")
    p.add_argument("--normal", type=Path, required=True, help="Path to normal log file.")
    p.add_argument("--fault1", type=Path, required=True, help="Path to fault1 log file.")
    p.add_argument("--fault2", type=Path, required=True, help="Path to fault2 log file.")
    p.add_argument("--fault3", type=Path, required=True, help="Path to fault3 log file.")
    p.add_argument("--out", type=Path, required=True, help="Output CSV path, e.g. label&train/dataset_instance.csv")
    p.add_argument("--seed", type=int, default=42, help="Random seed for downsampling.")
    p.add_argument(
        "--max-instances-per-class",
        type=int,
        default=0,
        help="Downsample each class to at most N instances (0 disables).",
    )
    p.add_argument(
        "--keywords",
        type=str,
        default="",
        help="Comma-separated keyword overrides; default uses built-in keyword list.",
    )
    args = p.parse_args()

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()] if args.keywords else list(DEFAULT_KEYWORDS)

    inputs = [args.normal, args.fault1, args.fault2, args.fault3]
    all_rows: List[Dict] = []

    for path in inputs:
        dataset_id = infer_dataset_id_from_filename(path)
        if dataset_id not in DATASET_LABELS:
            raise ValueError(f"Unknown dataset_id: {dataset_id}")

        rows = build_instance_dataset(path, dataset_id=dataset_id, keywords=keywords)
        rows = downsample_by_instances(
            rows, max_instances=(args.max_instances_per_class or None), seed=args.seed
        )
        all_rows.extend(rows)

    _write_csv(args.out, all_rows)

    # Print minimal summary for humans (stdout only; no extra files).
    by_label: Dict[int, int] = {}
    for r in all_rows:
        by_label[int(r["label_id"])] = by_label.get(int(r["label_id"]), 0) + 1

    print(f"Wrote {len(all_rows)} samples to: {args.out}")
    for label_id, cnt in sorted(by_label.items()):
        print(f"  label_id={label_id}: {cnt} instances")


if __name__ == "__main__":
    main()

