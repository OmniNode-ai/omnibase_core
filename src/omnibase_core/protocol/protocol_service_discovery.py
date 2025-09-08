"""
Protocol for Service Discovery abstraction.

Provides a clean interface for service discovery systems (Consul, etcd, etc.)
with proper fallback strategies and error handling.
"""

from typing import Protocol, runtime_checkable

from omnibase_core.core.common_types import ModelScalarValue
from omnibase_core.model.service.model_service_health import ModelServiceHealth


@runtime_checkable
class ProtocolServiceDiscovery(Protocol):
    """
    Protocol for service discovery systems.

    Abstracts service registration, discovery, and health checking
    from specific implementations like Consul, etcd, or in-memory fallbacks.
    """

    async def register_service(
        self,
        service_name: str,
        service_id: str,
        host: str,
        port: int,
        metadata: dict[str, ModelScalarValue],
        health_check_url: str | None = None,
        tags: list[str] | None = None,
    ) -> bool:
        """
        Register a service with the discovery system.

        Args:
            service_name: Name of the service
            service_id: Unique identifier for this service instance
            host: Host where service is running
            port: Port where service is listening
            health_check_url: Optional URL for health checks
            tags: Optional list of service tags
            metadata: Required service metadata as ModelScalarValue objects

        Returns:
            True if registration successful, False otherwise
        """
        ...

    async def deregister_service(self, service_id: str) -> bool:
        """
        Deregister a service from the discovery system.

        Args:
            service_id: Unique identifier of service to deregister

        Returns:
            True if deregistration successful, False otherwise
        """
        ...

    async def discover_services(
        self,
        service_name: str,
        healthy_only: bool = True,
    ) -> list[dict[str, ModelScalarValue]]:
        """
        Discover instances of a service.

        Args:
            service_name: Name of service to discover
            healthy_only: If True, return only healthy instances

        Returns:
            List of service instance information
        """
        ...

    async def get_service_health(self, service_id: str) -> ModelServiceHealth:
        """
        Get health status of a specific service instance.

        Args:
            service_id: Unique identifier of service

        Returns:
            Service health information
        """
        ...

    async def set_key_value(self, key: str, value: str) -> bool:
        """
        Set a key-value pair in the service discovery store.

        Args:
            key: Key to set
            value: Value to store

        Returns:
            True if successful, False otherwise
        """
        ...

    async def get_key_value(self, key: str) -> str | None:
        """
        Get value for a key from the service discovery store.

        Args:
            key: Key to retrieve

        Returns:
            Value if found, None if not found
        """
        ...

    async def delete_key(self, key: str) -> bool:
        """
        Delete a key from the service discovery store.

        Args:
            key: Key to delete

        Returns:
            True if successful, False otherwise
        """
        ...

    async def list_keys(self, prefix: str = "") -> list[str]:
        """
        List keys with optional prefix filter.

        Args:
            prefix: Optional prefix to filter keys

        Returns:
            List of matching keys
        """
        ...

    async def health_check(self) -> bool:
        """
        Check if the service discovery system is healthy.

        Returns:
            True if healthy, False otherwise
        """
        ...

    async def close(self) -> None:
        """
        Clean up resources and close connections.
        """
        ...
