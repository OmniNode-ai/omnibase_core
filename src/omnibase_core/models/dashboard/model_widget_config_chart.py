"""Chart widget configuration model.

This module defines the configuration for chart-based dashboard widgets,
supporting line, bar, area, pie, and scatter visualizations. Charts can
display multiple data series with customizable axes and styling.

Example:
    Create a multi-series line chart::

        from omnibase_core.models.dashboard import (
            ModelWidgetConfigChart,
            ModelChartSeriesConfig,
            ModelChartAxisConfig,
        )

        config = ModelWidgetConfigChart(
            chart_type="line",
            series=(
                ModelChartSeriesConfig(name="CPU", data_key="cpu", color="#3b82f6"),
                ModelChartSeriesConfig(name="Memory", data_key="memory", color="#10b981"),
            ),
            x_axis=ModelChartAxisConfig(label="Time"),
            y_axis=ModelChartAxisConfig(label="Usage %", min_value=0, max_value=100),
            show_legend=True,
        )
"""

from typing import ClassVar, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums import EnumWidgetType
from omnibase_core.models.dashboard.model_chart_axis_config import ModelChartAxisConfig
from omnibase_core.models.dashboard.model_chart_series_config import (
    ModelChartSeriesConfig,
)

__all__ = ("ModelWidgetConfigChart",)

#: Expected config_kind value for this widget type.
_EXPECTED_CONFIG_KIND = "chart"


class ModelWidgetConfigChart(BaseModel):
    """Configuration for chart-type dashboard widgets.

    Defines how a chart widget renders data with one or more series and
    optional axis configurations. Supports multiple chart types including
    line graphs, bar charts, area charts, pie charts, and scatter plots.

    Data-driven chart types (line, bar, area, scatter) require at least one
    series configuration. Pie charts derive their segments from the data
    directly without explicit series configuration.

    Attributes:
        config_kind: Literal discriminator value, always "chart".
        widget_type: Widget type enum, always CHART.
        chart_type: The visualization style - line, bar, area, pie, or scatter.
        series: Tuple of series configurations defining each data line/bar.
            Required for line, bar, area, and scatter charts.
        x_axis: Optional X-axis configuration for labels and ranges.
        y_axis: Optional Y-axis configuration for labels and ranges.
        show_legend: Whether to display the legend identifying series.
        stacked: Whether to stack series values (for bar/area charts).

    Raises:
        ValueError: If a data-driven chart type has no series configured.

    Example:
        Stacked bar chart::

            config = ModelWidgetConfigChart(
                chart_type="bar",
                series=(series1, series2),
                stacked=True,
            )
    """

    # Chart types that require data series configuration
    DATA_CHART_TYPES: ClassVar[frozenset[str]] = frozenset(
        {"line", "bar", "area", "scatter"}
    )

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
    def validate_series_for_data_charts(self) -> Self:
        """Validate that data-driven chart types have at least one series."""
        if self.chart_type in self.DATA_CHART_TYPES and not self.series:
            raise ValueError(
                f"Chart type '{self.chart_type}' requires at least one series configuration"
            )
        return self

    @model_validator(mode="after")
    def validate_widget_type_config_kind_consistency(self) -> Self:
        """Validate that widget_type is consistent with config_kind.

        Ensures that the widget_type enum matches the expected config_kind
        discriminator value. widget_type=CHART must have config_kind="chart".

        Raises:
            ValueError: If widget_type does not match config_kind.
        """
        if self.widget_type is not EnumWidgetType.CHART:
            raise ValueError(
                f"widget_type must be CHART for chart config, got {self.widget_type.value}"
            )
        if self.config_kind != _EXPECTED_CONFIG_KIND:
            raise ValueError(
                f"config_kind must be '{_EXPECTED_CONFIG_KIND}' for CHART widget, "
                f"got '{self.config_kind}'"
            )
        return self
