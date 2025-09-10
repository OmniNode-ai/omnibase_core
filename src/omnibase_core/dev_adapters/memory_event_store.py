"""
In-Memory Event Store for Development and Testing.

⚠️  WARNING: DEV/TEST ONLY - NEVER USE IN PRODUCTION ⚠️

This implementation provides event storage with ordering and idempotency guarantees
for workflow event sourcing patterns.
"""

import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.core.model_onex_event import OnexEvent

logger = logging.getLogger(__name__)


class StoredEvent(BaseModel):
    """Wrapper for events in the event store with storage metadata."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    storage_id: UUID = Field(
        default_factory=uuid4, description="Unique storage identifier"
    )
    event: OnexEvent = Field(..., description="The stored event")
    stored_at: datetime = Field(
        default_factory=datetime.now, description="Storage timestamp"
    )
    sequence_number: int = Field(..., description="Global sequence number")
    stream_sequence: int = Field(..., description="Sequence within stream")
    checksum: str = Field(..., description="Event content checksum")

    def calculate_checksum(self) -> str:
        """Calculate checksum for event content only (excluding sequence numbers)."""
        import hashlib

        # Use Pydantic's JSON serialization which handles UUID objects properly
        event_json = self.event.model_dump_json()
        return hashlib.sha256(event_json.encode()).hexdigest()


class EventStream(BaseModel):
    """Represents an event stream with ordered events."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    stream_id: str = Field(..., description="Stream identifier")
    events: list[StoredEvent] = Field(
        default_factory=list, description="Ordered events in stream"
    )
    last_sequence: int = Field(default=0, description="Last sequence number in stream")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Stream creation time"
    )

    def add_event(self, event: OnexEvent, global_sequence: int) -> StoredEvent:
        """Add event to stream with sequence numbers."""
        self.last_sequence += 1

        stored_event = StoredEvent(
            event=event,
            sequence_number=global_sequence,
            stream_sequence=self.last_sequence,
            checksum="",  # Will be calculated
        )
        stored_event.checksum = stored_event.calculate_checksum()

        self.events.append(stored_event)
        return stored_event

    def get_events_from_sequence(self, from_sequence: int) -> list[StoredEvent]:
        """Get events starting from a specific sequence number."""
        return [e for e in self.events if e.stream_sequence >= from_sequence]


class InMemoryEventStore:
    """
    ⚠️  DEV/TEST ONLY - In-Memory Event Store ⚠️

    Provides event storage with:
    - Ordering guarantees (global and per-stream sequence numbers)
    - Idempotency via event ID deduplication
    - Stream-based organization
    - Event replay capabilities
    - Deterministic ordering for testing
    """

    def __init__(self, **kwargs):
        """
        Initialize in-memory event store.

        Args:
            **kwargs: Configuration options
        """
        logger.warning(
            "🚨 InMemoryEventStore: DEV/TEST ONLY - NEVER USE IN PRODUCTION 🚨"
        )

        # Event streams organized by stream ID
        self._streams: dict[str, EventStream] = {}

        # Global sequence counter for ordering
        self._global_sequence = 0

        # Event ID deduplication
        self._event_ids: set[UUID] = set()

        # Configuration
        self._max_events_per_stream = kwargs.get("max_events_per_stream", 10000)

        logger.info("✅ InMemoryEventStore initialized for development/testing")

    def _get_stream_id(self, event: OnexEvent) -> str:
        """Determine stream ID for an event."""
        # Use correlation_id for stream grouping if available
        if event.correlation_id:
            return f"correlation_{event.correlation_id}"

        # Fall back to node_id based streams
        return f"node_{event.node_id}"

    def _get_or_create_stream(self, stream_id: str) -> EventStream:
        """Get or create an event stream."""
        if stream_id not in self._streams:
            self._streams[stream_id] = EventStream(stream_id=stream_id)
            logger.debug(f"Created new event stream: {stream_id}")

        return self._streams[stream_id]

    def store_event(self, event: OnexEvent) -> StoredEvent:
        """
        Store an event with idempotency and ordering guarantees.

        Args:
            event: OnexEvent to store

        Returns:
            StoredEvent with storage metadata

        Raises:
            ValueError: If event ID already exists (idempotency violation)
        """
        # Check for duplicate event ID (idempotency)
        if event.event_id in self._event_ids:
            raise ValueError(
                f"Event ID {event.event_id} already exists (idempotency violation)"
            )

        # Determine stream for this event
        stream_id = self._get_stream_id(event)
        stream = self._get_or_create_stream(stream_id)

        # Increment global sequence
        self._global_sequence += 1

        # Store event in stream
        stored_event = stream.add_event(event, self._global_sequence)

        # Track event ID for idempotency
        self._event_ids.add(event.event_id)

        # Enforce stream size limits
        if len(stream.events) > self._max_events_per_stream:
            # Remove oldest events (simple FIFO cleanup)
            removed_event = stream.events.pop(0)
            self._event_ids.discard(removed_event.event.event_id)
            logger.warning(
                f"Removed oldest event from stream {stream_id} due to size limit"
            )

        logger.debug(
            f"📦 Stored event {event.event_id} in stream {stream_id} (seq: {stored_event.sequence_number})"
        )
        return stored_event

    def get_events_by_stream(
        self, stream_id: str, from_sequence: int = 1, limit: int | None = None
    ) -> list[StoredEvent]:
        """
        Get events from a specific stream.

        Args:
            stream_id: Stream identifier
            from_sequence: Starting sequence number
            limit: Maximum events to return

        Returns:
            List of StoredEvent objects
        """
        if stream_id not in self._streams:
            return []

        stream = self._streams[stream_id]
        events = stream.get_events_from_sequence(from_sequence)

        if limit:
            events = events[:limit]

        return events

    def get_all_events(
        self, from_global_sequence: int = 1, limit: int | None = None
    ) -> list[StoredEvent]:
        """
        Get all events across all streams in global sequence order.

        Args:
            from_global_sequence: Starting global sequence number
            limit: Maximum events to return

        Returns:
            List of StoredEvent objects ordered by global sequence
        """
        all_events = []

        for stream in self._streams.values():
            all_events.extend(stream.events)

        # Sort by global sequence number
        all_events.sort(key=lambda e: e.sequence_number)

        # Filter by sequence number
        events = [e for e in all_events if e.sequence_number >= from_global_sequence]

        if limit:
            events = events[:limit]

        return events

    def get_event_by_id(self, event_id: UUID) -> StoredEvent | None:
        """
        Get a specific event by its ID.

        Args:
            event_id: Event ID to find

        Returns:
            StoredEvent if found, None otherwise
        """
        for stream in self._streams.values():
            for stored_event in stream.events:
                if stored_event.event.event_id == event_id:
                    return stored_event

        return None

    def event_exists(self, event_id: UUID) -> bool:
        """Check if an event ID already exists (for idempotency)."""
        return event_id in self._event_ids

    def get_stream_ids(self) -> list[str]:
        """Get list of all stream IDs."""
        return list(self._streams.keys())

    def get_stream_info(self, stream_id: str) -> dict[str, Any] | None:
        """Get information about a specific stream."""
        if stream_id not in self._streams:
            return None

        stream = self._streams[stream_id]
        return {
            "stream_id": stream_id,
            "event_count": len(stream.events),
            "last_sequence": stream.last_sequence,
            "created_at": stream.created_at,
            "first_event": stream.events[0].stored_at if stream.events else None,
            "last_event": stream.events[-1].stored_at if stream.events else None,
        }

    def get_stats(self) -> dict[str, Any]:
        """Get event store statistics."""
        total_events = sum(len(stream.events) for stream in self._streams.values())

        return {
            "total_events": total_events,
            "total_streams": len(self._streams),
            "global_sequence": self._global_sequence,
            "unique_event_ids": len(self._event_ids),
            "streams": {
                stream_id: {
                    "events": len(stream.events),
                    "last_sequence": stream.last_sequence,
                }
                for stream_id, stream in self._streams.items()
            },
        }

    def clear_stream(self, stream_id: str) -> None:
        """Clear all events from a specific stream."""
        if stream_id in self._streams:
            stream = self._streams[stream_id]

            # Remove event IDs from deduplication set
            for stored_event in stream.events:
                self._event_ids.discard(stored_event.event.event_id)

            # Clear stream events
            stream.events.clear()
            stream.last_sequence = 0

            logger.info(f"🗑️  Cleared stream {stream_id}")

    def clear_all(self) -> None:
        """Clear all events from all streams."""
        self._streams.clear()
        self._event_ids.clear()
        self._global_sequence = 0

        logger.info("🗑️  Cleared all events from event store")

    # === Context Manager Support ===

    def __enter__(self) -> "InMemoryEventStore":
        """Enter synchronous context manager."""
        logger.debug("📥 Entered InMemoryEventStore context manager")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit synchronous context manager with cleanup."""
        try:
            self.clear_all()
            logger.info("🧹 InMemoryEventStore context manager cleanup complete")
        except Exception as e:
            logger.error(f"Error during context manager cleanup: {e}")

    # === File-backed option for demos (JSONL format) ===

    def save_to_jsonl(self, filepath: str | Path) -> None:
        """
        Save all events to JSONL file for demos.

        Args:
            filepath: Path to JSONL file to create
        """
        import json
        from pathlib import Path

        path = Path(filepath)
        all_events = self.get_all_events()

        with open(path, "w") as f:
            for stored_event in all_events:
                # Create JSONL record with storage metadata
                record = {
                    "storage_id": str(stored_event.storage_id),
                    "sequence_number": stored_event.sequence_number,
                    "stream_sequence": stored_event.stream_sequence,
                    "stored_at": stored_event.stored_at.isoformat(),
                    "checksum": stored_event.checksum,
                    "event": stored_event.event.model_dump(mode="json"),
                }
                f.write(json.dumps(record) + "\n")

        logger.info(f"💾 Saved {len(all_events)} events to {path}")

    def load_from_jsonl(self, filepath: str | Path) -> None:
        """
        Load events from JSONL file.

        Args:
            filepath: Path to JSONL file to load
        """
        import json
        from datetime import datetime
        from pathlib import Path

        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"JSONL file not found: {path}")

        self.clear_all()

        events_loaded = 0

        with open(path, "r") as f:
            for line in f:
                if line.strip():  # Skip empty lines
                    record = json.loads(line.strip())

                    # Reconstruct OnexEvent
                    event_data = record["event"]
                    # Handle UUID reconstruction
                    if "event_id" in event_data and isinstance(
                        event_data["event_id"], str
                    ):
                        from uuid import UUID

                        event_data["event_id"] = UUID(event_data["event_id"])
                    if (
                        "correlation_id" in event_data
                        and event_data["correlation_id"] is not None
                        and isinstance(event_data["correlation_id"], str)
                    ):
                        from uuid import UUID

                        event_data["correlation_id"] = UUID(
                            event_data["correlation_id"]
                        )
                    # Handle timestamp reconstruction
                    if "timestamp" in event_data and isinstance(
                        event_data["timestamp"], str
                    ):
                        from datetime import datetime

                        event_data["timestamp"] = datetime.fromisoformat(
                            event_data["timestamp"]
                        )

                    event = OnexEvent(**event_data)

                    # Store event (will assign new sequence numbers)
                    try:
                        self.store_event(event)
                        events_loaded += 1
                    except ValueError:
                        # Skip duplicate events
                        logger.warning(f"Skipped duplicate event {event.event_id}")

        logger.info(f"📁 Loaded {events_loaded} events from {path}")


# Global instance for development/testing
_global_dev_event_store: InMemoryEventStore | None = None


def get_dev_event_store() -> InMemoryEventStore:
    """
    Get or create the global development event store instance.

    ⚠️  DEV/TEST ONLY - NEVER USE IN PRODUCTION ⚠️

    Returns:
        InMemoryEventStore instance
    """
    global _global_dev_event_store
    if _global_dev_event_store is None:
        _global_dev_event_store = InMemoryEventStore()
        logger.info("✅ Created global development event store")
    return _global_dev_event_store
