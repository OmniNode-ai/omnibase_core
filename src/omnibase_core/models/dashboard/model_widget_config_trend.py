# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Trend widget configuration (OMN-21997; view kind ``trend``)."""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field, field_validator

from omnibase_core.enums.enum_widget_type import EnumWidgetType
from omnibase_core.models.dashboard.model_renderer_theme_contract import (
    ModelRendererThemeContract,
)
from omnibase_core.models.dashboard.model_widget_config_view_base import (
    ModelWidgetConfigViewBase,
)

__all__ = ["ModelWidgetConfigTrend"]


class ModelWidgetConfigTrend(ModelWidgetConfigViewBase):
    """Configuration for trend widgets. One measure's trend per row."""

    _WIDGET_TYPE: ClassVar[EnumWidgetType] = EnumWidgetType.TREND

    config_kind: Literal["trend"] = Field(
        default="trend", description="Discriminator for widget config union"
    )
    widget_type: EnumWidgetType = Field(
        default=EnumWidgetType.TREND, description="Widget type enum value"
    )
    show_axes: bool = Field(default=True, description="Show the axes")
    line_color: str | None = Field(
        default=None,
        description=(
            "Theme colour token NAME the line resolves to (e.g. "
            "'color_accent_primary'). A NAME, never a colour value."
        ),
    )

    @field_validator("line_color")
    @classmethod
    def validate_line_color(cls, value: str | None) -> str | None:
        """Validate that line_color names a theme colour token when provided.

        Raises:
            ValueError: If ``value`` is not a colour token of the theme contract.
        """
        if value is None:
            return None
        if not ModelRendererThemeContract.is_color_token_name(value):
            raise ValueError(
                f"'{value}' is not a colour token of ModelRendererThemeContract; a "
                f"colour field must name a theme token (e.g. 'color_accent_primary'), "
                f"and a colour value is never accepted"
            )
        return value
