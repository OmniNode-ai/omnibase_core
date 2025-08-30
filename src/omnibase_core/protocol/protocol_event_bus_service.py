#!/usr/bin/env python3
"""
Protocol for Event Bus Service

Defines the required interface that all event bus service implementations must follow.
This ensures consistency and prevents runtime errors from missing methods.
"""

from typing import Any, Protocol


class ProtocolEventBusService(Protocol):
    """
    Protocol defining the required interface for event bus service implementations.

    All event bus service classes must implement these methods to ensure:
    - Consistent lifecycle management
    - Proper shutdown handling
    - Standard event bus access
    - Service status monitoring

    This protocol prevents runtime errors like missing shutdown() methods.
    """

    def get_event_bus(self) -> Any:
        """
        Get the event bus instance for publishing and subscribing to events.

        Returns:
            The event bus instance (e.g., ToolEventBusInMemory, EventBusAdapter)
        """
        ...

    def shutdown(self) -> None:
        """
        Gracefully shutdown the event bus service.

        This method must:
        - Clean up all connections
        - Stop any running threads
        - Release resources
        - Handle shutdown errors gracefully
        """
        ...

    @property
    def is_running(self) -> bool:
        """
        Check if the event bus service is currently running.

        Returns:
            True if service is active, False otherwise
        """
        ...

    def get_node_count(self) -> int:
        """
        Get the number of nodes connected to this event bus service.

        Returns:
            Count of connected nodes
        """
        ...

    def list_nodes(self) -> list[str]:
        """
        List the names of all nodes connected to this event bus service.

        Returns:
            List of node names
        """
        ...


class ProtocolEventBusAdapter(Protocol):
    """
    Protocol for event bus adapters that wrap HTTP/network event bus services.

    This is for lightweight adapters that connect to external event bus services.
    """

    def publish(self, event: Any) -> bool:
        """
        Publish an event to the event bus.

        Args:
            event: The event to publish

        Returns:
            True if successful, False otherwise
        """
        ...

    def subscribe(self, handler: Any) -> bool:
        """
        Subscribe to events with a handler function.

        Args:
            handler: Function to handle received events

        Returns:
            True if subscription successful, False otherwise
        """
        ...

    def unsubscribe(self, handler: Any) -> bool:
        """
        Unsubscribe a handler from events.

        Args:
            handler: Handler function to remove

        Returns:
            True if unsubscription successful, False otherwise
        """
        ...

    @property
    def is_healthy(self) -> bool:
        """
        Check if the adapter connection is healthy.

        Returns:
            True if connection is working, False otherwise
        """
        ...

    def close(self) -> None:
        """
        Close the adapter connection and clean up resources.
        """
        ...


# Type aliases for common event bus service types
EventBusServiceType = ProtocolEventBusService
EventBusAdapterType = ProtocolEventBusAdapter
