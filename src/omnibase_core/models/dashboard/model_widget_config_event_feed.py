"""Event feed widget configuration model.

This module defines the configuration for event feed dashboard widgets,
which display a real-time stream of events with filtering, grouping, and
display options.

Example:
    Create an event feed for error monitoring::

        from omnibase_core.models.dashboard import (
            ModelWidgetConfigEventFeed,
            ModelEventFilter,
        )

        config = ModelWidgetConfigEventFeed(
            max_items=100,
            event_filter=ModelEventFilter(
                severity_levels=("error", "critical"),
                sources=("api", "worker"),
            ),
            show_timestamp=True,
            show_severity=True,
            auto_scroll=True,
        )
"""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums import EnumWidgetType
from omnibase_core.models.dashboard.model_event_filter import ModelEventFilter

__all__ = ("ModelWidgetConfigEventFeed",)

#: Expected config_kind value for this widget type.
_EXPECTED_CONFIG_KIND = "event_feed"


class ModelWidgetConfigEventFeed(BaseModel):
    """Configuration for event feed dashboard widgets.

    Displays a scrolling feed of events in real-time, with optional filtering
    by event type, severity, and source. Events can be displayed with
    timestamps, source information, and severity indicators.

    The ``event_filter`` field uses the alias "filter" for JSON serialization
    to match frontend conventions while avoiding Python keyword conflicts.

    Attributes:
        config_kind: Literal discriminator value, always "event_feed".
        widget_type: Widget type enum, always EVENT_FEED.
        max_items: Maximum number of events to display in the feed (1-500).
            Older events are removed when this limit is exceeded.
        event_filter: Optional filter configuration to limit which events
            are displayed. Serialized as "filter" in JSON.
        show_timestamp: Whether to display event timestamps.
        show_source: Whether to display the event source/origin.
        show_severity: Whether to show severity level indicator.
        group_by_type: Whether to group events by their type.
        auto_scroll: Whether to automatically scroll to show new events.

    Example:
        Minimal event feed showing all events::

            config = ModelWidgetConfigEventFeed(max_items=25)
    """

    model_config = ConfigDict(
        frozen=True, extra="forbid", from_attributes=True, populate_by_name=True
    )

    config_kind: Literal["event_feed"] = Field(
        default="event_feed", description="Discriminator for widget config union"
    )
    widget_type: EnumWidgetType = Field(
        default=EnumWidgetType.EVENT_FEED, description="Widget type enum value"
    )
    max_items: int = Field(
        default=50, ge=1, le=500, description="Maximum events to display"
    )
    event_filter: ModelEventFilter | None = Field(
        default=None,
        alias="filter",
        serialization_alias="filter",
        description="Event filtering configuration",
    )
    show_timestamp: bool = Field(default=True, description="Show event timestamps")
    show_source: bool = Field(default=True, description="Show event source")
    show_severity: bool = Field(default=True, description="Show severity indicator")
    group_by_type: bool = Field(default=False, description="Group events by type")
    auto_scroll: bool = Field(default=True, description="Auto-scroll to new events")

    @model_validator(mode="after")
    def validate_widget_type_config_kind_consistency(self) -> Self:
        """Validate that widget_type is consistent with config_kind.

        Ensures that the widget_type enum matches the expected config_kind
        discriminator value. widget_type=EVENT_FEED must have
        config_kind="event_feed".

        Raises:
            ValueError: If widget_type does not match config_kind.
        """
        if self.widget_type is not EnumWidgetType.EVENT_FEED:
            raise ValueError(
                f"widget_type must be EVENT_FEED for event_feed config, "
                f"got {self.widget_type.value}"
            )
        if self.config_kind != _EXPECTED_CONFIG_KIND:
            raise ValueError(
                f"config_kind must be '{_EXPECTED_CONFIG_KIND}' for EVENT_FEED widget, "
                f"got '{self.config_kind}'"
            )
        return self
