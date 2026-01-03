from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, Tuple

import joblib


def stable_alert_id(entity_key: str, window_end: str, pred_label_id: int) -> str:
    base = f"{entity_key}|{window_end}|{pred_label_id}"
    return hashlib.sha1(base.encode("utf-8", errors="ignore")).hexdigest()[:24]


def load_artifacts(model_dir: Path):
    model_path = model_dir / "model.joblib"
    vec_path = model_dir / "vectorizer.joblib"
    label_map_path = model_dir / "label_map.json"

    clf = joblib.load(model_path)
    vec = joblib.load(vec_path)
    label_map_raw = json.loads(label_map_path.read_text(encoding="utf-8"))
    label_map = {int(k): str(v) for k, v in label_map_raw.items()}
    return clf, vec, label_map


def build_feature_dict(feature_msg: Dict[str, Any]) -> Dict[str, float]:
    tpl_counts = feature_msg.get("template_counts") or {}
    kw_counts = feature_msg.get("keyword_counts") or {}

    feat: Dict[str, float] = {}
    for tpl_id, cnt in tpl_counts.items():
        try:
            feat[f"tpl_{tpl_id}"] = float(cnt)
        except Exception:
            continue
    for kw, cnt in kw_counts.items():
        try:
            feat[f"kw_{kw}"] = float(cnt)
        except Exception:
            continue

    error_cnt = int(feature_msg.get("error_cnt") or 0)
    warn_cnt = int(feature_msg.get("warn_cnt") or 0)
    info_cnt = int(feature_msg.get("info_cnt") or 0)
    total_records = int(feature_msg.get("total_records") or 0)
    error_ratio = float(feature_msg.get("error_ratio") or 0.0)

    feat["error_cnt"] = float(error_cnt)
    feat["warn_cnt"] = float(warn_cnt)
    feat["info_cnt"] = float(info_cnt)
    feat["total_records"] = float(total_records)
    feat["error_ratio"] = float(error_ratio)

    feat["log_total_records"] = math.log1p(max(total_records, 0))
    feat["log_error_cnt"] = math.log1p(max(error_cnt, 0))

    return feat


def predict_one(clf, vec, label_map: Dict[int, str], feature_msg: Dict[str, Any]) -> Tuple[int, str, float]:
    feat = build_feature_dict(feature_msg)
    X = vec.transform([feat])

    pred_id = int(clf.predict(X)[0])
    pred_name = label_map.get(pred_id, str(pred_id))

    prob = 1.0
    if hasattr(clf, "predict_proba"):
        proba = clf.predict_proba(X)[0]
        try:
            prob = float(proba[pred_id])
        except Exception:
            prob = float(max(proba))

    return pred_id, pred_name, prob

