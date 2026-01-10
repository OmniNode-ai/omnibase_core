# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Status grid widget configuration model."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums import EnumWidgetType
from omnibase_core.models.dashboard.model_status_item_config import (
    ModelStatusItemConfig,
)

__all__ = ["ModelWidgetConfigStatusGrid"]


class ModelWidgetConfigStatusGrid(BaseModel):
    """Status grid widget configuration.

    Displays a grid of status indicators for multiple items.
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
    status_colors: dict[str, str] = Field(
        default_factory=lambda: {
            "healthy": "#22c55e",
            "warning": "#eab308",
            "error": "#ef4444",
            "unknown": "#6b7280",
        },
        description="Status value to color mapping",
    )
