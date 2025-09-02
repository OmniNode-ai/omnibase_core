"""
Canary Node Group Container

Provides proper dependency injection for all canary nodes in omnibase-core.
Implements duck typing for protocol resolution per ONEX standards.

This is a reference implementation based on omnibase_3 infrastructure patterns,
adapted for omnibase-core architecture with temporary service implementations.

Per user requirements:
- "it should be get_service("ProtocolEventBus") and we should have a onexcontainer
  with all depenenceies at the root of the tool group"
- "Everything needs to be resolved by duck typing"
- "the work for getting The instance of the event bus should be in there not in
  each base class. that's dumb"
"""

import types
from typing import TypeVar

from omnibase_core.core.onex_container import ONEXContainer
from omnibase_core.utils.generation.utility_schema_loader import UtilitySchemaLoader

T = TypeVar("T")


from omnibase_core.core.services.event_bus_service.v1_0_0.event_bus_service import (
    EventBusService,
)
from omnibase_core.core.services.event_bus_service.v1_0_0.models.model_event_bus_config import (
    ModelEventBusConfig,
)


def create_infrastructure_container() -> ONEXContainer:
    """
    Create infrastructure container with all shared dependencies.

    Per user requirements:
    - "it should be get_service("ProtocolEventBus") and we should have a onexcontainer
      with all depenenceies at the root of the tool group"
    - "Everything needs to be resolved by duck typing"

    Returns:
        Configured ONEXContainer with infrastructure dependencies
    """
    # Create base ONEX container
    container = ONEXContainer()

    # Set up all shared dependencies for infrastructure tools
    _setup_infrastructure_dependencies(container)

    # Bind custom get_service method that handles our infrastructure services
    _bind_infrastructure_get_service_method(container)

    return container


def _setup_infrastructure_dependencies(container: ONEXContainer):
    """Set up all dependencies needed by infrastructure canary nodes."""

    # Event Bus - Use in-memory implementation for omnibase-core
    from omnibase_core.nodes.canary.utils.memory_event_bus import MemoryEventBus

    event_bus = MemoryEventBus()

    # Event Bus Service - simplified for in-memory usage
    event_bus_config = ModelEventBusConfig(
        enable_lifecycle_events=True,
        enable_introspection_publishing=True,
        auto_resolve_event_bus=False,  # Not needed for in-memory
        suppress_connection_errors=True,
        use_broadcast_envelopes=True,
        enable_event_caching=False,  # Not needed for in-memory
    )
    event_bus_service = EventBusService(config=event_bus_config)

    # Minimal Metadata Loader - simplified for Pydantic model usage
    from omnibase_core.nodes.canary.utils.minimal_metadata_loader import (
        MinimalMetadataLoader,
    )

    schema_loader = MinimalMetadataLoader()

    # Register services in the container's service registry
    _register_service(container, "event_bus", event_bus)
    _register_service(container, "ProtocolEventBus", event_bus)
    _register_service(container, "event_bus_service", event_bus_service)
    _register_service(container, "schema_loader", schema_loader)
    _register_service(container, "ProtocolSchemaLoader", schema_loader)


def _register_service(container: ONEXContainer, service_name: str, service_instance):
    """Register a service in the container for later retrieval."""
    # Store in the container's provider registry
    if not hasattr(container, "_service_registry"):
        container._service_registry = {}
    container._service_registry[service_name] = service_instance


def _bind_infrastructure_get_service_method(container: ONEXContainer):
    """Bind custom get_service method to infrastructure container."""

    def get_service(
        self,
        protocol_type_or_name: type[T] | str,
        service_name: str | None = None,
    ) -> T:
        """
        Infrastructure-aware get_service method.

        Handles duck typing for infrastructure protocols:
        - get_service("ProtocolEventBus") -> EventBusClient
        - get_service("ProtocolSchemaLoader") -> SchemaLoader
        - get_service("event_bus") -> EventBusClient
        """
        # Handle string-only calls like get_service("event_bus")
        if isinstance(protocol_type_or_name, str):
            service_name = protocol_type_or_name

        # Check our infrastructure service registry first
        if hasattr(self, "_service_registry") and service_name:
            if service_name in self._service_registry:
                return self._service_registry[service_name]

        # Handle protocol type resolution by name
        if hasattr(protocol_type_or_name, "__name__"):
            protocol_name = protocol_type_or_name.__name__
            if (
                hasattr(self, "_service_registry")
                and protocol_name in self._service_registry
            ):
                return self._service_registry[protocol_name]

        # If not found, raise descriptive error
        msg = (
            f"Service '{service_name or protocol_type_or_name}' not found in infrastructure container. "
            f"Available services: {list(getattr(self, '_service_registry', {}).keys())}"
        )
        raise KeyError(
            msg,
        )

    # Bind the method to the container instance
    container.get_service = types.MethodType(get_service, container)
