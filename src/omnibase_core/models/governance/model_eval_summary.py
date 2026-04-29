# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Eval summary model for aggregated A/B comparison statistics."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelEvalSummary(BaseModel):
    """Summary statistics for an eval report."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    total_tasks: int = Field(..., description="Total number of tasks compared", ge=0)
    onex_better_count: int = Field(
        ..., description="Tasks where ONEX improved outcomes", ge=0
    )
    onex_worse_count: int = Field(
        ..., description="Tasks where ONEX degraded outcomes", ge=0
    )
    neutral_count: int = Field(
        ..., description="Tasks with no significant difference", ge=0
    )
    avg_latency_delta_ms: float = Field(
        ..., description="Average latency delta (negative = ONEX faster)"
    )
    avg_token_delta: float = Field(
        ..., description="Average token count delta (negative = ONEX uses fewer tokens)"
    )
    avg_success_rate_on: float = Field(
        ..., description="Average success rate with ONEX ON", ge=0.0, le=1.0
    )
    avg_success_rate_off: float = Field(
        ..., description="Average success rate with ONEX OFF", ge=0.0, le=1.0
    )
    pattern_hit_rate_on: float = Field(
        ..., description="How often patterns were used when ONEX is on", ge=0.0, le=1.0
    )
