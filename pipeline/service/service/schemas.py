from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class FeatureMessage(BaseModel):
    entity_key: str
    window_start: str
    window_end: str
    template_counts: Dict[str, int] = Field(default_factory=dict)
    keyword_counts: Dict[str, int] = Field(default_factory=dict)
    error_examples: List[Dict[str, Any]] = Field(default_factory=list)
    error_cnt: int = 0
    warn_cnt: int = 0
    info_cnt: int = 0
    total_records: int = 0
    error_ratio: float = 0.0


class AlertOut(BaseModel):
    alert_id: str
    created_at: str
    entity_key: str
    window_start: str
    window_end: str
    pred_class: str
    pred_label_id: int
    prob: float
    threshold: float
    severity: str
    status: str
    evidence: Dict[str, Any]


@dataclass(frozen=True)
class ModelArtifacts:
    label_map: Dict[int, str]

