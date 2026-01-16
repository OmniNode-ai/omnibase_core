"""Status grid widget configuration model.

This module defines the configuration for status grid dashboard widgets,
which display a grid of status indicators for monitoring multiple systems,
services, or components at a glance.

Example:
    Create a status grid for service health::

        from omnibase_core.models.dashboard import (
            ModelWidgetConfigStatusGrid,
            ModelStatusItemConfig,
        )

        config = ModelWidgetConfigStatusGrid(
            items=(
                ModelStatusItemConfig(key="api", label="API Server", icon="server"),
                ModelStatusItemConfig(key="db", label="Database", icon="database"),
                ModelStatusItemConfig(key="cache", label="Redis Cache", icon="cache"),
            ),
            columns=3,
            status_colors={
                "healthy": "#22c55e",
                "degraded": "#eab308",
                "down": "#ef4444",
            },
        )
"""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums import EnumWidgetType
from omnibase_core.models.dashboard.model_status_item_config import (
    ModelStatusItemConfig,
)
from omnibase_core.validation.validator_hex_color import validate_hex_color_mapping

__all__ = ("ModelWidgetConfigStatusGrid",)

#: Expected config_kind value for this widget type.
_EXPECTED_CONFIG_KIND = "status_grid"


class ModelWidgetConfigStatusGrid(BaseModel):
    """Configuration for status grid dashboard widgets.

    Displays a grid of status indicators, ideal for monitoring the health
    of multiple systems, services, or components. Each item shows a status
    value with color-coded visualization based on the configured color mapping.

    The status_colors mapping defines how status values are rendered. Any
    status value not in the mapping uses the "unknown" color (gray by default).

    Attributes:
        config_kind: Literal discriminator value, always "status_grid".
        widget_type: Widget type enum, always STATUS_GRID.
        items: Tuple of status item configurations to display in the grid.
        columns: Number of columns in the grid layout (1-12).
        show_labels: Whether to display text labels under each indicator.
        compact: Whether to use compact mode with smaller indicators.
        status_colors: Mapping of status values to hex color codes. Default
            includes "healthy" (green), "warning" (yellow), "error" (red),
            and "unknown" (gray).

    Raises:
        ValueError: If any color in status_colors is not a valid hex format.

    Example:
        Compact 4-column grid::

            config = ModelWidgetConfigStatusGrid(
                items=(item1, item2, item3, item4),
                columns=4,
                compact=True,
                show_labels=False,
            )
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    config_kind: Literal["status_grid"] = Field(
        default="status_grid", description="Discriminator for widget config union"
    )
    widget_type: EnumWidgetType = Field(
        default=EnumWidgetType.STATUS_GRID, description="Widget type enum value"
    )
    items: tuple[ModelStatusItemConfig, ...] = Field(
        default=(), description="Status items to display"
    )
    columns: int = Field(default=3, ge=1, le=12, description="Number of grid columns")
    show_labels: bool = Field(default=True, description="Show item labels")
    compact: bool = Field(default=False, description="Use compact display mode")
    status_colors: Mapping[str, str] = Field(
        default_factory=lambda: MappingProxyType(
            {
                "healthy": "#22c55e",
                "warning": "#eab308",
                "error": "#ef4444",
                "unknown": "#6b7280",
            }
        ),
        description="Status value to color mapping",
    )

    @field_validator("status_colors")
    @classmethod
    def validate_status_colors(cls, v: Mapping[str, str]) -> Mapping[str, str]:
        """Validate that all color values are valid hex color codes."""
        return validate_hex_color_mapping(v, "status")

    @model_validator(mode="after")
    def validate_widget_type_config_kind_consistency(self) -> Self:
        """Validate that widget_type is consistent with config_kind.

        Ensures that the widget_type enum matches the expected config_kind
        discriminator value. widget_type=STATUS_GRID must have
        config_kind="status_grid".

        Raises:
            ValueError: If widget_type does not match config_kind.
        """
        if self.widget_type is not EnumWidgetType.STATUS_GRID:
            raise ValueError(
                f"widget_type must be STATUS_GRID for status_grid config, "
                f"got {self.widget_type.value}"
            )
        if self.config_kind != _EXPECTED_CONFIG_KIND:
            raise ValueError(
                f"config_kind must be '{_EXPECTED_CONFIG_KIND}' for STATUS_GRID widget, "
                f"got '{self.config_kind}'"
            )
        return self
