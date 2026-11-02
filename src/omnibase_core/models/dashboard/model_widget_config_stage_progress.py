# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Stage progress widget configuration (OMN-21997; view kind ``stage_progress``)."""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import Field

from omnibase_core.enums.enum_widget_type import EnumWidgetType
from omnibase_core.models.dashboard.model_widget_config_view_base import (
    ModelWidgetConfigViewBase,
)

__all__ = ["ModelWidgetConfigStageProgress"]


class ModelWidgetConfigStageProgress(ModelWidgetConfigViewBase):
    """Configuration for stage progress widgets. Position within ordered stages, one item per row."""

    _WIDGET_TYPE: ClassVar[EnumWidgetType] = EnumWidgetType.STAGE_PROGRESS

    config_kind: Literal["stage_progress"] = Field(
        default="stage_progress", description="Discriminator for widget config union"
    )
    widget_type: EnumWidgetType = Field(
        default=EnumWidgetType.STAGE_PROGRESS, description="Widget type enum value"
    )
    show_stage_label: bool = Field(
        default=True, description="Show the name of the current stage"
    )
    show_percent: bool = Field(
        default=False, description="Show progress as a percentage of stages"
    )
