"""
Protocol for event bus lifecycle management (ISP - Interface Segregation Principle).

This module provides the ProtocolEventBusLifecycle protocol definition
for components that need to manage event bus lifecycle, without requiring
the full ProtocolEventBus interface.

Design Principles:
- Minimal interface: Only lifecycle-related methods
- Runtime checkable: Supports duck typing with @runtime_checkable
- ISP compliant: Lifecycle management separate from publish/subscribe
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.types.typed_dict.typed_dict_event_bus_health import (
        TypedDictEventBusHealth,
    )


@runtime_checkable
class ProtocolEventBusLifecycle(Protocol):
    """
    Protocol for event bus lifecycle management.

    This is a minimal interface for components that manage event bus lifecycle.
    It follows the Interface Segregation Principle (ISP) by separating
    lifecycle concerns from publishing and subscription operations.

    Use Cases:
    - Application bootstrap/shutdown handlers
    - Health check services
    - Container lifecycle managers
    - Graceful shutdown coordinators

    Example:
        >>> class AppLifecycle:
        ...     def __init__(self, lifecycle: ProtocolEventBusLifecycle):
        ...         self.lifecycle = lifecycle
        ...
        ...     async def startup(self) -> None:
        ...         await self.lifecycle.start()
        ...
        ...     async def shutdown(self) -> None:
        ...         await self.lifecycle.shutdown()
        ...
        ...     async def check_health(self) -> bool:
        ...         health = await self.lifecycle.health_check()
        ...         return health.get("healthy", False)
    """

    async def start(self) -> None:
        """
        Start the event bus.

        Initializes connections, creates consumers/producers, and prepares
        the event bus for operation. This should be called before any
        publish or subscribe operations.

        Raises:
            OnexError: If the event bus cannot be started (connection failure,
                configuration error, etc.).

        Note:
            This method is idempotent - calling it on an already started
            event bus should have no effect.
        """
        ...

    async def shutdown(self) -> None:
        """
        Gracefully shutdown the event bus.

        Stops message consumption, flushes pending messages, and prepares
        for closing connections. Use this for graceful application shutdown.

        This method should:
        1. Stop accepting new messages
        2. Flush pending outgoing messages
        3. Complete in-flight message processing
        4. Prepare for close()

        Raises:
            OnexError: If shutdown encounters errors.

        Note:
            After shutdown(), the event bus should not accept new operations.
            Call close() after shutdown() to release resources.
        """
        ...

    async def close(self) -> None:
        """
        Close the event bus and release all resources.

        Closes all connections, releases resources, and performs final cleanup.
        After calling close(), the event bus instance should not be used.

        Raises:
            OnexError: If closing fails.

        Note:
            This method is idempotent - calling it multiple times should
            be safe. For graceful shutdown, call shutdown() before close().
        """
        ...

    async def health_check(self) -> TypedDictEventBusHealth:
        """
        Perform a health check on the event bus.

        Returns status information about the event bus health, including
        connection status, message queue depths, and any error conditions.

        Returns:
            TypedDictEventBusHealth: A TypedDict containing health information:
                - healthy: bool - Overall health status (required)
                - connected: bool - Connection to broker status (required)
                - latency_ms: float - Current latency in milliseconds (optional)
                - pending_messages: int - Number of pending outgoing messages (optional)
                - error: str - Error message if unhealthy (optional)
                - status: str - Detailed status string (optional)
                - broker_available: bool - Whether broker is available (optional)
                - consumer_lag: int - Current consumer lag (optional)

        Example:
            >>> health = await lifecycle.health_check()
            >>> if health["healthy"]:
            ...     print("Event bus is healthy")
            ... else:
            ...     print(f"Event bus unhealthy: {health.get('error')}")
        """
        ...


__all__ = ["ProtocolEventBusLifecycle"]
