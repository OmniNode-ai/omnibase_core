from collections.abc import Callable
from typing import TypeVar
from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

"""
Container Service Resolver

Service resolution logic for ONEX container instances.
Handles the get_service method functionality that gets lost during
dependency-injector DynamicContainer transformation.
"""

from uuid import NAMESPACE_DNS, uuid5

# DELETED: not needed import create_hybrid_event_bus
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.container.model_service import ModelService

T = TypeVar("T")


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
) -> dict[str, Callable[[], ModelService]]:
    """Build registry mapping for service resolution."""
    # Note: These attributes are dynamically added by dependency-injector
    return {
        # Generation tool registries
        "contract_validator_registry": getattr(
            container, "contract_validator_registry", None
        ),  # type: ignore[dict-item]
        "model_regenerator_registry": getattr(
            container, "model_regenerator_registry", None
        ),  # type: ignore[dict-item]
        "contract_driven_generator_registry": getattr(
            container, "contract_driven_generator_registry", None
        ),  # type: ignore[dict-item]
        "workflow_generator_registry": getattr(
            container, "workflow_generator_registry", None
        ),  # type: ignore[dict-item]
        "ast_generator_registry": getattr(container, "ast_generator_registry", None),  # type: ignore[dict-item]
        "file_writer_registry": getattr(container, "file_writer_registry", None),  # type: ignore[dict-item]
        "introspection_generator_registry": getattr(
            container, "introspection_generator_registry", None
        ),  # type: ignore[dict-item]
        "protocol_generator_registry": getattr(
            container, "protocol_generator_registry", None
        ),  # type: ignore[dict-item]
        "node_stub_generator_registry": getattr(
            container, "node_stub_generator_registry", None
        ),  # type: ignore[dict-item]
        "ast_renderer_registry": getattr(container, "ast_renderer_registry", None),  # type: ignore[dict-item]
        "reference_resolver_registry": getattr(
            container, "reference_resolver_registry", None
        ),  # type: ignore[dict-item]
        "type_import_registry_registry": getattr(
            container, "type_import_registry_registry", None
        ),  # type: ignore[dict-item]
        "python_class_builder_registry": getattr(
            container, "python_class_builder_registry", None
        ),  # type: ignore[dict-item]
        "subcontract_loader_registry": getattr(
            container, "subcontract_loader_registry", None
        ),  # type: ignore[dict-item]
        "import_builder_registry": getattr(container, "import_builder_registry", None),  # type: ignore[dict-item]
        # Logging tool registries
        "smart_log_formatter_registry": getattr(
            container, "smart_log_formatter_registry", None
        ),  # type: ignore[dict-item]
        "logger_engine_registry": getattr(container, "logger_engine_registry", None),  # type: ignore[dict-item]
        # File processing registries
        "onextree_processor_registry": getattr(
            container, "onextree_processor_registry", None
        ),  # type: ignore[dict-item]
        "onexignore_processor_registry": getattr(
            container, "onexignore_processor_registry", None
        ),  # type: ignore[dict-item]
        "unified_file_processor_tool_registry": getattr(
            container, "unified_file_processor_tool_registry", None
        ),  # type: ignore[dict-item]
        # File processing services
        "rsd_cache_manager": getattr(container, "rsd_cache_manager", None),  # type: ignore[dict-item]
        "rsd_rate_limiter": getattr(container, "rsd_rate_limiter", None),  # type: ignore[dict-item]
        "rsd_metrics_collector": getattr(container, "rsd_metrics_collector", None),  # type: ignore[dict-item]
        "tree_sitter_analyzer": getattr(container, "tree_sitter_analyzer", None),  # type: ignore[dict-item]
        "unified_file_processor": getattr(container, "unified_file_processor", None),  # type: ignore[dict-item]
        "onextree_regeneration_service": getattr(
            container, "onextree_regeneration_service", None
        ),  # type: ignore[dict-item]
        # AI Orchestrator services
        "ai_orchestrator_cli_adapter": getattr(
            container, "ai_orchestrator_cli_adapter", None
        ),  # type: ignore[dict-item]
        "ai_orchestrator_node": getattr(container, "ai_orchestrator_node", None),  # type: ignore[dict-item]
        "ai_orchestrator_tool": getattr(container, "ai_orchestrator_tool", None),  # type: ignore[dict-item]
        # Infrastructure CLI tool
        "infrastructure_cli": getattr(container, "infrastructure_cli", None),  # type: ignore[dict-item]
    }


def bind_get_service_method(container: ModelONEXContainer) -> None:
    """
    Bind get_service method to container instance.

    Args:
        container: Container instance to bind method to
    """
    import types

    get_service = create_get_service_method(container)
    container.get_service = types.MethodType(get_service, container)  # type: ignore[method-assign]
