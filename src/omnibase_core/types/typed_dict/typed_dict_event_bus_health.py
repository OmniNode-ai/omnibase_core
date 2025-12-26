"""TypedDict for event bus health check results.

This TypedDict defines the structure returned by ProtocolEventBusLifecycle.health_check(),
providing typed access to event bus health status information.

Related:
    - ProtocolEventBusLifecycle: Protocol that defines health_check()
    - PR #241: TypedDict for health_check() return types

.. versionadded:: 0.4.0
"""

from __future__ import annotations

from typing import NotRequired, TypedDict


class TypedDictEventBusHealth(TypedDict):
    """TypedDict for event bus health check results.

    This TypedDict defines the contract for health check results from
    ProtocolEventBusLifecycle.health_check().

    Required Fields:
        healthy: Overall health status of the event bus.
        connected: Whether the event bus is connected to the broker.

    Optional Fields:
        latency_ms: Current latency in milliseconds.
        pending_messages: Number of pending outgoing messages.
        error: Error message if unhealthy.
        status: Detailed status string (e.g., "connected", "disconnected").
        broker_available: Whether the broker is available.
        consumer_lag: Current consumer lag (messages behind).
    """

    healthy: bool
    connected: bool
    latency_ms: NotRequired[float]
    pending_messages: NotRequired[int]
    error: NotRequired[str]
    status: NotRequired[str]
    broker_available: NotRequired[bool]
    consumer_lag: NotRequired[int]


__all__ = ["TypedDictEventBusHealth"]
