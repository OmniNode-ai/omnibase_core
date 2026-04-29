# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Eval metric model for a single metric observation from an eval run."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.governance.enum_eval_metric_type import EnumEvalMetricType

_RATIO_METRICS = frozenset(
    {EnumEvalMetricType.SUCCESS_RATE, EnumEvalMetricType.PATTERN_HIT_RATE}
)
_COUNT_METRICS = frozenset(
    {
        EnumEvalMetricType.TOKEN_COUNT,
        EnumEvalMetricType.ERROR_COUNT,
        EnumEvalMetricType.RETRY_COUNT,
    }
)


class ModelEvalMetric(BaseModel):
    """A single metric observation from an eval run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    metric_type: EnumEvalMetricType = Field(..., description="Type of metric")
    value: float = Field(..., description="Measured value")
    unit: str = Field(
        ..., description="Unit of measurement (e.g., ms, count, ratio)", max_length=50
    )

    @model_validator(mode="after")
    def validate_metric_contract(self) -> ModelEvalMetric:
        if self.metric_type in _RATIO_METRICS and not (0.0 <= self.value <= 1.0):
            raise ValueError(
                f"{self.metric_type} must be in [0.0, 1.0], got {self.value}"
            )
        if self.metric_type in _COUNT_METRICS and self.value < 0:
            raise ValueError(
                f"{self.metric_type} must be non-negative, got {self.value}"
            )
        return self
