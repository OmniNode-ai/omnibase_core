"""Widget definition model with discriminated union configuration.

This module defines the widget wrapper that combines metadata (id, title,
position) with type-specific configuration. It uses Pydantic's discriminated
union feature to support multiple widget types through a single config field.

The ``ModelWidgetConfig`` type alias is a union of all widget config types,
discriminated by the ``config_kind`` field for efficient deserialization.

Example:
    Create a chart widget definition::

        from uuid import uuid4
        from omnibase_core.models.dashboard import (
            ModelWidgetDefinition,
            ModelWidgetConfigChart,
            ModelChartSeriesConfig,
        )

        widget = ModelWidgetDefinition(
            widget_id=uuid4(),
            title="Request Latency",
            row=0,
            col=0,
            width=6,
            height=2,
            config=ModelWidgetConfigChart(
                chart_type="line",
                series=(
                    ModelChartSeriesConfig(
                        name="P50",
                        data_key="latency_p50",
                    ),
                ),
            ),
        )
"""

from collections.abc import Mapping
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.dashboard.model_widget_config_chart import (
    ModelWidgetConfigChart,
)
from omnibase_core.models.dashboard.model_widget_config_event_feed import (
    ModelWidgetConfigEventFeed,
)
from omnibase_core.models.dashboard.model_widget_config_metric_card import (
    ModelWidgetConfigMetricCard,
)
from omnibase_core.models.dashboard.model_widget_config_status_grid import (
    ModelWidgetConfigStatusGrid,
)
from omnibase_core.models.dashboard.model_widget_config_table import (
    ModelWidgetConfigTable,
)

__all__ = ("ModelWidgetDefinition", "ModelWidgetConfig")


#: Discriminated union of all widget configuration types.
#:
#: This type alias represents the union of all widget-specific configuration
#: models, using the ``config_kind`` field as the discriminator for efficient
#: parsing. Pydantic will automatically select the correct model based on
#: the ``config_kind`` value during deserialization.
#:
#: Supported config types:
#:     - ``chart``: :class:`ModelWidgetConfigChart`
#:     - ``table``: :class:`ModelWidgetConfigTable`
#:     - ``metric_card``: :class:`ModelWidgetConfigMetricCard`
#:     - ``status_grid``: :class:`ModelWidgetConfigStatusGrid`
#:     - ``event_feed``: :class:`ModelWidgetConfigEventFeed`
ModelWidgetConfig = Annotated[
    ModelWidgetConfigChart
    | ModelWidgetConfigTable
    | ModelWidgetConfigMetricCard
    | ModelWidgetConfigStatusGrid
    | ModelWidgetConfigEventFeed,
    Field(discriminator="config_kind"),
]


class ModelWidgetDefinition(BaseModel):
    """Complete widget definition with metadata, position, and configuration.

    This model wraps a type-specific widget configuration with the metadata
    and positioning information needed to place it on the dashboard grid.
    Each widget has a unique ID, display title, grid coordinates, and
    a configuration object that varies by widget type.

    The ``config`` field accepts any of the widget config types and uses
    the ``config_kind`` discriminator for efficient deserialization.

    Attributes:
        widget_id: Unique identifier for this widget instance.
        title: Display title shown in the widget header.
        config: Type-specific widget configuration (chart, table, etc.).
            The actual type is determined by the ``config_kind`` field.
        row: Starting row position in the dashboard grid (0-indexed).
        col: Starting column position in the dashboard grid (0-indexed).
        width: Number of grid columns this widget spans (1-12).
        height: Number of grid rows this widget spans (minimum 1).
        description: Optional longer description or help text.
        data_source: Optional identifier for the widget's data source.
        extra_config: Optional extension configuration as string key-value
            pairs for custom widget implementations.

    Example:
        Create a metric card at position (0, 0) spanning 3 columns::

            widget = ModelWidgetDefinition(
                widget_id=uuid4(),
                title="Active Users",
                row=0,
                col=0,
                width=3,
                height=1,
                config=ModelWidgetConfigMetricCard(
                    metric_key="active_users",
                    label="Active Users",
                    format="number",
                ),
            )
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    widget_id: UUID = Field(..., description="Unique widget identifier")
    title: str = Field(..., min_length=1, description="Widget display title")
    config: ModelWidgetConfig = Field(..., description="Widget-specific configuration")

    # Layout positioning (grid-based)
    row: int = Field(default=0, ge=0, description="Grid row position")
    col: int = Field(default=0, ge=0, description="Grid column position")
    width: int = Field(default=1, ge=1, le=12, description="Grid column span")
    height: int = Field(default=1, ge=1, description="Grid row span")

    # Optional metadata
    description: str | None = Field(default=None, description="Widget description")
    data_source: str | None = Field(default=None, description="Data source identifier")
    extra_config: Mapping[str, str] | None = Field(
        default=None, description="Extension config (string values only)"
    )
