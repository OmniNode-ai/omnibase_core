# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Event feed widget configuration model."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums import EnumWidgetType
from omnibase_core.models.dashboard.model_event_filter import ModelEventFilter

__all__ = ["ModelWidgetConfigEventFeed"]


class ModelWidgetConfigEventFeed(BaseModel):
    """Event feed widget configuration.

    Displays a real-time feed of events with filtering.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    config_kind: Literal["event_feed"] = Field(
        default="event_feed", description="Discriminator for widget config union"
    )
    widget_type: EnumWidgetType = Field(
        default=EnumWidgetType.EVENT_FEED, description="Widget type enum value"
    )
    max_items: int = Field(
        default=50, ge=1, le=500, description="Maximum events to display"
    )
    filter: ModelEventFilter | None = Field(
        default=None, description="Event filtering configuration"
    )
    show_timestamp: bool = Field(default=True, description="Show event timestamps")
    show_source: bool = Field(default=True, description="Show event source")
    show_severity: bool = Field(default=True, description="Show severity indicator")
    group_by_type: bool = Field(default=False, description="Group events by type")
    auto_scroll: bool = Field(default=True, description="Auto-scroll to new events")
