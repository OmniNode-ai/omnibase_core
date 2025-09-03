"""
Simple in-memory event bus implementation for canary testing.

Provides a minimal event bus that implements ProtocolEventBus
for testing and fallback scenarios when Kafka is unavailable.
"""

import logging
from collections import defaultdict
from typing import Any, Callable, Dict, List

from omnibase_core.model.core.model_event_envelope import ModelEventEnvelope
from omnibase_core.model.core.model_onex_event import ModelOnexEvent


class MemoryEventBus:
    """
    Simple in-memory event bus for testing and fallback scenarios.

    Implements the essential ProtocolEventBus interface methods
    needed by MixinEventDrivenNode and canary system components.
    """

    def __init__(self):
        """Initialize the in-memory event bus."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._event_history: List[Any] = []
        self._is_connected = True

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
            # Store event in history
            self._event_history.append(event_or_envelope)

            # Determine event type for routing and extract correlation_id if not provided
            event_type = None
            extracted_correlation_id = correlation_id

            if isinstance(event_or_envelope, ModelEventEnvelope):
                if hasattr(event_or_envelope, "payload") and hasattr(
                    event_or_envelope.payload, "event_type"
                ):
                    event_type = event_or_envelope.payload.event_type
                # Try to extract correlation_id from envelope if not provided
                if not extracted_correlation_id and hasattr(
                    event_or_envelope, "correlation_id"
                ):
                    extracted_correlation_id = event_or_envelope.correlation_id
            elif isinstance(event_or_envelope, ModelOnexEvent):
                event_type = event_or_envelope.event_type
                # Try to extract correlation_id from event if not provided
                if not extracted_correlation_id and hasattr(
                    event_or_envelope, "correlation_id"
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
                                    f"Error in subscriber: {e} [event_bus=memory]{correlation_context}"
                                )

            correlation_context = (
                f" [correlation_id={extracted_correlation_id}]"
                if extracted_correlation_id
                else ""
            )
            self.logger.debug(
                f"Published event: {event_type} [event_bus=memory]{correlation_context}"
            )
            return True

        except Exception as e:
            correlation_context = (
                f" [correlation_id={extracted_correlation_id}]"
                if extracted_correlation_id
                else ""
            )
            self.logger.error(
                f"Failed to publish event: {e} [event_bus=memory]{correlation_context}"
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
                f"Failed to subscribe to {pattern}: {e} [event_bus=memory]"
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
                        f"Unsubscribed from pattern: {pattern} [event_bus=memory]"
                    )
                    return True
            return False
        except Exception as e:
            self.logger.error(
                f"Failed to unsubscribe from {pattern}: {e} [event_bus=memory]"
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

    def get_event_history(self) -> List[Any]:
        """Get the history of events processed by this in-memory event bus."""
        return self._event_history.copy()

    def clear_event_history(self) -> None:
        """Clear the event history."""
        self._event_history.clear()

    def get_subscriber_count(self) -> int:
        """Get the number of active subscribers."""
        return sum(len(subscribers) for subscribers in self._subscribers.values())

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
