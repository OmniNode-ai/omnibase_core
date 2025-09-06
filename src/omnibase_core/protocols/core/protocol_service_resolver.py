"""
Protocol definitions for Service Resolution.

Provides abstract interfaces for service discovery and resolution
to ensure consistent implementation across different resolver types.
"""

from abc import abstractmethod
from typing import Any, Optional, Protocol, TypeVar, runtime_checkable

from omnibase_core.protocols.types.model_service_health import (
    ModelServiceHealth,
    ModelServiceHealthCollection,
)

T = TypeVar("T")


@runtime_checkable
class ProtocolServiceResolver(Protocol):
    """Protocol for service resolution and discovery."""

    @abstractmethod
    def register_service(self, service_type: type[T], instance: T) -> None:
        """
        Register a service instance.
        
        Args:
            service_type: The type/interface of the service
            instance: The service instance to register
        """
        ...

    @abstractmethod
    def get_service(self, service_type: type[T]) -> Optional[T]:
        """
        Get a service instance by type.
        
        Args:
            service_type: The type/interface of the service
            
        Returns:
            The service instance or None if not found
        """
        ...

    @abstractmethod
    def has_service(self, service_type: type[T]) -> bool:
        """
        Check if a service is registered.
        
        Args:
            service_type: The type/interface of the service
            
        Returns:
            True if the service is registered
        """
        ...

    @abstractmethod
    async def get_service_health(self, service_type: type[T]) -> ModelServiceHealth:
        """
        Get health status for a specific service.
        
        Args:
            service_type: The type/interface of the service
            
        Returns:
            Health status model for the service
        """
        ...

    @abstractmethod
    async def get_all_service_health(self) -> ModelServiceHealthCollection:
        """
        Get health status for all registered services.
        
        Returns:
            Collection of all service health statuses
        """
        ...


@runtime_checkable
class ProtocolServiceDiscovery(Protocol):
    """Protocol for service discovery operations."""

    @abstractmethod
    async def discover_services(self, service_type: Optional[str] = None) -> list[str]:
        """
        Discover available services.
        
        Args:
            service_type: Optional filter by service type
            
        Returns:
            List of discovered service identifiers
        """
        ...

    @abstractmethod
    async def register_endpoint(
        self,
        service_id: str,
        endpoint: str,
        metadata: Optional[dict[str, Any]] = None
    ) -> bool:
        """
        Register a service endpoint.
        
        Args:
            service_id: Unique service identifier
            endpoint: Service endpoint URL
            metadata: Optional service metadata
            
        Returns:
            True if registration successful
        """
        ...

    @abstractmethod
    async def deregister_endpoint(self, service_id: str) -> bool:
        """
        Deregister a service endpoint.
        
        Args:
            service_id: Service identifier to deregister
            
        Returns:
            True if deregistration successful
        """
        ...

    @abstractmethod
    async def get_endpoint(self, service_id: str) -> Optional[str]:
        """
        Get endpoint for a service.
        
        Args:
            service_id: Service identifier
            
        Returns:
            Service endpoint URL or None if not found
        """
        ...

    @abstractmethod
    async def get_service_metadata(self, service_id: str) -> Optional[dict[str, Any]]:
        """
        Get metadata for a service.
        
        Args:
            service_id: Service identifier
            
        Returns:
            Service metadata or None if not found
        """
        ...