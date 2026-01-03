from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse
import json
import time
from pathlib import Path
from typing import Iterator, Tuple

from kafka import KafkaProducer


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


def main() -> None:
    p = argparse.ArgumentParser(description="Replay OpenStack logs into Kafka (merged multi-line records).")
    p.add_argument("--bootstrap", required=True, help="Kafka bootstrap servers, e.g. localhost:29092")
    p.add_argument("--topic", default="openstack.raw")
    p.add_argument("--dataset", default="sample", help="dataset_id to embed in each message")
    p.add_argument("--log", type=Path, required=True, help="Path to .log file")
    p.add_argument("--rate", type=float, default=200.0, help="Records per second (merged records)")
    p.add_argument("--max-records", type=int, default=0, help="0 means no limit")
    args = p.parse_args()

    if args.rate <= 0:
        raise ValueError("--rate must be > 0")

    producer = KafkaProducer(
        bootstrap_servers=args.bootstrap,
        value_serializer=lambda d: json.dumps(d, ensure_ascii=False).encode("utf-8"),
        key_serializer=lambda s: (s or "").encode("utf-8"),
        linger_ms=10,
        retries=3,
        acks=1,
    )

    interval = 1.0 / float(args.rate)
    sent = 0
    t0 = time.time()
    next_ts = t0

    for start_ln, end_ln, record in iter_merged_records(args.log):
        now_ms = int(time.time() * 1000)
        msg = {
            "dataset_id": args.dataset,
            "ingest_ts": now_ms,
            "start_line_no": int(start_ln),
            "end_line_no": int(end_ln),
            "raw_record": record,
        }
        # Key left empty; Spark will compute entity_key. You can also key by instance_id if you prefer.
        producer.send(args.topic, key="", value=msg)
        sent += 1

        if args.max_records and sent >= args.max_records:
            break

        # Rate control (best-effort)
        next_ts += interval
        sleep_for = next_ts - time.time()
        if sleep_for > 0:
            time.sleep(sleep_for)

        if sent % 1000 == 0:
            dt = max(time.time() - t0, 1e-6)
            print(f"sent={sent} rate={sent/dt:.1f} rec/s", flush=True)

    producer.flush(timeout=10)
    producer.close(timeout=10)
    dt = max(time.time() - t0, 1e-6)
    print(f"done sent={sent} avg_rate={sent/dt:.1f} rec/s")


if __name__ == "__main__":
    main()

