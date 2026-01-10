# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Chart widget configuration model."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums import EnumWidgetType
from omnibase_core.models.dashboard.model_chart_axis_config import ModelChartAxisConfig
from omnibase_core.models.dashboard.model_chart_series_config import (
    ModelChartSeriesConfig,
)

__all__ = ["ModelWidgetConfigChart"]


class ModelWidgetConfigChart(BaseModel):
    """Chart widget configuration.

    Defines how a chart widget renders data with series and axes.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    config_kind: Literal["chart"] = Field(
        default="chart", description="Discriminator for widget config union"
    )
    widget_type: EnumWidgetType = Field(
        default=EnumWidgetType.CHART, description="Widget type enum value"
    )
    chart_type: Literal["line", "bar", "area", "pie", "scatter"] = Field(
        default="line", description="Primary chart visualization type"
    )
    series: tuple[ModelChartSeriesConfig, ...] = Field(
        default=(), description="Chart series configurations"
    )
    x_axis: ModelChartAxisConfig | None = Field(
        default=None, description="X-axis configuration"
    )
    y_axis: ModelChartAxisConfig | None = Field(
        default=None, description="Y-axis configuration"
    )
    show_legend: bool = Field(default=True, description="Show chart legend")
    stacked: bool = Field(default=False, description="Stack series values")

    @model_validator(mode="after")
    def validate_series_for_data_charts(self) -> "ModelWidgetConfigChart":
        """Validate that data-driven chart types have at least one series."""
        data_chart_types = {"line", "bar", "area", "scatter"}
        if self.chart_type in data_chart_types and not self.series:
            raise ValueError(
                f"Chart type '{self.chart_type}' requires at least one series configuration"
            )
        return self
