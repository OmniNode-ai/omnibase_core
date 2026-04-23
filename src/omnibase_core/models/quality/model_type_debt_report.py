# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ModelTypeDebtReport — final envelope emitted by both ADK eval tracks.

Shared output schema for Track A (ADK) and Track B (omnimarket POC).
Includes the prioritized findings, tool discriminator, latency, LLM
call count, and a marginal inference-cost estimate (USD).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.quality.model_type_debt_priority import ModelTypeDebtPriority


class ModelTypeDebtReport(BaseModel):
    """Final report envelope emitted by the ADK-eval harness for one track."""

    repo: str = Field(
        ...,
        min_length=1,
        description="Name of the repo the report was generated against.",
    )
    generated_at: datetime = Field(
        ...,
        description="Timestamp when the report was generated (UTC).",
    )
    findings_total: int = Field(
        ...,
        ge=0,
        description="Total number of mypy findings fed into the scorer.",
    )
    findings_prioritized: list[ModelTypeDebtPriority] = Field(
        default_factory=list,
        description="Priority output from the scorer.",
    )
    tool: Literal["adk", "omnimarket_node"] = Field(
        ...,
        description="Which track produced this report.",
    )
    latency_seconds: float = Field(
        ...,
        ge=0.0,
        description="Wall-clock latency of the scoring invocation in seconds.",
    )
    llm_calls: int = Field(
        ...,
        ge=0,
        description="Count of LLM calls the track made (Track B = 1; Track A may fan out).",
    )
    estimated_cost_usd: float = Field(
        ...,
        ge=0.0,
        description="Marginal per-run LLM inference cost in USD (excludes hardware/power).",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    @model_validator(mode="after")
    def _check_unique_finding_refs(self) -> ModelTypeDebtReport:
        seen: set[str] = set()
        for p in self.findings_prioritized:
            if p.finding_ref in seen:
                msg = (
                    f"Duplicate finding_ref in findings_prioritized: {p.finding_ref!r}"
                )
                raise ValueError(msg)
            seen.add(p.finding_ref)
        return self


__all__ = ["ModelTypeDebtReport"]
