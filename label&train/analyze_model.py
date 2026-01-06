from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import joblib
import numpy as np

from openstack_log_pipeline import iter_merged_records, parse_record


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _save_json(path: Path, obj) -> None:
    _ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)


def _try_get_feature_names(vec) -> List[str]:
    if hasattr(vec, "get_feature_names_out"):
        return list(vec.get_feature_names_out())
    if hasattr(vec, "feature_names_"):
        return list(vec.feature_names_)
    raise RuntimeError("Cannot extract feature names from vectorizer.")


def build_template_text_map(log_paths: Iterable[Path]) -> Dict[str, str]:
    """
    Build a map template_id -> normalized_message by scanning logs using the same
    parser/normalizer as the offline dataset builder.

    Note: template_id is sha1(normalized_message)[:8], so mapping should be stable
    and (almost always) one-to-one.
    """
    tpl_to_text: Dict[str, str] = {}
    collisions: Dict[str, List[str]] = {}

    for lp in log_paths:
        for start_line_no, end_line_no, merged in iter_merged_records(lp):
            rec = parse_record(start_line_no, end_line_no, merged)
            tpl = rec.template_id
            txt = rec.normalized_message
            if tpl not in tpl_to_text:
                tpl_to_text[tpl] = txt
            elif tpl_to_text[tpl] != txt:
                collisions.setdefault(tpl, list({tpl_to_text[tpl], txt}))

    # Keep collisions for debugging; do not overwrite the canonical mapping.
    if collisions:
        tpl_to_text["_collisions"] = json.dumps(collisions, ensure_ascii=False)

    return tpl_to_text


@dataclass(frozen=True)
class FeatureWeight:
    feature: str
    weight: float
    kind: str
    template_id: Optional[str]
    template_text: Optional[str]


def _feature_kind(name: str) -> Tuple[str, Optional[str]]:
    if name.startswith("tpl_"):
        return "template", name[len("tpl_") :]
    if name.startswith("kw_"):
        return "keyword", None
    return "scalar", None


def top_features_by_class(
    coef: np.ndarray,
    feature_names: List[str],
    class_ids: List[int],
    tpl_to_text: Dict[str, str],
    topk: int,
) -> Dict[str, Dict[str, List[Dict]]]:
    out: Dict[str, Dict[str, List[Dict]]] = {}
    for row_i, cls in enumerate(class_ids):
        weights = coef[row_i]
        order_pos = np.argsort(-weights)[:topk]
        order_neg = np.argsort(weights)[:topk]

        def _pack(indices: np.ndarray) -> List[Dict]:
            items: List[Dict] = []
            for j in indices:
                name = feature_names[int(j)]
                kind, tpl_id = _feature_kind(name)
                items.append(
                    {
                        "feature": name,
                        "weight": float(weights[int(j)]),
                        "kind": kind,
                        "template_id": tpl_id,
                        "template_text": tpl_to_text.get(tpl_id) if tpl_id else None,
                    }
                )
            return items

        out[str(cls)] = {"top_positive": _pack(order_pos), "top_negative": _pack(order_neg)}
    return out


def render_markdown(
    label_map: Dict[str, str],
    per_class: Dict[str, Dict[str, List[Dict]]],
    topk: int,
) -> str:
    lines: List[str] = []
    lines.append("# Feature Importance (Logistic Regression Coefficients)")
    lines.append("")
    lines.append("- 说明：权重来自 `LogisticRegression(multinomial)` 的系数；正权重表示更倾向该类别。")
    lines.append(f"- 每类展示：Top-{topk} 正向特征 + Top-{topk} 负向特征。")
    lines.append("")

    for cls_id, cls_name in sorted(label_map.items(), key=lambda x: int(x[0])):
        block = per_class.get(cls_id)
        if not block:
            continue
        lines.append(f"## Class {cls_id}: {cls_name}")
        lines.append("")

        def _table(title: str, items: List[Dict]) -> None:
            lines.append(f"### {title}")
            lines.append("")
            lines.append("| rank | feature | weight | kind | template_text (if tpl_*) |")
            lines.append("|---:|---|---:|---|---|")
            for i, it in enumerate(items, start=1):
                txt = (it.get("template_text") or "").replace("\n", "\\n")
                if len(txt) > 120:
                    txt = txt[:120] + "…"
                lines.append(
                    f"| {i} | `{it.get('feature')}` | {it.get('weight'):.6f} | {it.get('kind')} | {txt} |"
                )
            lines.append("")

        _table(f"Top-{topk} positive", block["top_positive"])
        _table(f"Top-{topk} negative", block["top_negative"])

    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description="Analyze trained sklearn artifacts (feature importance / template map).")
    p.add_argument("--artifacts", type=Path, default=Path("label&train/output/artifacts"))
    p.add_argument("--reports", type=Path, default=Path("label&train/output/reports"))
    p.add_argument("--topk", type=int, default=20)
    p.add_argument(
        "--logs",
        type=Path,
        nargs="*",
        default=[
            Path("openstack-nova-normal-vm-create.log"),
            Path("openstack-vm-destroy-immediately-after-create.log"),
            Path("openstack-nova-dhcpoff.log"),
            Path("openstack-nova-undefine-vm-after-create.log"),
        ],
        help="Log paths used to build template_id -> normalized_message map.",
    )
    args = p.parse_args()

    model_path = args.artifacts / "model.joblib"
    vec_path = args.artifacts / "vectorizer.joblib"
    label_map_path = args.artifacts / "label_map.json"

    if not model_path.exists() or not vec_path.exists():
        raise FileNotFoundError(f"Missing artifacts: {model_path} or {vec_path}")

    clf = joblib.load(model_path)
    vec = joblib.load(vec_path)

    with label_map_path.open("r", encoding="utf-8") as f:
        label_map = json.load(f)

    feature_names = _try_get_feature_names(vec)
    if not hasattr(clf, "coef_") or not hasattr(clf, "classes_"):
        raise RuntimeError("Only sklearn LogisticRegression artifacts are supported for coefficient analysis.")

    coef = np.asarray(clf.coef_, dtype=np.float64)
    class_ids = [int(x) for x in list(clf.classes_)]

    tpl_to_text = build_template_text_map(args.logs)
    per_class = top_features_by_class(
        coef=coef,
        feature_names=feature_names,
        class_ids=class_ids,
        tpl_to_text=tpl_to_text,
        topk=args.topk,
    )

    out_json = {
        "topk": args.topk,
        "n_features": len(feature_names),
        "classes": class_ids,
        "label_map": label_map,
        "per_class": per_class,
    }

    _save_json(args.reports / "feature_importance.json", out_json)
    _save_json(args.reports / "template_text_map.json", tpl_to_text)
    md = render_markdown(label_map=label_map, per_class=per_class, topk=args.topk)
    _ensure_dir(args.reports)
    (args.reports / "feature_importance.md").write_text(md, encoding="utf-8")

    print(f"Saved: {args.reports / 'feature_importance.json'}")
    print(f"Saved: {args.reports / 'template_text_map.json'}")
    print(f"Saved: {args.reports / 'feature_importance.md'}")


if __name__ == "__main__":
    main()

