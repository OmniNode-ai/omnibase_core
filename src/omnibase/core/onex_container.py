"""
ONEX Dependency Injection Container.

Protocol-driven dependency injection container that provides clean service resolution
without legacy registry dependencies.
"""

import os
from typing import Any, Dict, Optional, Type, TypeVar, Union

from omnibase.exceptions.base_onex_error import OnexError


T = TypeVar("T")


class ONEXContainer:
    """
    Protocol-driven ONEX dependency injection container.
    
    Provides clean dependency injection for ONEX tools and nodes using
    protocol-based service resolution without legacy registry coupling.
    """
    
    def __init__(self) -> None:
        """Initialize the container."""
        self._services: Dict[str, Any] = {}
        self._config: Dict[str, Any] = {}
        
    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the container with settings."""
        self._config.update(config)
        
    def register_service(self, protocol_name: str, service_instance: Any) -> None:
        """Register a service instance for a protocol."""
        self._services[protocol_name] = service_instance
        
    def get_service(self, protocol_name: str) -> Any:
        """
        Get service by protocol name.
        
        Clean protocol-based resolution only, without registry lookup.
        
        Args:
            protocol_name: Protocol interface name (e.g., "ProtocolEventBus")
            
        Returns:
            Service implementation instance
            
        Raises:
            OnexError: If service cannot be resolved
        """
        # Handle direct protocol name resolution
        if protocol_name in self._services:
            return self._services[protocol_name]
            
        # Handle common protocol shortcuts
        protocol_shortcuts = {
            "event_bus": "ProtocolEventBus",
            "logger": "ProtocolLogger",
            "health_check": "ProtocolHealthCheck",
        }
        
        # Try shortcut resolution
        if protocol_name in protocol_shortcuts:
            full_protocol_name = protocol_shortcuts[protocol_name]
            if full_protocol_name in self._services:
                return self._services[full_protocol_name]
                
        # Service not found
        raise OnexError(
            message=f"Unable to resolve service for protocol: {protocol_name}",
            error_code="SERVICE_RESOLUTION_FAILED"
        )
        
    def has_service(self, protocol_name: str) -> bool:
        """Check if service is available for protocol."""
        return protocol_name in self._services


# === CONTAINER FACTORY ===

def create_onex_container() -> ONEXContainer:
    """
    Create and configure ONEX container.
    
    Returns configured container with basic service setup.
    """
    container = ONEXContainer()
    
    # Load basic configuration from environment
    config = {
        "logging": {"level": os.getenv("LOG_LEVEL", "INFO")},
        "environment": os.getenv("ENVIRONMENT", "development"),
    }
    
    container.configure(config)
    
    return container


# === GLOBAL CONTAINER INSTANCE ===
_container: Optional[ONEXContainer] = None


def get_container() -> ONEXContainer:
    """Get or create global container instance."""
    global _container
    if _container is None:
        _container = create_onex_container()
    return _container