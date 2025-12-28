"""ONEX-compatible security event collection model for audit trails."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_security_event_type import EnumSecurityEventType
from omnibase_core.errors import ModelOnexError
from omnibase_core.models.security.model_security_summaries import (
    ModelEventStatistics,
    ModelEventTimeRange,
)
from omnibase_core.types.type_serializable_value import SerializedDict

if TYPE_CHECKING:
    from omnibase_core.models.security.model_security_event import ModelSecurityEvent


class ModelSecurityEventCollection(BaseModel):
    """Collection of security events for audit trails."""

    model_config = ConfigDict(validate_assignment=True, extra="forbid")
    MAX_EVENTS: ClassVar[int] = 10000
    MAX_RECENT_EVENTS: ClassVar[int] = 1000
    MAX_QUERY_LIMIT: ClassVar[int] = 1000
    events: list[ModelSecurityEvent] = Field(
        default_factory=list,
        description="List of security events",
        max_length=MAX_EVENTS,
    )
    collection_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this collection",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this collection was created",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this collection was last updated",
    )
    description: str | None = Field(
        default=None, description="Description of this collection"
    )
    max_events: int = Field(
        default=MAX_EVENTS,
        description="Maximum number of events this collection can hold",
        ge=1,
        le=MAX_EVENTS,
    )
    auto_prune: bool = Field(
        default=True, description="Automatically prune old events when limit is reached"
    )
    retention_days: int | None = Field(
        default=None,
        description="Number of days to retain events (None = retain forever)",
        ge=1,
    )

    @field_validator("events")
    @classmethod
    def validate_events(cls, v: list[ModelSecurityEvent]) -> list[ModelSecurityEvent]:
        """Validate events list."""
        if len(v) > cls.MAX_EVENTS:
            raise ModelOnexError(
                message=(
                    f"Events list contains {len(v)} events, which exceeds the maximum "
                    f"allowed limit of {cls.MAX_EVENTS}. Consider using auto_prune=True "
                    "or manually removing old events before adding more."
                ),
                error_code=EnumCoreErrorCode.PARAMETER_OUT_OF_RANGE,
            )
        return v

    @field_validator("retention_days")
    @classmethod
    def validate_retention_days(cls, v: int | None) -> int | None:
        """Validate retention days."""
        if v is not None and v < 1:
            raise ModelOnexError(
                message=(
                    f"retention_days must be at least 1, got {v}. "
                    "Set to None to retain events indefinitely, or specify a positive "
                    "number of days for automatic event expiration."
                ),
                error_code=EnumCoreErrorCode.PARAMETER_OUT_OF_RANGE,
            )
        return v

    def add_event(self, event: ModelSecurityEvent) -> None:
        """Add a security event to the collection."""
        if len(self.events) >= self.max_events:
            if self.auto_prune:
                self._prune_oldest_events()
            else:
                raise ModelOnexError(
                    message=(
                        f"Cannot add event: collection has reached its maximum capacity "
                        f"of {self.max_events} events and auto_prune is disabled. "
                        "Enable auto_prune=True to automatically remove old events, "
                        "or manually call remove_old_events() or clear_events() first."
                    ),
                    error_code=EnumCoreErrorCode.INVALID_STATE,
                )
        self.events.append(event)
        self.updated_at = datetime.now(UTC)

    def get_recent_events(self, limit: int = 10) -> list[ModelSecurityEvent]:
        """Get the most recent security events."""
        if limit <= 0:
            raise ModelOnexError(
                message=(
                    f"limit must be a positive integer, got {limit}. "
                    "Specify how many recent events to retrieve (e.g., limit=10)."
                ),
                error_code=EnumCoreErrorCode.PARAMETER_OUT_OF_RANGE,
            )
        if limit > self.MAX_RECENT_EVENTS:
            raise ModelOnexError(
                message=(
                    f"limit value {limit} exceeds maximum allowed value of "
                    f"{self.MAX_RECENT_EVENTS}. Reduce the limit or use pagination "
                    "for retrieving large numbers of events."
                ),
                error_code=EnumCoreErrorCode.PARAMETER_OUT_OF_RANGE,
            )
        sorted_events = sorted(self.events, key=lambda e: e.timestamp, reverse=True)
        return sorted_events[:limit]

    def count_events(self) -> int:
        """Get the total number of events in the collection."""
        return len(self.events)

    def get_events_by_type(
        self, event_type: EnumSecurityEventType
    ) -> list[ModelSecurityEvent]:
        """Get events of a specific type."""
        return [event for event in self.events if event.event_type == event_type]

    def get_events_by_user(self, user_id: UUID) -> list[ModelSecurityEvent]:
        """Get events for a specific user."""
        if not user_id:
            raise ModelOnexError(
                message=(
                    "user_id parameter is required and cannot be empty. "
                    "Provide a valid UUID to filter events by user."
                ),
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )
        return [event for event in self.events if event.user_id == user_id]

    def get_events_by_time_range(
        self, start_time: datetime | None = None, end_time: datetime | None = None
    ) -> list[ModelSecurityEvent]:
        """Get events within a specific time range."""
        if start_time and end_time and (start_time >= end_time):
            raise ModelOnexError(
                message=(
                    f"start_time ({start_time.isoformat()}) must be before "
                    f"end_time ({end_time.isoformat()}). Swap the values or adjust "
                    "the time range to ensure start_time < end_time."
                ),
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
            )
        filtered_events = self.events
        if start_time:
            filtered_events = [e for e in filtered_events if e.timestamp >= start_time]
        if end_time:
            filtered_events = [e for e in filtered_events if e.timestamp <= end_time]
        return filtered_events

    def get_events_by_severity(
        self, severity_levels: list[str]
    ) -> list[ModelSecurityEvent]:
        """Get events with specific status levels (severity proxy)."""
        if not severity_levels:
            raise ModelOnexError(
                message=(
                    "severity_levels list cannot be empty. Provide at least one "
                    "severity level to filter by (e.g., ['critical', 'high', 'medium'])."
                ),
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )
        return [event for event in self.events if event.status.value in severity_levels]

    def get_events_by_node(self, node_id: UUID) -> list[ModelSecurityEvent]:
        """Get events for a specific node."""
        if not node_id:
            raise ModelOnexError(
                message=(
                    "node_id parameter is required and cannot be empty. "
                    "Provide a valid UUID to filter events by node."
                ),
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )
        return [
            event for event in self.events if getattr(event, "node_id", None) == node_id
        ]

    def search_events(self, query: str) -> list[ModelSecurityEvent]:
        """Search events by content (case-insensitive)."""
        if not query:
            raise ModelOnexError(
                message=(
                    "query parameter is required and cannot be empty. "
                    "Provide a search term to find matching events."
                ),
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )
        query_lower = query.lower()
        matching_events = []
        for event in self.events:
            searchable_content = [
                getattr(event, "description", ""),
                getattr(event, "user_id", ""),
                getattr(event, "node_id", ""),
                getattr(event, "details", ""),
            ]
            for content in searchable_content:
                if content and query_lower in str(content).lower():
                    matching_events.append(event)
                    break
        return matching_events

    def get_event_statistics(self) -> ModelEventStatistics:
        """Get statistics about the events in this collection."""
        if not self.events:
            return ModelEventStatistics(
                total_events=0,
                event_types={},
                severity_distribution={},
                users_involved=[],
                nodes_involved=[],
                time_range=None,
            )
        event_types: dict[str, int] = {}
        severity_distribution: dict[str, int] = {}
        users_involved: set[UUID] = set()
        nodes_involved: set[UUID] = set()
        timestamps: list[datetime] = []
        for event in self.events:
            event_type = (
                event.event_type.value
                if hasattr(event.event_type, "value")
                else str(event.event_type)
            )
            event_types[event_type] = event_types.get(event_type, 0) + 1
            severity = getattr(event, "severity", "unknown")
            severity_distribution[severity] = severity_distribution.get(severity, 0) + 1
            if hasattr(event, "user_id") and event.user_id:
                users_involved.add(event.user_id)
            if hasattr(event, "node_id") and event.node_id:
                nodes_involved.add(event.node_id)
            timestamps.append(event.timestamp)
        time_range: ModelEventTimeRange | None = None
        if timestamps:
            time_range = ModelEventTimeRange(
                earliest=min(timestamps).isoformat(),
                latest=max(timestamps).isoformat(),
            )
        return ModelEventStatistics(
            total_events=len(self.events),
            event_types=event_types,
            severity_distribution=severity_distribution,
            users_involved=sorted(users_involved),
            nodes_involved=sorted(nodes_involved),
            time_range=time_range,
        )

    def clear_events(self) -> None:
        """Clear all events from the collection."""
        self.events.clear()
        self.updated_at = datetime.now(UTC)

    def remove_old_events(self, cutoff_date: datetime) -> int:
        """Remove events older than the cutoff date. Returns number of events removed."""
        original_count = len(self.events)
        self.events = [event for event in self.events if event.timestamp >= cutoff_date]
        removed_count = original_count - len(self.events)
        if removed_count > 0:
            self.updated_at = datetime.now(UTC)
        return removed_count

    def _prune_oldest_events(self) -> None:
        """Remove oldest events when collection is full."""
        if len(self.events) < self.max_events:
            return
        sorted_events = sorted(self.events, key=lambda e: e.timestamp)
        prune_count = max(1, len(self.events) // 10)
        self.events = sorted_events[prune_count:]
        self.updated_at = datetime.now(UTC)

    def apply_retention_policy(self) -> int:
        """Apply retention policy and remove expired events. Returns number of events removed."""
        if self.retention_days is None:
            return 0
        cutoff_date = datetime.now(UTC) - timedelta(days=self.retention_days)
        return self.remove_old_events(cutoff_date)

    def export_events(self, format_type: str = "dict") -> list[SerializedDict]:
        """Export events in specified format."""
        if format_type not in ["dict", "json"]:
            raise ModelOnexError(
                message=(
                    f"format_type '{format_type}' is not supported. "
                    "Must be one of: 'dict' (Python dictionaries) or 'json' "
                    "(JSON-serializable format with ISO datetime strings)."
                ),
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )
        event_data: list[SerializedDict] = []
        for event in self.events:
            event_dict = event.model_dump()
            for key, value in event_dict.items():
                if isinstance(value, datetime):
                    event_dict[key] = value.isoformat()
            event_data.append(event_dict)
        return event_data

    def __len__(self) -> int:
        """Return the number of events in the collection."""
        return len(self.events)

    def __contains__(self, event: ModelSecurityEvent) -> bool:
        """Check if an event is in the collection."""
        return event in self.events

    def __str__(self) -> str:
        """Human-readable representation."""
        return f"SecurityEventCollection[{len(self.events)} events, created: {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}]"
