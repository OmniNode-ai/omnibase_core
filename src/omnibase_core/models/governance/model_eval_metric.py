# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Eval metric model for a single metric observation from an eval run."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.governance.enum_eval_metric_type import EnumEvalMetricType


class ModelEvalMetric(BaseModel):
    """A single metric observation from an eval run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    metric_type: EnumEvalMetricType = Field(..., description="Type of metric")
    value: float = Field(..., description="Measured value")
    unit: str = Field(
        ..., description="Unit of measurement (e.g., ms, count, ratio)", max_length=50
    )
