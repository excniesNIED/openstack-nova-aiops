from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, Optional, Tuple

from confluent_kafka import Producer


HEAD_PREFIXES = ("DEBUG", "INFO", "WARNING", "WARN", "ERROR", "CRITICAL")


def iter_merged_records(path: Path) -> Iterator[Tuple[int, int, str]]:
    """
    Merge multi-line blocks (Traceback / XML / long dumps) into a single record.
    A new record starts when the line begins with one of HEAD_PREFIXES (ignoring leading spaces).
    """
    start_line_no = 0
    buf: list[str] = []

    with path.open("r", encoding="utf-8", errors="replace") as f:
        for idx, line in enumerate(f, start=1):
            stripped = line.lstrip()
            is_head = any(stripped.startswith(pfx) for pfx in HEAD_PREFIXES)
            if is_head:
                if buf:
                    yield start_line_no, idx - 1, "".join(buf).rstrip("\n")
                start_line_no = idx
                buf = [line]
            else:
                if not buf:
                    start_line_no = idx
                    buf = [line]
                else:
                    buf.append(line)

    if buf:
        yield start_line_no, start_line_no + len(buf) - 1, "".join(buf).rstrip("\n")


@dataclass(frozen=True)
class ReplayConfig:
    kafka_bootstrap: str
    raw_topic: str
    allowed_log_dir: Path
    default_rate: float


class ReplayController:
    def __init__(self, cfg: ReplayConfig):
        self.cfg = cfg
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

        self._lock = threading.Lock()
        self._running = False
        self._started_at: Optional[float] = None
        self._finished_at: Optional[float] = None
        self._sent = 0
        self._last_error: Optional[str] = None
        self._dataset_id: str = "sample"
        self._log_path: Optional[str] = None
        self._rate: float = float(cfg.default_rate)
        self._loop: bool = False
        self._max_records: int = 0

    def start(
        self,
        *,
        dataset_id: str,
        log_name: str,
        rate: Optional[float] = None,
        loop: bool = False,
        max_records: int = 0,
    ) -> None:
        with self._lock:
            if self._running:
                return

            log_path = self._resolve_log(log_name)
            self._stop.clear()
            self._running = True
            self._started_at = time.time()
            self._finished_at = None
            self._sent = 0
            self._last_error = None
            self._dataset_id = dataset_id
            self._log_path = str(log_path)
            self._rate = float(rate if rate is not None else self.cfg.default_rate)
            self._loop = bool(loop)
            self._max_records = int(max_records or 0)

            self._thread = threading.Thread(target=self._run, name="ReplayController", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        t = self._thread
        if t:
            t.join(timeout=5)

    def status(self) -> Dict[str, object]:
        with self._lock:
            return {
                "running": self._running,
                "dataset_id": self._dataset_id,
                "log_path": self._log_path,
                "rate": self._rate,
                "loop": self._loop,
                "max_records": self._max_records,
                "sent_records": self._sent,
                "started_at": self._iso(self._started_at),
                "finished_at": self._iso(self._finished_at),
                "last_error": self._last_error,
            }

    def list_logs(self) -> Dict[str, str]:
        base = self.cfg.allowed_log_dir
        if not base.exists() or not base.is_dir():
            return {}
        out: Dict[str, str] = {}
        for p in sorted(base.glob("*.log")):
            out[p.name] = str(p)
        return out

    def _resolve_log(self, log_name: str) -> Path:
        name = (log_name or "").strip()
        if not name:
            raise ValueError("log_name is required")

        base = self.cfg.allowed_log_dir.resolve()
        resolved = (base / name).resolve()
        if base not in resolved.parents and resolved != base:
            raise ValueError("log_name resolves outside allowed directory")
        if not resolved.exists() or not resolved.is_file():
            raise ValueError(f"log not found: {name}")
        return resolved

    @staticmethod
    def _iso(ts: Optional[float]) -> Optional[str]:
        if ts is None:
            return None
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))

    def _set_done(self, *, err: Optional[str] = None) -> None:
        with self._lock:
            self._running = False
            self._finished_at = time.time()
            if err:
                self._last_error = err

    def _inc_sent(self, n: int = 1) -> None:
        with self._lock:
            self._sent += n

    def _run(self) -> None:
        st = self.status()
        dataset_id = str(st["dataset_id"])
        log_path = Path(str(st["log_path"]))
        rate = float(st["rate"])
        loop = bool(st["loop"])
        max_records = int(st["max_records"])

        if rate < 0:
            rate = 0

        producer = Producer(
            {
                "bootstrap.servers": self.cfg.kafka_bootstrap,
                "linger.ms": 10,
                "message.send.max.retries": 3,
                "acks": 1,
            }
        )

        try:
            interval = (1.0 / rate) if rate > 0 else 0.0
            sent = 0
            next_ts = time.time()

            while not self._stop.is_set():
                for start_ln, end_ln, record in iter_merged_records(log_path):
                    if self._stop.is_set():
                        break

                    now_ms = int(time.time() * 1000)
                    msg = {
                        "dataset_id": dataset_id,
                        "ingest_ts": now_ms,
                        "start_line_no": int(start_ln),
                        "end_line_no": int(end_ln),
                        "raw_record": record,
                    }
                    producer.produce(
                        self.cfg.raw_topic,
                        key=b"",
                        value=json.dumps(msg, ensure_ascii=False).encode("utf-8"),
                    )
                    producer.poll(0)
                    sent += 1
                    self._inc_sent(1)

                    if max_records and sent >= max_records:
                        self._stop.set()
                        break

                    if interval > 0:
                        next_ts += interval
                        sleep_for = next_ts - time.time()
                        if sleep_for > 0:
                            time.sleep(sleep_for)

                if not loop:
                    break

            producer.flush(10)
            self._set_done()
        except Exception as e:
            try:
                producer.flush(5)
            except Exception:
                pass
            self._set_done(err=str(e))
        finally:
            try:
                producer.flush(5)
            except Exception:
                pass


def replay_config_from_env() -> ReplayConfig:
    explicit = os.environ.get("APP_REPLAY_LOG_DIR")
    candidates = [Path(explicit)] if explicit else [Path("/opt/workspace"), Path.cwd(), Path.cwd().parent]
    allowed_dir = next((p for p in candidates if p.exists() and p.is_dir() and any(p.glob("*.log"))), candidates[0])
    return ReplayConfig(
        kafka_bootstrap=os.environ.get("APP_KAFKA_BOOTSTRAP", "kafka:9092"),
        raw_topic=os.environ.get("APP_KAFKA_RAW_TOPIC", "openstack.raw"),
        allowed_log_dir=allowed_dir,
        default_rate=float(os.environ.get("APP_REPLAY_RATE", "50")),
    )
