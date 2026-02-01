"""
Container Service Resolver

Service resolution logic for ONEX container instances.
Handles the get_service method functionality that gets lost during
dependency-injector DynamicContainer transformation.
"""

from collections.abc import Callable
from typing import Any, TypeVar, cast
from uuid import NAMESPACE_DNS, UUID, uuid5

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.container.model_service import ModelService
from omnibase_core.models.errors.model_onex_error import ModelOnexError

T = TypeVar("T")


def _get_container_callable(
    container: ModelONEXContainer, attr_name: str
) -> Callable[[], Any] | None:
    """
    Get callable attribute from container with proper typing.

    Dependency-injector dynamically adds callable attributes to containers.
    This helper wraps getattr with runtime validation and proper typing.

    Args:
        container: The ONEX container instance
        attr_name: Name of the attribute to retrieve

    Returns:
        The callable if found and valid, None otherwise
    """
    value = getattr(container, attr_name, None)
    if value is None:
        return None
    if not callable(value):
        return None
    # NOTE(OMN-1302): getattr() returns Any; validated callable at runtime above.
    return cast(Callable[[], Any], value)


def _generate_service_uuid(service_name: str) -> UUID:
    """
    Generate deterministic UUID for service name.

    Uses UUID5 with DNS namespace to create consistent UUIDs
    for the same service name across invocations.

    Args:
        service_name: Name of the service

    Returns:
        Deterministic UUID for the service
    """
    return uuid5(NAMESPACE_DNS, f"omnibase.service.{service_name}")


def create_get_service_method(
    _container: ModelONEXContainer,
) -> Callable[..., ModelService]:
    """
    Create get_service method for container instance.

    This method is lost during dependency-injector DynamicContainer transformation,
    so we recreate it and bind it to the container instance.

    Args:
        container: The container instance to bind the method to

    Returns:
        Bound method for container.get_service()
    """

    def get_service(
        self: ModelONEXContainer,
        protocol_type_or_name: type[T] | str,
        service_name: str | None = None,
    ) -> ModelService:
        """
        Get service instance for protocol type or service name.

        Restored method for DynamicContainer instances.
        """
        # Handle string-only calls like get_service("event_bus")
        if isinstance(protocol_type_or_name, str) and service_name is None:
            service_name = protocol_type_or_name

            # Handle special service name "event_bus"
            if service_name == "event_bus":
                # create_hybrid_event_bus() - REMOVED: function no longer exists
                return ModelService(
                    service_id=_generate_service_uuid("event_bus"),
                    service_name="event_bus",
                    service_type="hybrid_event_bus",
                    protocol_name="ProtocolEventBus",
                    health_status="healthy",
                )

            # For other string names, try to resolve them in registry_map
            protocol_type = None  # Will be handled below
        else:
            protocol_type = protocol_type_or_name

        # Handle protocol type resolution
        if protocol_type and hasattr(protocol_type, "__name__"):
            protocol_name = protocol_type.__name__

            # Contract-driven service resolution for protocols
            if protocol_name == "ProtocolEventBus":
                # create_hybrid_event_bus() - REMOVED: function no longer exists
                return ModelService(
                    service_id=_generate_service_uuid("event_bus_protocol"),
                    service_name="event_bus",
                    service_type="hybrid_event_bus",
                    protocol_name=protocol_name,
                    health_status="healthy",
                )
            if protocol_name == "ProtocolConsulClient":
                getattr(self, "consul_client", lambda: None)()
                return ModelService(
                    service_id=_generate_service_uuid("consul_client"),
                    service_name="consul_client",
                    service_type="consul_client",
                    protocol_name=protocol_name,
                    health_status="healthy",
                )
            if protocol_name == "ProtocolVaultClient":
                # Vault client resolution following the same pattern as consul client
                # Assumes container has a vault_client() method available
                if hasattr(self, "vault_client"):
                    self.vault_client()
                    return ModelService(
                        service_id=_generate_service_uuid("vault_client"),
                        service_name="vault_client",
                        service_type="vault_client",
                        protocol_name=protocol_name,
                        health_status="healthy",
                    )
                msg = f"Vault client not available in container: {protocol_name}"
                raise ModelOnexError(
                    msg,
                    EnumCoreErrorCode.REGISTRY_RESOLUTION_FAILED,
                )

        # Handle generation tool registries with registry pattern
        if service_name:
            registry_map = _build_registry_map(self)
            if service_name in registry_map:
                registry_map[service_name]()
                return ModelService(
                    service_id=_generate_service_uuid(service_name),
                    service_name=service_name,
                    service_type="registry_service",
                    health_status="healthy",
                )

        # No fallbacks - fail fast for unknown services

        # If no protocol_type and service not found, raise error
        msg = f"Unable to resolve service: {service_name}"
        raise ModelOnexError(
            msg,
            error_code=EnumCoreErrorCode.REGISTRY_RESOLUTION_FAILED,
        )

    return get_service


def _build_registry_map(
    container: ModelONEXContainer,
) -> dict[str, Callable[[], Any]]:
    """
    Build registry mapping for service resolution.

    Note: These attributes are dynamically added by dependency-injector.
    Uses _get_container_callable to safely retrieve and validate callables,
    filtering out None values to ensure all dict values are callable.

    Args:
        container: The ONEX container instance

    Returns:
        Dictionary mapping service names to their callable resolvers.
        Only includes services that have valid callables registered.
    """
    # List of all registry/service names to resolve
    registry_names = [
        # Generation tool registries
        "contract_validator_registry",
        "model_regenerator_registry",
        "contract_driven_generator_registry",
        "workflow_generator_registry",
        "ast_generator_registry",
        "file_writer_registry",
        "introspection_generator_registry",
        "protocol_generator_registry",
        "node_stub_generator_registry",
        "ast_renderer_registry",
        "reference_resolver_registry",
        "type_import_registry_registry",
        "python_class_builder_registry",
        "subcontract_loader_registry",
        "import_builder_registry",
        # Logging tool registries
        "smart_log_formatter_registry",
        "logger_engine_registry",
        # File processing registries
        "onextree_processor_registry",
        "onexignore_processor_registry",
        "unified_file_processor_tool_registry",
        # File processing services
        "rsd_cache_manager",
        "rsd_rate_limiter",
        "rsd_metrics_collector",
        "tree_sitter_analyzer",
        "unified_file_processor",
        "onextree_regeneration_service",
        # AI Orchestrator services
        "ai_orchestrator_cli_adapter",
        "ai_orchestrator_node",
        "ai_orchestrator_tool",
        # Infrastructure CLI tool
        "infrastructure_cli",
    ]

    # Build dict with only valid callables (filter out None)
    return {
        name: callable_
        for name in registry_names
        if (callable_ := _get_container_callable(container, name)) is not None
    }


def bind_get_service_method(container: ModelONEXContainer) -> None:
    """
    Bind get_service method to container instance.

    Args:
        container: Container instance to bind method to
    """
    import types

    get_service = create_get_service_method(container)
    # NOTE(OMN-1302): Dynamic method binding required for DynamicContainer restoration.
    container.get_service = types.MethodType(get_service, container)  # type: ignore[method-assign]
