# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Machine bay widget configuration (OMN-21997; view kind ``machine_bay``)."""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from omnibase_core.enums.enum_widget_type import EnumWidgetType
from omnibase_core.models.dashboard.model_widget_config_view_base import (
    ModelWidgetConfigViewBase,
)

__all__ = ["ModelWidgetConfigMachineBay"]


class ModelWidgetConfigMachineBay(ModelWidgetConfigViewBase):
    """Configuration for machine bay widgets. One machine bay per row."""

    _WIDGET_TYPE: ClassVar[EnumWidgetType] = EnumWidgetType.MACHINE_BAY

    config_kind: Literal["machine_bay"] = Field(
        default="machine_bay", description="Discriminator for widget config union"
    )
    widget_type: EnumWidgetType = Field(
        default=EnumWidgetType.MACHINE_BAY, description="Widget type enum value"
    )
    columns: int = Field(default=4, ge=1, le=12, description="Number of bay columns")
    show_machine_label: bool = Field(
        default=True, description="Show the machine label under the bay label"
    )
