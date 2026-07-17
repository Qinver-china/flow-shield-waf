"""Structured LLM output schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    request_id: str = ""
    note: str = ""


class RuleDraft(BaseModel):
    name: str
    mode: str = "observe"
    priority: int = 100
    site_ids: list[int] = Field(default_factory=list)
    enabled: bool = True
    conditions: dict = Field(default_factory=lambda: {"logic": "and", "conditions": []})


class AttackAnalysis(BaseModel):
    summary: str
    attack_indicators: list[str] = Field(default_factory=list)
    benign_indicators: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    suggested_rule: RuleDraft
    evidence: list[EvidenceItem] = Field(default_factory=list)
