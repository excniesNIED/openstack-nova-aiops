from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from kafka import KafkaConsumer

from .db import Alert, init_db, insert_alert, make_engine, utcnow_iso
from .model import load_artifacts, predict_one, stable_alert_id


@dataclass
class WorkerConfig:
    kafka_bootstrap: str
    features_topic: str
    group_id: str
    db_url: str
    model_dir: Path
    alert_threshold: float
    dedup_ttl_sec: int


class InferenceWorker:
    def __init__(self, cfg: WorkerConfig):
        self.cfg = cfg
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self._engine = make_engine(cfg.db_url)
        init_db(self._engine)

        self._clf, self._vec, self._label_map = load_artifacts(cfg.model_dir)

        # (entity_key, pred_id) -> last_window_end_epoch
        self._dedup: Dict[str, float] = {}

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="InferenceWorker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _dedup_key(self, entity_key: str, pred_id: int) -> str:
        return f"{entity_key}#{pred_id}"

    def _purge_dedup(self) -> None:
        now = time.time()
        ttl = float(self.cfg.dedup_ttl_sec)
        if ttl <= 0:
            return
        dead = [k for k, ts in self._dedup.items() if (now - ts) > ttl]
        for k in dead:
            self._dedup.pop(k, None)

    def _severity(self, pred_id: int, prob: float, error_ratio: float) -> str:
        if pred_id == 0:
            return "P3"
        if prob >= 0.9 or error_ratio >= 0.2:
            return "P1"
        return "P2"

    def _run(self) -> None:
        consumer = KafkaConsumer(
            self.cfg.features_topic,
            bootstrap_servers=self.cfg.kafka_bootstrap,
            group_id=self.cfg.group_id,
            enable_auto_commit=True,
            auto_offset_reset="latest",
            value_deserializer=lambda b: json.loads(b.decode("utf-8", errors="replace")),
            consumer_timeout_ms=1000,
        )

        try:
            while not self._stop.is_set():
                self._purge_dedup()
                polled = consumer.poll(timeout_ms=1000, max_records=200)
                if not polled:
                    continue

                for _tp, msgs in polled.items():
                    for m in msgs:
                        try:
                            self._handle_feature(m.value)
                        except Exception:
                            # Keep worker alive; details are surfaced in container logs.
                            continue
        finally:
            try:
                consumer.close(timeout=5)
            except Exception:
                pass

    def _handle_feature(self, feature: Dict[str, Any]) -> None:
        entity_key = str(feature.get("entity_key") or "")
        if not entity_key:
            return

        window_end = str(feature.get("window_end") or "")
        if not window_end:
            return

        pred_id, pred_name, prob = predict_one(self._clf, self._vec, self._label_map, feature)

        # Only alert on non-normal.
        if pred_id == 0:
            return
        if prob < float(self.cfg.alert_threshold):
            return

        dk = self._dedup_key(entity_key, pred_id)
        now = time.time()
        if dk in self._dedup and (now - self._dedup[dk]) < float(self.cfg.dedup_ttl_sec):
            return
        self._dedup[dk] = now

        alert_id = stable_alert_id(entity_key, window_end, pred_id)

        error_ratio = float(feature.get("error_ratio") or 0.0)
        severity = self._severity(pred_id, prob, error_ratio)

        evidence = {
            "top_templates": feature.get("top_templates") or [],
            "template_counts": feature.get("template_counts") or {},
            "keyword_counts": feature.get("keyword_counts") or {},
            "error_examples": feature.get("error_examples") or [],
            "error_ratio": error_ratio,
            "counts": {
                "error_cnt": int(feature.get("error_cnt") or 0),
                "warn_cnt": int(feature.get("warn_cnt") or 0),
                "info_cnt": int(feature.get("info_cnt") or 0),
                "total_records": int(feature.get("total_records") or 0),
            },
        }

        a = Alert(
            alert_id=alert_id,
            created_at=utcnow_iso(),
            entity_key=entity_key,
            window_start=str(feature.get("window_start") or ""),
            window_end=window_end,
            pred_class=str(pred_name),
            pred_label_id=int(pred_id),
            prob=float(prob),
            threshold=float(self.cfg.alert_threshold),
            severity=severity,
            status="new",
            evidence=evidence,
        )

        insert_alert(self._engine, a)


def config_from_env() -> WorkerConfig:
    model_dir = Path(os.environ.get("APP_MODEL_DIR", "/models"))
    return WorkerConfig(
        kafka_bootstrap=os.environ.get("APP_KAFKA_BOOTSTRAP", "kafka:9092"),
        features_topic=os.environ.get("APP_KAFKA_FEATURES_TOPIC", "openstack.features"),
        group_id=os.environ.get("APP_KAFKA_GROUP_ID", "openstack-inference"),
        db_url=os.environ.get("APP_DB_URL", "sqlite:////data/alerts.db"),
        model_dir=model_dir,
        alert_threshold=float(os.environ.get("APP_ALERT_THRESHOLD", "0.7")),
        dedup_ttl_sec=int(os.environ.get("APP_DEDUP_TTL_SEC", "300")),
    )
