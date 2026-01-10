# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Metric card widget configuration model."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums import EnumWidgetType
from omnibase_core.models.dashboard.model_metric_threshold import ModelMetricThreshold

__all__ = ["ModelWidgetConfigMetricCard"]


class ModelWidgetConfigMetricCard(BaseModel):
    """Metric card widget configuration.

    Displays a single metric value with optional trend and thresholds.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    config_kind: Literal["metric_card"] = Field(
        default="metric_card", description="Discriminator for widget config union"
    )
    widget_type: EnumWidgetType = Field(
        default=EnumWidgetType.METRIC_CARD, description="Widget type enum value"
    )
    metric_key: str = Field(..., description="Key to extract metric value from data")
    label: str = Field(..., description="Metric display label")
    unit: str | None = Field(default=None, description="Unit of measurement")
    format: Literal["number", "currency", "percent", "duration"] = Field(
        default="number", description="How to format the value"
    )
    precision: int = Field(default=2, ge=0, le=10, description="Decimal precision")
    show_trend: bool = Field(default=False, description="Show trend indicator")
    trend_key: str | None = Field(
        default=None, description="Key for trend comparison value"
    )
    thresholds: tuple[ModelMetricThreshold, ...] = Field(
        default=(), description="Color thresholds for the metric"
    )
    icon: str | None = Field(default=None, description="Icon identifier")

    @model_validator(mode="after")
    def validate_trend_key_when_show_trend(self) -> "ModelWidgetConfigMetricCard":
        """Validate that trend_key is set when show_trend is enabled."""
        if self.show_trend and not self.trend_key:
            raise ValueError("trend_key must be set when show_trend is enabled")
        return self
