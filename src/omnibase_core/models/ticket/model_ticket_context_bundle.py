# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Ticket Context Bundle -- provenance-stamped, TTL-bound context artifact."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ModelTCBNormalizedIntent(BaseModel):
    repos: list[str] = Field(default_factory=list)
    modules: list[str] = Field(default_factory=list)
    capability_tags: list[str] = Field(default_factory=list)
    risk_tags: list[str] = Field(default_factory=list)


class ModelTCBIntent(BaseModel):
    raw: str
    normalized: ModelTCBNormalizedIntent


class ModelTCBProvenance(BaseModel):
    repo: str
    commit: str | None = None
    path: str | None = None


class ModelTCBEntrypoint(BaseModel):
    kind: Literal["file", "symbol"]
    ref: str
    why: str
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: dict[str, str]
    last_verified: str | None = None


class ModelTCBRelatedChange(BaseModel):
    kind: Literal["pr", "commit"]
    ref: str
    why: str
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: dict[str, str]
    last_verified: str | None = None


class ModelTCBPattern(BaseModel):
    pattern_id: str
    title: str
    why: str
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: dict[str, str]
    status: Literal["active", "deprecated"] = "active"


class ModelTCBTestRecommendation(BaseModel):
    name: str
    why: str
    confidence: float = Field(ge=0.0, le=1.0)
    provenance: dict[str, str]


class ModelTCBConstraint(BaseModel):
    type: Literal["invariant", "policy"]
    text: str
    enforced_by: list[str] = Field(default_factory=list)
    severity: Literal["error", "warning", "info"] = "error"


class ModelTCBAssumption(BaseModel):
    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    source: str


class ModelTicketContextBundle(BaseModel):
    tcb_version: str = "0.1"
    ticket_id: str
    epic_id: str | None = None
    created_at: datetime
    ttl_days: int = Field(default=7, ge=1, le=30)

    intent: ModelTCBIntent

    assumptions: list[ModelTCBAssumption] = Field(default_factory=list)
    suggested_entrypoints: list[ModelTCBEntrypoint] = Field(default_factory=list)
    related_changes: list[ModelTCBRelatedChange] = Field(default_factory=list)
    recommended_patterns: list[ModelTCBPattern] = Field(default_factory=list)
    anti_patterns: list[ModelTCBPattern] = Field(default_factory=list)
    tests_to_run: list[ModelTCBTestRecommendation] = Field(default_factory=list)
    constraints: list[ModelTCBConstraint] = Field(default_factory=list)

    @model_validator(mode="after")
    def enforce_size_caps(self) -> ModelTicketContextBundle:
        if len(self.suggested_entrypoints) > 10:
            raise ValueError(
                f"suggested_entrypoints exceeds cap of 10 (got {len(self.suggested_entrypoints)})"
            )
        if len(self.related_changes) > 10:
            raise ValueError("related_changes exceeds cap of 10")
        if len(self.recommended_patterns) > 10:
            raise ValueError("recommended_patterns exceeds cap of 10")
        if len(self.tests_to_run) > 15:
            raise ValueError("tests_to_run exceeds cap of 15")
        return self

    def is_stale(self, now: datetime | None = None) -> bool:
        """Return True if this bundle is past its TTL."""
        reference = now or datetime.now(tz=UTC)
        created = self.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        age_days = (reference - created).days
        return age_days >= self.ttl_days

    def to_markdown_summary(self) -> str:
        """Render a human-readable summary for ticket comments."""
        lines = [
            "## Ticket Context Bundle",
            "",
            "> Suggestions only -- verify before relying",
            "",
            f"**Bundle ID:** {self.ticket_id}-tcb | **Created:** {self.created_at.date()} | **TTL:** {self.ttl_days}d",
            "",
            f"**Intent:** {self.intent.raw}",
            f"**Repos:** {', '.join(self.intent.normalized.repos)}",
            f"**Risk Tags:** {', '.join(self.intent.normalized.risk_tags) or 'none'}",
            "",
        ]

        if self.suggested_entrypoints:
            lines.append("### Top Entrypoints")
            for e in self.suggested_entrypoints[:5]:
                lines.append(
                    f"- `{e.ref}` -- {e.why} *(confidence: {e.confidence:.0%})*"
                )
            lines.append("")

        if self.tests_to_run:
            lines.append("### Tests to Run")
            for t in self.tests_to_run[:8]:
                lines.append(f"- `{t.name}` -- {t.why}")
            lines.append("")

        if self.constraints:
            lines.append("### Constraints")
            for c in self.constraints:
                lines.append(f"- [{c.severity.upper()}] {c.text}")
            lines.append("")

        if self.recommended_patterns:
            lines.append("### Recommended Patterns")
            for p in self.recommended_patterns[:5]:
                lines.append(f"- **{p.title}** -- {p.why}")
            lines.append("")

        return "\n".join(lines)
