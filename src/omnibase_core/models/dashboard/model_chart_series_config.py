# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Chart series configuration model."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.dashboard.model_renderer_theme_contract import (
    ModelRendererThemeContract,
)

__all__ = ("ModelChartSeriesConfig",)


class ModelChartSeriesConfig(BaseModel):
    """Configuration for a single data series in dashboard charts.

    Defines how a dataset should be rendered within a chart widget,
    including the data source key, visual styling, and chart type.

    Multiple series configs can be combined to create multi-series
    charts with different visualization styles (line, bar, area, scatter).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str = Field(..., min_length=1, description="Series display name")
    data_key: str = Field(
        ..., min_length=1, description="Key to extract data from source"
    )
    color: str | None = Field(
        default=None,
        description=(
            "Name of the ModelRendererThemeContract colour token this series "
            "resolves to (e.g. 'color_accent_primary'). A NAME, never a colour value."
        ),
    )
    series_type: Literal["line", "bar", "area", "scatter"] = Field(
        default="line", description="How to render this series"
    )

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str | None) -> str | None:
        """Validate that color names a theme colour token when provided.

        Raises:
            ValueError: If ``v`` is not a colour token of the theme contract.
        """
        if v is None:
            return None
        if not ModelRendererThemeContract.is_color_token_name(v):
            raise ValueError(
                f"'{v}' is not a colour token of ModelRendererThemeContract; a "
                f"colour field must name a theme token (e.g. 'color_accent_primary'), "
                f"and a colour value is never accepted"
            )
        return v
