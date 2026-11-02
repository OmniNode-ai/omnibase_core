# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Drawer detail widget configuration (OMN-21997; view kind ``drawer_detail``)."""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from omnibase_core.enums.enum_widget_type import EnumWidgetType
from omnibase_core.models.dashboard.model_widget_config_view_base import (
    ModelWidgetConfigViewBase,
)

__all__ = ["ModelWidgetConfigDrawerDetail"]


class ModelWidgetConfigDrawerDetail(ModelWidgetConfigViewBase):
    """Configuration for drawer detail widgets. Detail entries in an expandable drawer."""

    _WIDGET_TYPE: ClassVar[EnumWidgetType] = EnumWidgetType.DRAWER_DETAIL

    config_kind: Literal["drawer_detail"] = Field(
        default="drawer_detail", description="Discriminator for widget config union"
    )
    widget_type: EnumWidgetType = Field(
        default=EnumWidgetType.DRAWER_DETAIL, description="Widget type enum value"
    )
    open_by_default: bool = Field(
        default=False, description="Open the drawer when the view loads"
    )
