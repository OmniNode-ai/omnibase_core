# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Dispatch evaluation result model."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_dispatch_verdict import EnumDispatchVerdict
from omnibase_core.models.cost import ModelCostProvenance
from omnibase_core.models.dispatch.model_model_call_record import ModelCallRecord


class ModelDispatchEvalResult(BaseModel):
    """Typed payload for per-task dispatch evaluation outcomes."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # string-id-ok: external dispatch-evaluation task identifier, not an ONEX UUID
    task_id: str = Field(description="Evaluated task identifier.", min_length=1)
    # string-id-ok: external dispatch identifier, not guaranteed to be a UUID
    dispatch_id: str = Field(description="Dispatch operation identifier.", min_length=1)
    ticket_id: str | None = Field(
        default=None,
        description="Optional ticket identifier associated with the dispatch.",
    )
    verdict: EnumDispatchVerdict = Field(description="Evaluation verdict.")
    quality_score: float | None = Field(
        default=None,
        description="Optional quality score assigned by the evaluator.",
        ge=0,
        le=1,
    )
    token_cost: int = Field(description="Rollup token cost.", ge=0)
    dollars_cost: float = Field(description="Rollup dollar cost.", ge=0)
    cost_provenance: ModelCostProvenance = Field(
        description="Validated rollup provenance for the dispatch evaluation."
    )
    model_calls: list[ModelCallRecord] = Field(
        description="Model invocations observed during evaluation."
    )
    evaluated_at: datetime = Field(description="UTC timestamp when evaluation ran.")
    eval_latency_ms: int = Field(
        description="Evaluation latency in milliseconds.", ge=0
    )
