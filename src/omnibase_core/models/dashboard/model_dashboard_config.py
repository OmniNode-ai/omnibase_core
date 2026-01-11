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

from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
            to disable auto-refresh. Minimum 1s for dev/testing scenarios;
            production deployments should use 5-30s.
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
    # NOTE: 1-second minimum allows rapid refresh for development, debugging, and
    # real-time monitoring scenarios. Production deployments should typically use
    # 5-30 seconds to balance data freshness with server/network load.
    refresh_interval_seconds: int | None = Field(
        default=None,
        ge=1,  # 1s minimum for dev/test; production should use 5-30s
        description="Auto-refresh interval in seconds (None = disabled). "
        "Minimum 1s supported for development and real-time debugging; "
        "production deployments should use 5-30s to balance freshness with load.",
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

    @model_validator(mode="after")
    def validate_widget_widths(self) -> Self:
        """Ensure all widget widths fit within dashboard grid columns.

        Validates that no widget spans more columns than available in the
        dashboard grid layout. This prevents invalid configurations where
        widgets would overflow the grid boundaries.

        Returns:
            Self for chaining.

        Raises:
            ValueError: If any widget's width exceeds the layout columns.
        """
        if self.layout and self.widgets:
            max_cols = self.layout.columns
            for widget in self.widgets:
                if widget.width > max_cols:
                    raise ValueError(
                        f"Widget '{widget.widget_id}' width ({widget.width}) exceeds "
                        f"dashboard grid columns ({max_cols})"
                    )
        return self
