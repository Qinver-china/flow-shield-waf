"""Structured LLM output schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


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
    create_rule: bool = False
    suggested_rule: RuleDraft | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_rule(self) -> "AttackAnalysis":
        if self.create_rule and self.suggested_rule is None:
            raise ValueError("create_rule=true 时必须提供 suggested_rule")
        if not self.create_rule:
            self.suggested_rule = None
        return self
