"""
Container Service Resolver

Service resolution logic for ONEX container instances.
Handles the get_service method functionality that gets lost during
dependency-injector DynamicContainer transformation.
"""

from collections.abc import Callable
from typing import TypeVar
from uuid import NAMESPACE_DNS, UUID, uuid5

from omnibase_core.errors import CoreErrorCode, OnexError

# DELETED: not needed import create_hybrid_event_bus
from omnibase_core.models.container.model_service import ModelService
from omnibase_core.models.core import ModelContainer

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
    container: ModelContainer,
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
        self,
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
                self.consul_client()
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
                raise OnexError(
                    msg,
                    CoreErrorCode.REGISTRY_RESOLUTION_FAILED,
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
        raise OnexError(
            msg,
            error_code=CoreErrorCode.REGISTRY_RESOLUTION_FAILED,
        )

    return get_service


def _build_registry_map(
    container: ModelContainer,
) -> dict[str, Callable[[], ModelService]]:
    """Build registry mapping for service resolution."""
    return {
        # Generation tool registries
        "contract_validator_registry": container.contract_validator_registry,
        "model_regenerator_registry": container.model_regenerator_registry,
        "contract_driven_generator_registry": container.contract_driven_generator_registry,
        "workflow_generator_registry": container.workflow_generator_registry,
        "ast_generator_registry": container.ast_generator_registry,
        "file_writer_registry": container.file_writer_registry,
        "introspection_generator_registry": container.introspection_generator_registry,
        "protocol_generator_registry": container.protocol_generator_registry,
        "node_stub_generator_registry": container.node_stub_generator_registry,
        "ast_renderer_registry": container.ast_renderer_registry,
        "reference_resolver_registry": container.reference_resolver_registry,
        "type_import_registry_registry": container.type_import_registry_registry,
        "python_class_builder_registry": container.python_class_builder_registry,
        "subcontract_loader_registry": container.subcontract_loader_registry,
        "import_builder_registry": container.import_builder_registry,
        # Logging tool registries
        "smart_log_formatter_registry": container.smart_log_formatter_registry,
        "logger_engine_registry": container.logger_engine_registry,
        # File processing registries
        "onextree_processor_registry": container.onextree_processor_registry,
        "onexignore_processor_registry": container.onexignore_processor_registry,
        "unified_file_processor_tool_registry": container.unified_file_processor_tool_registry,
        # File processing services
        "rsd_cache_manager": container.rsd_cache_manager,
        "rsd_rate_limiter": container.rsd_rate_limiter,
        "rsd_metrics_collector": container.rsd_metrics_collector,
        "tree_sitter_analyzer": container.tree_sitter_analyzer,
        "unified_file_processor": container.unified_file_processor,
        "onextree_regeneration_service": container.onextree_regeneration_service,
        # AI Orchestrator services
        "ai_orchestrator_cli_adapter": container.ai_orchestrator_cli_adapter,
        "ai_orchestrator_node": container.ai_orchestrator_node,
        "ai_orchestrator_tool": container.ai_orchestrator_tool,
        # Infrastructure CLI tool
        "infrastructure_cli": container.infrastructure_cli,
    }


def bind_get_service_method(container: ModelContainer) -> None:
    """
    Bind get_service method to container instance.

    Args:
        container: Container instance to bind method to
    """
    import types

    get_service = create_get_service_method(container)
    container.get_service = types.MethodType(get_service, container)
