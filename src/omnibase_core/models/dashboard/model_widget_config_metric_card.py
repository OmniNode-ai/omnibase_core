"""Metric card widget configuration model.

This module defines the configuration for metric card dashboard widgets,
which display a single key performance indicator (KPI) with optional
trend comparison, color thresholds, and value formatting.

Example:
    Create a metric card with trend and thresholds::

        from omnibase_core.models.dashboard import (
            ModelWidgetConfigMetricCard,
            ModelMetricThreshold,
        )

        config = ModelWidgetConfigMetricCard(
            metric_key="error_rate",
            label="Error Rate",
            unit="%",
            value_format="percent",
            precision=2,
            show_trend=True,
            trend_key="error_rate_previous",
            thresholds=(
                ModelMetricThreshold(value=1.0, color="#22c55e", label="Good"),
                ModelMetricThreshold(value=5.0, color="#eab308", label="Warning"),
                ModelMetricThreshold(value=10.0, color="#ef4444", label="Critical"),
            ),
        )
"""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums import EnumWidgetType
from omnibase_core.models.dashboard.model_metric_threshold import ModelMetricThreshold

__all__ = ("ModelWidgetConfigMetricCard",)

#: Expected config_kind value for this widget type.
_EXPECTED_CONFIG_KIND = "metric_card"


class ModelWidgetConfigMetricCard(BaseModel):
    """Configuration for metric card dashboard widgets.

    Displays a single metric value prominently with optional formatting,
    trend indicator, color thresholds, and icon. Metric cards are ideal
    for highlighting KPIs like counts, percentages, or durations.

    The threshold system allows dynamic coloring based on the metric value,
    with thresholds checked in order (first matching threshold wins).

    Attributes:
        config_kind: Literal discriminator value, always "metric_card".
        widget_type: Widget type enum, always METRIC_CARD.
        metric_key: Data key to extract the metric value from the data source.
        label: Human-readable label displayed above/below the value.
        unit: Unit of measurement displayed after the value (e.g., "%", "ms").
        value_format: Value formatting mode - number, currency, percent, or duration.
            Aliased as "format" in JSON for API compatibility.
        precision: Decimal places to show (0-10).
        show_trend: Whether to show up/down trend indicator.
        trend_key: Data key for the comparison value when show_trend is True.
        thresholds: Tuple of threshold configs for conditional coloring.
        icon: Optional icon identifier to display with the metric.

    Raises:
        ValueError: If show_trend is True but trend_key is not provided.

    Example:
        Simple count metric::

            config = ModelWidgetConfigMetricCard(
                metric_key="active_users",
                label="Active Users",
                value_format="number",
                precision=0,
            )
    """

    model_config = ConfigDict(
        frozen=True, extra="forbid", from_attributes=True, populate_by_name=True
    )

    config_kind: Literal["metric_card"] = Field(
        default="metric_card", description="Discriminator for widget config union"
    )
    widget_type: EnumWidgetType = Field(
        default=EnumWidgetType.METRIC_CARD, description="Widget type enum value"
    )
    metric_key: str = Field(
        ..., min_length=1, description="Key to extract metric value from data"
    )
    label: str = Field(..., min_length=1, description="Metric display label")
    unit: str | None = Field(default=None, description="Unit of measurement")
    value_format: Literal["number", "currency", "percent", "duration"] = Field(
        default="number", alias="format", description="How to format the value"
    )
    precision: int = Field(default=2, ge=0, le=10, description="Decimal precision")
    show_trend: bool = Field(default=False, description="Show trend indicator")
    trend_key: str | None = Field(
        default=None, description="Key for trend comparison value"
    )
    thresholds: tuple[ModelMetricThreshold, ...] = Field(
        default=(), description="Color thresholds for the metric"
    )
    icon: str | None = Field(default=None, min_length=1, description="Icon identifier")

    @model_validator(mode="after")
    def validate_trend_key_when_show_trend(self) -> Self:
        """Validate that trend_key is set when show_trend is enabled."""
        if self.show_trend and not self.trend_key:
            raise ValueError("trend_key must be set when show_trend is enabled")
        return self

    @model_validator(mode="after")
    def validate_widget_type_config_kind_consistency(self) -> Self:
        """Validate that widget_type is consistent with config_kind.

        Ensures that the widget_type enum matches the expected config_kind
        discriminator value. widget_type=METRIC_CARD must have
        config_kind="metric_card".

        Raises:
            ValueError: If widget_type does not match config_kind.
        """
        if self.widget_type is not EnumWidgetType.METRIC_CARD:
            raise ValueError(
                f"widget_type must be METRIC_CARD for metric_card config, "
                f"got {self.widget_type.value}"
            )
        if self.config_kind != _EXPECTED_CONFIG_KIND:
            raise ValueError(
                f"config_kind must be '{_EXPECTED_CONFIG_KIND}' for METRIC_CARD widget, "
                f"got '{self.config_kind}'"
            )
        return self
