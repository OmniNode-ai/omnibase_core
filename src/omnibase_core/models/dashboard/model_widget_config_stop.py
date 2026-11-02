# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Stop widget configuration (OMN-21997; view kind ``stop``)."""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from omnibase_core.enums.enum_widget_type import EnumWidgetType
from omnibase_core.models.dashboard.model_widget_config_view_base import (
    ModelWidgetConfigViewBase,
)

__all__ = ["ModelWidgetConfigStop"]


class ModelWidgetConfigStop(ModelWidgetConfigViewBase):
    """Configuration for stop widgets. One stoppage per row."""

    _WIDGET_TYPE: ClassVar[EnumWidgetType] = EnumWidgetType.STOP

    config_kind: Literal["stop"] = Field(
        default="stop", description="Discriminator for widget config union"
    )
    widget_type: EnumWidgetType = Field(
        default=EnumWidgetType.STOP, description="Widget type enum value"
    )
    show_duration: bool = Field(
        default=True, description="Show how long the stop has lasted"
    )
