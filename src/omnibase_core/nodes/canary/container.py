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

from omnibase_core.core.onex_container import ModelONEXContainer
from omnibase_core.utils.generation.utility_schema_loader import UtilitySchemaLoader

T = TypeVar("T")


from omnibase_core.core.services.event_bus_service.v1_0_0.event_bus_service import (
    EventBusService,
)
from omnibase_core.core.services.event_bus_service.v1_0_0.models.model_event_bus_config import (
    ModelEventBusConfig,
)


def create_infrastructure_container() -> ModelONEXContainer:
    """
    Create infrastructure container with all shared dependencies.

    Per user requirements:
    - "it should be get_service("ProtocolEventBus") and we should have a onexcontainer
      with all depenenceies at the root of the tool group"
    - "Everything needs to be resolved by duck typing"

    Returns:
        Configured ModelONEXContainer with infrastructure dependencies
    """
    # Create base ONEX container
    container = ModelONEXContainer()

    # Set up all shared dependencies for infrastructure tools
    _setup_infrastructure_dependencies(container)

    # Bind custom get_service method that handles our infrastructure services
    _bind_infrastructure_get_service_method(container)

    return container


def _setup_infrastructure_dependencies(container: ModelONEXContainer):
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


def _register_service(
    container: ModelONEXContainer, service_name: str, service_instance
):
    """Register a service in the container for later retrieval."""
    # Store in the container's provider registry
    if not hasattr(container, "_service_registry"):
        container._service_registry = {}
    container._service_registry[service_name] = service_instance


def _bind_infrastructure_get_service_method(container: ModelONEXContainer):
    """Bind custom get_service method to infrastructure container."""

    def get_service(
        self,
        protocol_type_or_name: type[T] | str,
        service_name: str | None = None,
    ) -> T:
        """
        Infrastructure-aware get_service method with comprehensive input validation.

        Handles duck typing for infrastructure protocols:
        - get_service("ProtocolEventBus") -> EventBusClient
        - get_service("ProtocolSchemaLoader") -> SchemaLoader
        - get_service("event_bus") -> EventBusClient

        Args:
            protocol_type_or_name: Protocol type class or service name string
            service_name: Optional service name override

        Returns:
            Requested service instance

        Raises:
            ValueError: If inputs are invalid (None, empty, wrong type)
            KeyError: If requested service is not found in registry
        """
        # Input validation
        if protocol_type_or_name is None:
            raise ValueError("protocol_type_or_name cannot be None")

        if isinstance(protocol_type_or_name, str):
            if not protocol_type_or_name.strip():
                raise ValueError("protocol_type_or_name cannot be empty string")
            service_name = protocol_type_or_name.strip()
        elif not (
            hasattr(protocol_type_or_name, "__name__")
            or callable(protocol_type_or_name)
        ):
            raise ValueError(
                f"protocol_type_or_name must be a string or type, got {type(protocol_type_or_name)}"
            )

        # Validate service_name if provided
        if service_name is not None:
            if not isinstance(service_name, str):
                raise ValueError(
                    f"service_name must be string or None, got {type(service_name)}"
                )
            if not service_name.strip():
                raise ValueError("service_name cannot be empty string")
            service_name = service_name.strip()

        # Ensure service registry exists
        if not hasattr(self, "_service_registry"):
            self._service_registry = {}

        # Check our infrastructure service registry first
        if service_name and service_name in self._service_registry:
            return self._service_registry[service_name]

        # Handle protocol type resolution by name
        if hasattr(protocol_type_or_name, "__name__"):
            protocol_name = protocol_type_or_name.__name__
            if protocol_name in self._service_registry:
                return self._service_registry[protocol_name]

        # Generate helpful error message
        available_services = list(self._service_registry.keys())
        search_term = service_name or getattr(
            protocol_type_or_name, "__name__", str(protocol_type_or_name)
        )

        # Suggest similar service names if available
        suggestions = []
        if available_services:
            search_lower = search_term.lower()
            suggestions = [
                svc
                for svc in available_services
                if search_lower in svc.lower() or svc.lower().startswith(search_lower)
            ]

        error_msg = f"Service '{search_term}' not found in infrastructure container."
        if available_services:
            error_msg += f" Available services: {available_services}"
        if suggestions:
            error_msg += f". Did you mean: {suggestions}?"
        else:
            error_msg += " No services are currently registered."

        raise KeyError(error_msg)

    # Bind the method to the container instance
    container.get_service = types.MethodType(get_service, container)
