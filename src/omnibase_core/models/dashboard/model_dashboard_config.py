# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Dashboard configuration model.

This module defines the top-level dashboard configuration container that holds
all settings for a dashboard instance, including layout, widgets, refresh
behavior, and theme preferences.

Example:
    Create a dashboard with auto-refresh and dark theme::

        from uuid import uuid4
        from omnibase_core.enums import EnumDashboardTheme
        from omnibase_core.models.dashboard import (
            ModelDashboardConfig,
            ModelDashboardLayoutConfig,
        )

        config = ModelDashboardConfig(
            dashboard_id=uuid4(),
            name="Operations Dashboard",
            description="Real-time system metrics",
            layout=ModelDashboardLayoutConfig(columns=12, row_height=120),
            refresh_interval_seconds=30,
            theme=EnumDashboardTheme.DARK,
        )
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums import EnumDashboardStatus, EnumDashboardTheme
from omnibase_core.models.dashboard.model_dashboard_layout_config import (
    ModelDashboardLayoutConfig,
)
from omnibase_core.models.dashboard.model_widget_definition import (
    ModelWidgetDefinition,
)

__all__ = ("ModelDashboardConfig",)


class ModelDashboardConfig(BaseModel):
    """Complete configuration for a dashboard instance.

    This is the top-level model that defines everything needed to render
    and operate a dashboard, including layout grid settings, widget
    definitions with their positions, refresh behavior, and theme.

    The dashboard uses a responsive grid system where widgets are placed
    by row/column coordinates and span multiple cells as needed.

    Attributes:
        dashboard_id: Unique identifier for this dashboard instance.
        name: Human-readable display name for the dashboard.
        description: Optional longer description of the dashboard purpose.
        layout: Grid layout configuration (columns, row height, gaps).
        widgets: Tuple of widget definitions with their configurations.
        refresh_interval_seconds: Auto-refresh interval in seconds, or None
            to disable auto-refresh. Must be >= 1 if specified.
        theme: Visual theme preference (light, dark, or system-following).
        initial_status: Starting lifecycle status for the dashboard.

    Example:
        Basic dashboard with two widgets::

            config = ModelDashboardConfig(
                dashboard_id=uuid4(),
                name="API Metrics",
                widgets=(widget1, widget2),
                refresh_interval_seconds=60,
            )
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
    theme: EnumDashboardTheme = Field(
        default=EnumDashboardTheme.SYSTEM, description="Dashboard theme preference"
    )

    # Status tracking (initial status only)
    initial_status: EnumDashboardStatus = Field(
        default=EnumDashboardStatus.INITIALIZING,
        description="Initial dashboard status",
    )
