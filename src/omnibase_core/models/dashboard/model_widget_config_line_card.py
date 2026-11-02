# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Line card widget configuration (OMN-21997; view kind ``line_card``)."""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from omnibase_core.enums.enum_widget_type import EnumWidgetType
from omnibase_core.models.dashboard.model_widget_config_view_base import (
    ModelWidgetConfigViewBase,
)

__all__ = ["ModelWidgetConfigLineCard"]


class ModelWidgetConfigLineCard(ModelWidgetConfigViewBase):
    """Configuration for line card widgets: one production line per row."""

    _WIDGET_TYPE: ClassVar[EnumWidgetType] = EnumWidgetType.LINE_CARD

    config_kind: Literal["line_card"] = Field(
        default="line_card", description="Discriminator for widget config union"
    )
    widget_type: EnumWidgetType = Field(
        default=EnumWidgetType.LINE_CARD, description="Widget type enum value"
    )
    show_detail: bool = Field(
        default=True, description="Show each row's detail text under its status"
    )
