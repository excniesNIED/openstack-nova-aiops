from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple


DATASET_LABELS = {
    "normal": (0, "normal"),
    "fault1": (1, "fault_vm_destroy_after_create"),
    "fault2": (2, "fault_network_dhcpoff"),
    "fault3": (3, "fault_libvirt_domain_undefine"),
}


FILENAME_TO_DATASET_ID = {
    "openstack-nova-normal-vm-create.log": "normal",
    "openstack-vm-destroy-immediately-after-create.log": "fault1",
    "openstack-nova-dhcpoff.log": "fault2",
    "openstack-nova-undefine-vm-after-create.log": "fault3",
}


DEFAULT_KEYWORDS = [
    "FlavorDiskSmallerThanImage",
    "BuildAbortException",
    "VirtualInterfaceCreateException",
    "Failed to allocate network",
    "qemu unexpectedly closed the monitor",
    "Failed to start libvirt guest",
    "Error launching a defined domain",
]


_HEAD_RE = re.compile(r"^\s*(DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL)\b")
_REQ_ID_RE = re.compile(r"\breq-[0-9a-f-]{36}\b", re.IGNORECASE)
_INSTANCE_ID_RE = re.compile(r"\binstance:\s*([0-9a-f-]{36})\b", re.IGNORECASE)
_UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE)
_IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_MAC_RE = re.compile(r"\b(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\b", re.IGNORECASE)
_ABS_PATH_RE = re.compile(r"/(?:[A-Za-z0-9._-]+/)+[A-Za-z0-9._-]+")
_LONG_NUM_RE = re.compile(r"\b\d{4,}\b")


@dataclass(frozen=True)
class ParsedRecord:
    start_line_no: int
    end_line_no: int
    level: str
    component: str
    request_id: Optional[str]
    instance_id: Optional[str]
    message: str
    normalized_message: str
    template_id: str
    raw_record: str


def iter_merged_records(path: Path) -> Iterator[Tuple[int, int, str]]:
    """
    Merge multi-line blocks (XML/Traceback) into a single record.

    A new record starts when a line matches:
      ^(DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL)\\b
    """
    start_line_no = 0
    buf: List[str] = []

    with path.open("r", encoding="utf-8", errors="replace") as f:
        for idx, line in enumerate(f, start=1):
            if _HEAD_RE.match(line):
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


def _extract_message_from_head_line(head_line: str) -> Tuple[str, str, str]:
    """
    Returns: (level, component, message)
    """
    stripped = head_line.strip()
    parts = stripped.split(None, 2)
    if len(parts) == 0:
        return "", "", stripped
    if len(parts) == 1:
        return parts[0], "", ""
    if len(parts) == 2:
        return parts[0], parts[1], ""

    level, component, remainder = parts

    # Heuristic: message is often after the last "] " context bracket.
    idx = remainder.rfind("] ")
    if idx != -1:
        message = remainder[idx + 2 :]
    else:
        message = remainder
    return level, component, message


def normalize_message(message: str) -> str:
    normalized = message
    normalized = _UUID_RE.sub("<UUID>", normalized)
    normalized = re.sub(r"\breq-<UUID>\b", "req-<UUID>", normalized, flags=re.IGNORECASE)
    normalized = _IPV4_RE.sub("<IPV4>", normalized)
    normalized = _MAC_RE.sub("<MAC>", normalized)
    normalized = _ABS_PATH_RE.sub("<PATH>", normalized)
    normalized = _LONG_NUM_RE.sub("<NUM>", normalized)
    return normalized


def compute_template_id(normalized_message: str) -> str:
    return hashlib.sha1(normalized_message.encode("utf-8", errors="ignore")).hexdigest()[:8]


def parse_record(start_line_no: int, end_line_no: int, raw_record: str) -> ParsedRecord:
    lines = raw_record.splitlines()
    head_line = lines[0] if lines else ""
    level, component, msg0 = _extract_message_from_head_line(head_line)

    # Keep continuation text as part of message for template/keyword purposes.
    if len(lines) > 1:
        message = msg0 + "\n" + "\n".join(lines[1:])
    else:
        message = msg0

    request_id_match = _REQ_ID_RE.search(raw_record)
    request_id = request_id_match.group(0) if request_id_match else None

    instance_id_match = _INSTANCE_ID_RE.search(raw_record)
    instance_id = instance_id_match.group(1) if instance_id_match else None

    normalized_message = normalize_message(message)
    template_id = compute_template_id(normalized_message)

    return ParsedRecord(
        start_line_no=start_line_no,
        end_line_no=end_line_no,
        level=(level or "").upper(),
        component=component,
        request_id=request_id,
        instance_id=instance_id,
        message=message,
        normalized_message=normalized_message,
        template_id=template_id,
        raw_record=raw_record,
    )


def infer_dataset_id_from_filename(path: Path) -> str:
    name = path.name
    if name in FILENAME_TO_DATASET_ID:
        return FILENAME_TO_DATASET_ID[name]
    raise ValueError(f"Unknown file name for dataset mapping: {name}")


def build_instance_dataset(
    log_path: Path,
    dataset_id: str,
    keywords: List[str],
    max_error_examples: int = 10,
) -> List[Dict]:
    """
    Build Plan-A samples: one sample per instance_id.
    Records without instance_id are ignored by default for semantic stability.
    """
    label_id, label_name = DATASET_LABELS[dataset_id]

    per_instance_templates: Dict[str, Counter] = {}
    per_instance_levels: Dict[str, Counter] = {}
    per_instance_keywords: Dict[str, Counter] = {}
    per_instance_lines: Dict[str, List[int]] = {}
    per_instance_error_examples: Dict[str, List[Dict]] = {}

    for start_line_no, end_line_no, merged in iter_merged_records(log_path):
        rec = parse_record(start_line_no, end_line_no, merged)
        if not rec.instance_id:
            continue

        key = rec.instance_id
        per_instance_templates.setdefault(key, Counter())[rec.template_id] += 1
        per_instance_levels.setdefault(key, Counter())[rec.level] += 1
        per_instance_keywords.setdefault(key, Counter())
        per_instance_lines.setdefault(key, []).extend([start_line_no, end_line_no])

        for kw in keywords:
            if kw in rec.message or kw in rec.normalized_message:
                per_instance_keywords[key][kw] += 1

        if rec.level == "ERROR":
            ex = per_instance_error_examples.setdefault(key, [])
            if len(ex) < max_error_examples:
                ex.append(
                    {
                        "start_line_no": rec.start_line_no,
                        "end_line_no": rec.end_line_no,
                        "component": rec.component,
                        "raw": rec.raw_record,
                    }
                )

    rows: List[Dict] = []
    for instance_id, tpl_counts in per_instance_templates.items():
        level_counts = per_instance_levels.get(instance_id, Counter())
        keyword_counts = per_instance_keywords.get(instance_id, Counter())
        line_marks = per_instance_lines.get(instance_id, [])

        start_ln = min(line_marks) if line_marks else 0
        end_ln = max(line_marks) if line_marks else 0

        total_records = sum(level_counts.values())
        error_cnt = int(level_counts.get("ERROR", 0))
        warn_cnt = int(level_counts.get("WARNING", 0) + level_counts.get("WARN", 0))
        info_cnt = int(level_counts.get("INFO", 0))
        error_ratio = (error_cnt / total_records) if total_records else 0.0

        top_templates = [tpl for tpl, _ in tpl_counts.most_common(10)]

        rows.append(
            {
                "sample_id": f"{dataset_id}#{instance_id}",
                "dataset_id": dataset_id,
                "label_id": label_id,
                "label_name": label_name,
                "entity_key": instance_id,
                "start_line_no": start_ln,
                "end_line_no": end_ln,
                "total_records": total_records,
                "error_cnt": error_cnt,
                "warn_cnt": warn_cnt,
                "info_cnt": info_cnt,
                "error_ratio": round(error_ratio, 6),
                "template_counts_json": json.dumps(dict(tpl_counts), ensure_ascii=False, sort_keys=True),
                "keyword_counts_json": json.dumps(dict(keyword_counts), ensure_ascii=False, sort_keys=True),
                "top_templates_json": json.dumps(top_templates, ensure_ascii=False),
                "error_examples_json": json.dumps(per_instance_error_examples.get(instance_id, []), ensure_ascii=False),
            }
        )

    return rows


def downsample_by_instances(rows: List[Dict], max_instances: Optional[int], seed: int) -> List[Dict]:
    if max_instances is None or max_instances <= 0 or len(rows) <= max_instances:
        return rows

    import random

    rng = random.Random(seed)
    selected = rng.sample(rows, k=max_instances)
    return selected

