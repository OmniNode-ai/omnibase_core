"""Dashboard layout grid configuration model.

This module defines the grid layout settings for dashboard widget positioning.
Dashboards use a responsive CSS Grid-like system where widgets are placed on
a configurable grid with adjustable column count, row height, and gap spacing.

Example:
    Create a compact 6-column layout::

        from omnibase_core.models.dashboard import ModelDashboardLayoutConfig

        layout = ModelDashboardLayoutConfig(
            columns=6,
            row_height=80,
            gap=8,
            responsive=True,
        )
"""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ("ModelDashboardLayoutConfig",)


class ModelDashboardLayoutConfig(BaseModel):
    """Grid layout configuration for dashboard widget positioning.

    Defines the grid structure that widgets are placed on. The grid uses
    a column-based system (similar to Bootstrap or CSS Grid) where widgets
    can span multiple columns and rows.

    Attributes:
        columns: Number of columns in the grid. Standard dashboards use 12
            columns for flexibility. Valid range: 1-24.
        row_height: Height of each grid row in pixels. Widgets spanning
            multiple rows will be row_height * height pixels tall.
            Minimum: 50px.
        gap: Spacing between widgets in pixels. Applied both horizontally
            and vertically. Default: 16px.
        responsive: When True, the grid adjusts column widths based on
            viewport size. When False, columns have fixed widths.

    Example:
        Standard 12-column responsive layout::

            layout = ModelDashboardLayoutConfig()  # Uses all defaults

        Fixed dense layout for monitoring::

            layout = ModelDashboardLayoutConfig(
                columns=24,
                row_height=60,
                gap=4,
                responsive=False,
            )
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    columns: int = Field(default=12, ge=1, le=24, description="Grid column count")
    row_height: int = Field(default=100, ge=50, description="Row height in pixels")
    gap: int = Field(default=16, ge=0, description="Gap between widgets in pixels")
    responsive: bool = Field(default=True, description="Enable responsive layout")
