"""
Simple in-memory event bus implementation for canary testing.

Provides a minimal event bus that implements ProtocolEventBus
for testing and development scenarios.
"""

import logging
from collections import defaultdict, deque
from collections.abc import Callable
from typing import Any

from omnibase_core.models.core.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.core.model_onex_event import ModelOnexEvent


class MemoryEventBus:
    """
    Simple in-memory event bus for testing and fallback scenarios.

    Implements the essential ProtocolEventBus interface methods
    needed by MixinEventDrivenNode and canary system components.

    Uses a circular buffer for event history to prevent memory leaks.
    """

    def __init__(self, max_history_size: int = 1000):
        """
        Initialize the in-memory event bus.

        Args:
            max_history_size: Maximum number of events to keep in history.
                             Older events are automatically removed when limit is exceeded.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._event_history: deque = deque(maxlen=max_history_size)
        self._max_history_size = max_history_size
        self._is_connected = True
        self._events_published = 0
        self._events_discarded = 0

    def publish(
        self,
        event_or_envelope: ModelEventEnvelope | ModelOnexEvent | dict,
        correlation_id: str | None = None,
    ) -> bool:
        """
        Publish an event to all matching subscribers.

        Args:
            event_or_envelope: Event to publish (envelope, event, or dict)
            correlation_id: Correlation ID for tracing requests across components

        Returns:
            bool: True if published successfully
        """
        try:
            # Store event in history (circular buffer automatically discards old events)
            history_was_full = len(self._event_history) >= self._max_history_size
            self._event_history.append(event_or_envelope)

            # Track metrics
            self._events_published += 1
            if history_was_full:
                self._events_discarded += 1

            # Determine event type for routing and extract correlation_id if not provided
            event_type = None
            extracted_correlation_id = correlation_id

            if isinstance(event_or_envelope, ModelEventEnvelope):
                if hasattr(event_or_envelope, "payload") and hasattr(
                    event_or_envelope.payload,
                    "event_type",
                ):
                    event_type = event_or_envelope.payload.event_type
                # Try to extract correlation_id from envelope if not provided
                if not extracted_correlation_id and hasattr(
                    event_or_envelope,
                    "correlation_id",
                ):
                    extracted_correlation_id = event_or_envelope.correlation_id
            elif isinstance(event_or_envelope, ModelOnexEvent):
                event_type = event_or_envelope.event_type
                # Try to extract correlation_id from event if not provided
                if not extracted_correlation_id and hasattr(
                    event_or_envelope,
                    "correlation_id",
                ):
                    extracted_correlation_id = event_or_envelope.correlation_id
            elif isinstance(event_or_envelope, dict):
                event_type = event_or_envelope.get("event_type", "unknown")
                # Try to extract correlation_id from dict if not provided
                if not extracted_correlation_id:
                    extracted_correlation_id = event_or_envelope.get("correlation_id")

            if event_type:
                # Notify matching subscribers
                for pattern, subscribers in self._subscribers.items():
                    if self._matches_pattern(event_type, pattern):
                        for subscriber in subscribers:
                            try:
                                subscriber(event_or_envelope)
                            except Exception as e:
                                correlation_context = (
                                    f" [correlation_id={extracted_correlation_id}]"
                                    if extracted_correlation_id
                                    else ""
                                )
                                self.logger.error(
                                    f"Error in subscriber: {e} [event_bus=memory]{correlation_context}",
                                )

            correlation_context = (
                f" [correlation_id={extracted_correlation_id}]"
                if extracted_correlation_id
                else ""
            )
            self.logger.debug(
                f"Published event: {event_type} [event_bus=memory]{correlation_context}",
            )
            return True

        except Exception as e:
            correlation_context = (
                f" [correlation_id={extracted_correlation_id}]"
                if extracted_correlation_id
                else ""
            )
            self.logger.error(
                f"Failed to publish event: {e} [event_bus=memory]{correlation_context}",
            )
            return False

    def subscribe(self, callback: Callable, pattern: str = "*") -> bool:
        """
        Subscribe to events matching a pattern.

        Args:
            callback: Function to call when matching events occur
            pattern: Event pattern to match (supports wildcards)

        Returns:
            bool: True if subscribed successfully
        """
        try:
            self._subscribers[pattern].append(callback)
            self.logger.debug(f"Subscribed to pattern: {pattern} [event_bus=memory]")
            return True
        except Exception as e:
            self.logger.error(
                f"Failed to subscribe to {pattern}: {e} [event_bus=memory]",
            )
            return False

    def unsubscribe(self, callback: Callable, pattern: str) -> bool:
        """
        Unsubscribe from events matching a pattern.

        Args:
            callback: Function to remove from subscribers
            pattern: Event pattern to stop matching

        Returns:
            bool: True if unsubscribed successfully
        """
        try:
            if pattern in self._subscribers:
                if callback in self._subscribers[pattern]:
                    self._subscribers[pattern].remove(callback)
                    self.logger.debug(
                        f"Unsubscribed from pattern: {pattern} [event_bus=memory]",
                    )
                    return True
            return False
        except Exception as e:
            self.logger.error(
                f"Failed to unsubscribe from {pattern}: {e} [event_bus=memory]",
            )
            return False

    def is_connected(self) -> bool:
        """Check if the event bus is connected."""
        return self._is_connected

    def disconnect(self) -> None:
        """Disconnect from the event bus."""
        self._is_connected = False
        self._subscribers.clear()
        self.logger.info("Memory event bus disconnected")

    def get_event_history(self) -> list[Any]:
        """Get the history of events processed by this in-memory event bus."""
        return list(self._event_history)

    def clear_event_history(self) -> None:
        """Clear the event history and reset metrics."""
        events_cleared = len(self._event_history)
        self._event_history.clear()
        self.logger.info(
            f"Cleared {events_cleared} events from history [event_bus=memory]",
        )

    def get_subscriber_count(self) -> int:
        """Get the number of active subscribers."""
        return sum(len(subscribers) for subscribers in self._subscribers.values())

    def get_memory_stats(self) -> dict[str, Any]:
        """
        Get memory usage statistics for the event bus.

        Returns:
            Dictionary containing memory and performance metrics
        """
        return {
            "max_history_size": self._max_history_size,
            "current_history_size": len(self._event_history),
            "events_published": self._events_published,
            "events_discarded": self._events_discarded,
            "active_subscribers": self.get_subscriber_count(),
            "subscriber_patterns": list(self._subscribers.keys()),
            "memory_usage_ratio": len(self._event_history) / self._max_history_size,
            "is_history_full": len(self._event_history) >= self._max_history_size,
        }

    def resize_history(self, new_max_size: int) -> bool:
        """
        Resize the event history buffer.

        Args:
            new_max_size: New maximum size for event history

        Returns:
            bool: True if resize was successful

        Note:
            If new size is smaller than current history, oldest events are discarded.
        """
        if new_max_size <= 0:
            self.logger.error("History size must be positive")
            return False

        old_size = self._max_history_size
        old_events = list(self._event_history)

        # Create new deque with new size
        self._event_history = deque(old_events, maxlen=new_max_size)
        self._max_history_size = new_max_size

        # Update discard counter if events were lost
        events_lost = max(0, len(old_events) - new_max_size)
        self._events_discarded += events_lost

        self.logger.info(
            f"Resized event history: {old_size} -> {new_max_size}, "
            f"retained {len(self._event_history)} events, "
            f"discarded {events_lost} events [event_bus=memory]",
        )

        return True

    def _matches_pattern(self, event_type: str, pattern: str) -> bool:
        """
        Check if an event type matches a subscription pattern.

        Supports simple wildcard matching:
        - "event.*" matches "event.start", "event.end", etc.
        - "*.coordination" matches "canary.coordination", "test.coordination", etc.

        Args:
            event_type: The actual event type
            pattern: The subscription pattern

        Returns:
            bool: True if the event type matches the pattern
        """
        if pattern == event_type:
            return True

        # Simple wildcard support
        if "*" in pattern:
            # Convert pattern to regex-like matching
            pattern_parts = pattern.split("*")
            if len(pattern_parts) == 2:
                prefix, suffix = pattern_parts
                return event_type.startswith(prefix) and event_type.endswith(suffix)

        return False
