# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Dashboard configuration model."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums import EnumDashboardStatus
from omnibase_core.models.dashboard.model_dashboard_layout_config import (
    ModelDashboardLayoutConfig,
)
from omnibase_core.models.dashboard.model_widget_definition import (
    ModelWidgetDefinition,
)

__all__ = ["ModelDashboardConfig"]


class ModelDashboardConfig(BaseModel):
    """Dashboard configuration.

    Defines the complete dashboard layout, widgets, and refresh behavior.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    dashboard_id: UUID = Field(..., description="Unique dashboard identifier")
    name: str = Field(..., min_length=1, description="Dashboard display name")
    description: str | None = Field(default=None, description="Dashboard description")

    # Layout
    layout: ModelDashboardLayoutConfig = Field(
        default_factory=ModelDashboardLayoutConfig,
        description="Dashboard layout configuration",
    )

    # Widgets
    widgets: tuple[ModelWidgetDefinition, ...] = Field(
        default=(), description="Widget definitions"
    )

    # Refresh (simple - no runtime timestamps in config)
    refresh_interval_seconds: int | None = Field(
        default=None,
        ge=1,
        description="Auto-refresh interval in seconds (None = disabled)",
    )

    # Theme
    theme: Literal["light", "dark", "system"] = Field(
        default="system", description="Dashboard theme preference"
    )

    # Status tracking (initial status only)
    initial_status: EnumDashboardStatus = Field(
        default=EnumDashboardStatus.INITIALIZING,
        description="Initial dashboard status",
    )
