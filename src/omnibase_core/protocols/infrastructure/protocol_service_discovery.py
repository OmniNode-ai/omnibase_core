"""
Protocol for service discovery operations.

This module provides the ProtocolServiceDiscovery protocol which defines
the contract for service discovery implementations. It supports:
- Service registration and deregistration
- Service lookup by name or tags
- Health check integration
- Service metadata retrieval

IMPORTANT - Architecture Boundary:
    This protocol is defined in omnibase_core. Concrete implementations
    (e.g., ConsulServiceDiscovery, EtcdServiceDiscovery) belong in omnibase_infra,
    NOT in omnibase_core. This maintains clean architecture separation:

    - omnibase_core: Protocols (interfaces) only - no external dependencies
    - omnibase_infra: Concrete implementations with external library dependencies

Design Principles:
- Use typing.Protocol with @runtime_checkable for duck typing support
- Keep interfaces minimal - only define what ONEX Core actually needs
- Provide complete type hints for mypy strict mode compliance
- Support async operations for production deployments

Usage:
    from omnibase_core.protocols.infrastructure import ProtocolServiceDiscovery

    async def find_database(discovery: ProtocolServiceDiscovery) -> str | None:
        services = await discovery.discover_services("postgres")
        if services:
            return services[0]["address"]
        return None

Migration Guide:
    Step 1: Create an adapter implementing ProtocolServiceDiscovery (in omnibase_infra)
        # NOTE: This adapter implementation belongs in omnibase_infra, not omnibase_core.
        # Example location: omnibase_infra/adapters/discovery/consul_discovery_adapter.py

        import consul.aio
        from omnibase_core.protocols.infrastructure import ProtocolServiceDiscovery

        class ConsulServiceDiscoveryAdapter:
            def __init__(self, client: consul.aio.Consul):
                self._client = client

            async def discover_services(
                self, service_name: str
            ) -> list[dict[str, Any]]:
                _, services = await self._client.catalog.service(service_name)
                return [
                    {
                        "id": s["ServiceID"],
                        "name": s["ServiceName"],
                        "address": s["ServiceAddress"],
                        "port": s["ServicePort"],
                        "tags": s["ServiceTags"],
                    }
                    for s in services
                ]

    Step 2: Register via DI container
        # Import adapter from omnibase_infra:
        from omnibase_infra.adapters.discovery import ConsulServiceDiscoveryAdapter

        consul_client = consul.aio.Consul()
        adapter = ConsulServiceDiscoveryAdapter(consul_client)
        container.register_service("ProtocolServiceDiscovery", adapter)
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ProtocolServiceDiscovery(Protocol):
    """
    Protocol for service discovery operations.

    Defines the minimal interface for service discovery needed by ONEX Core.
    Implementations can wrap Consul, etcd, Kubernetes, or other service
    discovery systems.

    This protocol enables dependency inversion - components depend on
    this protocol rather than concrete discovery libraries, allowing:
    - Easier unit testing with mock implementations
    - Swapping discovery backends without code changes
    - Consistent interface across different discovery systems

    Service Metadata Format:
        Services are represented as dictionaries with these standard keys:
        - id: Unique service instance identifier
        - name: Service name
        - address: Service host/IP address
        - port: Service port number
        - tags: List of service tags for filtering
        - metadata: Additional key-value metadata (optional)

    Example:
        async def get_api_endpoints(discovery: ProtocolServiceDiscovery) -> list[str]:
            services = await discovery.discover_services("api-gateway")
            return [f"http://{s['address']}:{s['port']}" for s in services]
    """

    async def register_service(
        self,
        service_id: str,
        service_name: str,
        address: str,
        port: int,
        tags: list[str] | None = None,
        metadata: dict[str, str] | None = None,
        health_check_url: str | None = None,
        health_check_interval: str | None = None,
    ) -> bool:
        """
        Register a service with the discovery system.

        Args:
            service_id: Unique identifier for this service instance
            service_name: Name of the service (used for discovery)
            address: Host or IP address of the service
            port: Port number the service listens on
            tags: Optional list of tags for filtering/grouping
            metadata: Optional key-value metadata
            health_check_url: Optional URL for health checks
            health_check_interval: Optional interval for health checks (e.g., "10s")

        Returns:
            True if registration succeeded, False otherwise
        """
        ...

    async def deregister_service(self, service_id: str) -> bool:
        """
        Deregister a service from the discovery system.

        Args:
            service_id: Unique identifier of the service instance to deregister

        Returns:
            True if deregistration succeeded, False otherwise
        """
        ...

    async def discover_services(
        self,
        service_name: str,
        tags: list[str] | None = None,
        healthy_only: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Discover services by name and optional tags.

        Args:
            service_name: Name of the service to discover
            tags: Optional tags to filter by (services must have all tags)
            healthy_only: If True, only return healthy service instances

        Returns:
            List of service dictionaries with id, name, address, port, tags, metadata
        """
        ...

    async def get_service(self, service_id: str) -> dict[str, Any] | None:
        """
        Get a specific service instance by ID.

        Args:
            service_id: Unique identifier of the service instance

        Returns:
            Service dictionary if found, None otherwise
        """
        ...

    async def get_service_health(self, service_id: str) -> dict[str, Any]:
        """
        Get health status for a specific service.

        Args:
            service_id: Unique identifier of the service instance

        Returns:
            Health status dictionary with at minimum:
            - status: "passing", "warning", "critical", or "unknown"
            - message: Human-readable status message
            - last_check: ISO timestamp of last health check
        """
        ...

    async def list_services(self) -> list[str]:
        """
        List all registered service names.

        Returns:
            List of unique service names in the discovery system
        """
        ...

    async def watch_service(
        self,
        service_name: str,
        callback: Any,
    ) -> str:
        """
        Watch for changes to a service.

        Args:
            service_name: Name of the service to watch
            callback: Async callback function called when service changes
                     Signature: async def callback(services: list[dict[str, Any]]) -> None

        Returns:
            Watch ID that can be used to stop watching

        Note:
            Implementation details vary by backend. Some may use polling,
            others may use blocking queries or WebSocket connections.
        """
        ...

    async def stop_watch(self, watch_id: str) -> bool:
        """
        Stop watching a service.

        Args:
            watch_id: The watch ID returned from watch_service()

        Returns:
            True if the watch was stopped, False if watch_id not found
        """
        ...


__all__ = ["ProtocolServiceDiscovery"]
