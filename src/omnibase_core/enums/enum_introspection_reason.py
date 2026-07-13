# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""
Introspection Reason Enumeration.

Defines reason values for node introspection events, categorizing why a node
emits an introspection event for filtering, alerting, and analytics.

Thread Safety:
    All enums in this module are immutable and thread-safe.
    Enum values can be safely shared across threads without synchronization.
"""

from enum import Enum, unique


@unique
class EnumIntrospectionReason(str, Enum):
    """
    Reasons why a node emits an introspection event.

    Used by ModelNodeIntrospectionEvent to categorize introspection
    events for filtering, alerting, and analytics.

    Values:
        STARTUP: Node just started and is announcing presence.
        SHUTDOWN: Node is gracefully shutting down.
        REQUEST: Explicit request for introspection (e.g., admin query).
        HEARTBEAT: Periodic health heartbeat.
        HEALTH_CHANGE: Node health status changed.
        CAPABILITY_CHANGE: Node capabilities changed at runtime.

    Example:
        >>> reason = EnumIntrospectionReason.STARTUP
        >>> reason.is_lifecycle_event()
        True
        >>> str(EnumIntrospectionReason.HEARTBEAT)
        'heartbeat'
    """

    STARTUP = "startup"
    """Node just started and is announcing presence."""

    SHUTDOWN = "shutdown"
    """Node is gracefully shutting down."""

    REQUEST = "request"
    """Explicit request for introspection (e.g., admin query)."""

    HEARTBEAT = "heartbeat"
    """Periodic health heartbeat."""

    HEALTH_CHANGE = "health_change"
    """Node health status changed."""

    CAPABILITY_CHANGE = "capability_change"
    """Node capabilities changed at runtime."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    def is_lifecycle_event(self) -> bool:
        """
        Check if this reason represents a lifecycle event.

        Lifecycle events indicate node startup or shutdown, which are
        significant for registration and discovery workflows.

        Returns:
            True if the reason is a lifecycle event, False otherwise

        Example:
            >>> EnumIntrospectionReason.STARTUP.is_lifecycle_event()
            True
            >>> EnumIntrospectionReason.HEARTBEAT.is_lifecycle_event()
            False
        """
        return self in {
            EnumIntrospectionReason.STARTUP,
            EnumIntrospectionReason.SHUTDOWN,
        }

    def is_health_related(self) -> bool:
        """
        Check if this reason is health-related.

        Health-related reasons indicate the node is reporting its health
        status, either periodically or due to a change.

        Returns:
            True if the reason is health-related, False otherwise

        Example:
            >>> EnumIntrospectionReason.HEARTBEAT.is_health_related()
            True
            >>> EnumIntrospectionReason.REQUEST.is_health_related()
            False
        """
        return self in {
            EnumIntrospectionReason.HEARTBEAT,
            EnumIntrospectionReason.HEALTH_CHANGE,
        }

    def is_change_event(self) -> bool:
        """
        Check if this reason indicates a state change.

        Change events indicate something about the node changed that
        may require re-evaluation by the registration system.

        Returns:
            True if the reason indicates a change, False otherwise

        Example:
            >>> EnumIntrospectionReason.CAPABILITY_CHANGE.is_change_event()
            True
            >>> EnumIntrospectionReason.HEARTBEAT.is_change_event()
            False
        """
        return self in {
            EnumIntrospectionReason.HEALTH_CHANGE,
            EnumIntrospectionReason.CAPABILITY_CHANGE,
        }

    @classmethod
    def get_description(cls, reason: "EnumIntrospectionReason") -> str:
        """
        Get a human-readable description of the introspection reason.

        Args:
            reason: The introspection reason to describe

        Returns:
            A human-readable description of the reason

        Example:
            >>> EnumIntrospectionReason.get_description(
            ...     EnumIntrospectionReason.STARTUP
            ... )
            'Node just started and is announcing presence'
        """
        descriptions = {
            cls.STARTUP: "Node just started and is announcing presence",
            cls.SHUTDOWN: "Node is gracefully shutting down",
            cls.REQUEST: "Explicit request for introspection",
            cls.HEARTBEAT: "Periodic health heartbeat",
            cls.HEALTH_CHANGE: "Node health status changed",
            cls.CAPABILITY_CHANGE: "Node capabilities changed at runtime",
        }
        return descriptions.get(reason, "Unknown introspection reason")


__all__: list[str] = ["EnumIntrospectionReason"]
