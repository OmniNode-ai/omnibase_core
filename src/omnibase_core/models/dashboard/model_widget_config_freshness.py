# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Freshness widget configuration (OMN-21997; view kind ``freshness``)."""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from omnibase_core.enums.enum_widget_type import EnumWidgetType
from omnibase_core.models.dashboard.model_widget_config_view_base import (
    ModelWidgetConfigViewBase,
)

__all__ = ["ModelWidgetConfigFreshness"]


class ModelWidgetConfigFreshness(ModelWidgetConfigViewBase):
    """Configuration for freshness widgets. One feed's freshness per row."""

    _WIDGET_TYPE: ClassVar[EnumWidgetType] = EnumWidgetType.FRESHNESS

    config_kind: Literal["freshness"] = Field(
        default="freshness", description="Discriminator for widget config union"
    )
    widget_type: EnumWidgetType = Field(
        default=EnumWidgetType.FRESHNESS, description="Widget type enum value"
    )
    show_age: bool = Field(
        default=True, description="Show the age of the last observation"
    )
