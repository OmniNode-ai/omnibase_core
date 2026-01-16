"""Event filter configuration model.

This module defines the filter configuration used in event feed widgets
to limit which events are displayed. Filters can be applied by event type,
severity level, and/or source.

Example:
    Create a filter for critical events from specific sources::

        from omnibase_core.models.dashboard import ModelEventFilter

        event_filter = ModelEventFilter(
            event_types=("error", "failure", "timeout"),
            severity_levels=("critical", "error"),
            sources=("payment-service", "auth-service"),
        )
"""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ("ModelEventFilter",)


class ModelEventFilter(BaseModel):
    """Filter configuration for event feed widgets.

    Defines criteria for filtering which events appear in an event feed.
    All filter criteria use allowlist semantics - only events matching
    the specified values are included. Empty tuples mean "include all".

    Multiple filter criteria are combined with AND logic - an event must
    match all non-empty filter criteria to be displayed.

    Attributes:
        event_types: Tuple of event type strings to include. An empty tuple
            means all event types are included. Example: ("error", "warning").
        severity_levels: Tuple of severity levels to include. An empty tuple
            means all severity levels are included. Example: ("critical", "error").
        sources: Tuple of event source identifiers to include. An empty tuple
            means all sources are included. Example: ("api", "worker", "scheduler").

    Example:
        Filter to show only error events::

            filter = ModelEventFilter(
                event_types=("error",),
            )

        No filtering (show all events)::

            filter = ModelEventFilter()  # All tuples default to empty
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    event_types: tuple[str, ...] = Field(
        default=(), description="Event types to include (empty = all)"
    )
    severity_levels: tuple[str, ...] = Field(
        default=(), description="Severity levels to include (empty = all)"
    )
    sources: tuple[str, ...] = Field(
        default=(), description="Event sources to include (empty = all)"
    )
