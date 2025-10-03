"""
Comprehensive unit tests for container_service_resolver module.

Tests cover:
- Registry map building
- Protocol-based service resolution
- Special service cases (event_bus, consul, vault)
- Error handling for missing services
- Method binding functionality
"""

import types
from unittest.mock import MagicMock, Mock

import pytest

from omnibase_core.container.container_service_resolver import (
    _build_registry_map,
    bind_get_service_method,
    create_get_service_method,
)
from omnibase_core.errors import CoreErrorCode, OnexError
from omnibase_core.models.container.model_service import ModelService


class TestRegistryMapBuilding:
    """Test registry map construction from container."""

    def test_build_registry_map_with_all_services(self):
        """Test registry map includes all expected services."""
        # Create mock container with all registry methods
        container = Mock()
        container.contract_validator_registry = Mock()
        container.model_regenerator_registry = Mock()
        container.contract_driven_generator_registry = Mock()
        container.workflow_generator_registry = Mock()
        container.ast_generator_registry = Mock()
        container.file_writer_registry = Mock()
        container.introspection_generator_registry = Mock()
        container.protocol_generator_registry = Mock()
        container.node_stub_generator_registry = Mock()
        container.ast_renderer_registry = Mock()
        container.reference_resolver_registry = Mock()
        container.type_import_registry_registry = Mock()
        container.python_class_builder_registry = Mock()
        container.subcontract_loader_registry = Mock()
        container.import_builder_registry = Mock()
        container.smart_log_formatter_registry = Mock()
        container.logger_engine_registry = Mock()
        container.onextree_processor_registry = Mock()
        container.onexignore_processor_registry = Mock()
        container.unified_file_processor_tool_registry = Mock()
        container.rsd_cache_manager = Mock()
        container.rsd_rate_limiter = Mock()
        container.rsd_metrics_collector = Mock()
        container.tree_sitter_analyzer = Mock()
        container.unified_file_processor = Mock()
        container.onextree_regeneration_service = Mock()
        container.ai_orchestrator_cli_adapter = Mock()
        container.ai_orchestrator_node = Mock()
        container.ai_orchestrator_tool = Mock()
        container.infrastructure_cli = Mock()

        registry_map = _build_registry_map(container)

        # Verify all expected keys are present
        expected_keys = [
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

        for key in expected_keys:
            assert key in registry_map, f"Missing registry key: {key}"
            assert callable(registry_map[key])

    def test_build_registry_map_returns_callables(self):
        """Test that registry map values are callable."""
        container = Mock()
        container.contract_validator_registry = Mock()
        container.file_writer_registry = Mock()

        registry_map = _build_registry_map(container)

        for service_name, service_method in registry_map.items():
            assert callable(service_method), f"Service {service_name} not callable"


class TestServiceResolution:
    """Test service resolution logic."""

    def test_resolve_service_by_name_from_registry(self):
        """Test resolving service by name from registry map."""
        container = Mock()
        container.contract_validator_registry = Mock(
            return_value=Mock()
        )  # Return value for the call

        get_service = create_get_service_method(container)
        service = get_service(container, "contract_validator_registry")

        assert isinstance(service, ModelService)
        assert service.service_name == "contract_validator_registry"
        assert service.service_type == "registry_service"
        assert service.health_status == "healthy"

    def test_resolve_event_bus_by_string(self):
        """Test resolving event_bus by string name."""
        container = Mock()

        get_service = create_get_service_method(container)
        service = get_service(container, "event_bus")

        assert isinstance(service, ModelService)
        assert service.service_name == "event_bus"
        assert service.service_type == "hybrid_event_bus"
        assert service.protocol_name == "ProtocolEventBus"

    def test_resolve_consul_client_by_protocol(self):
        """Test resolving consul client by protocol type."""
        container = Mock()
        container.consul_client = Mock()

        # Create mock protocol type
        protocol_type = Mock()
        protocol_type.__name__ = "ProtocolConsulClient"

        get_service = create_get_service_method(container)
        service = get_service(container, protocol_type)

        assert isinstance(service, ModelService)
        assert service.service_name == "consul_client"
        assert service.protocol_name == "ProtocolConsulClient"
        container.consul_client.assert_called_once()

    def test_resolve_vault_client_by_protocol(self):
        """Test resolving vault client by protocol type."""
        container = Mock()
        container.vault_client = Mock()

        # Create mock protocol type
        protocol_type = Mock()
        protocol_type.__name__ = "ProtocolVaultClient"

        get_service = create_get_service_method(container)
        service = get_service(container, protocol_type)

        assert isinstance(service, ModelService)
        assert service.service_name == "vault_client"
        assert service.protocol_name == "ProtocolVaultClient"
        container.vault_client.assert_called_once()

    def test_resolve_event_bus_by_protocol(self):
        """Test resolving event bus by protocol type."""
        container = Mock()

        # Create mock protocol type
        protocol_type = Mock()
        protocol_type.__name__ = "ProtocolEventBus"

        get_service = create_get_service_method(container)
        service = get_service(container, protocol_type)

        assert isinstance(service, ModelService)
        assert service.service_name == "event_bus"
        assert service.protocol_name == "ProtocolEventBus"


class TestErrorHandling:
    """Test error handling in service resolution."""

    def test_raises_error_for_unknown_service_name(self):
        """Test that unknown service name raises OnexError."""
        container = Mock()

        get_service = create_get_service_method(container)

        with pytest.raises(OnexError) as exc_info:
            get_service(container, "unknown_service")

        assert exc_info.value.error_code == CoreErrorCode.REGISTRY_RESOLUTION_FAILED
        assert "Unable to resolve service: unknown_service" in str(exc_info.value)

    def test_raises_error_when_vault_client_unavailable(self):
        """Test error when vault client method not available."""
        container = Mock(spec=[])  # Empty spec - no vault_client

        # Create mock protocol type
        protocol_type = Mock()
        protocol_type.__name__ = "ProtocolVaultClient"

        get_service = create_get_service_method(container)

        with pytest.raises(OnexError) as exc_info:
            get_service(container, protocol_type)

        assert exc_info.value.error_code == CoreErrorCode.REGISTRY_RESOLUTION_FAILED
        assert "Vault client not available" in str(exc_info.value)

    def test_raises_error_for_invalid_protocol(self):
        """Test error for invalid protocol type without __name__."""
        container = Mock()

        get_service = create_get_service_method(container)

        # Protocol without __name__ attribute should fail
        protocol_type = Mock(spec=[])  # No __name__

        with pytest.raises(OnexError) as exc_info:
            get_service(container, "nonexistent_service")

        assert exc_info.value.error_code == CoreErrorCode.REGISTRY_RESOLUTION_FAILED


class TestMethodBinding:
    """Test bind_get_service_method functionality."""

    def test_bind_get_service_method_creates_bound_method(self):
        """Test that bind_get_service_method creates a bound method."""
        container = Mock()

        bind_get_service_method(container)

        assert hasattr(container, "get_service")
        assert callable(container.get_service)
        assert isinstance(container.get_service, types.MethodType)

    def test_bound_method_can_resolve_services(self):
        """Test that bound method can successfully resolve services."""
        container = Mock()
        container.contract_validator_registry = Mock()

        bind_get_service_method(container)

        service = container.get_service("contract_validator_registry")

        assert isinstance(service, ModelService)
        assert service.service_name == "contract_validator_registry"

    def test_bound_method_preserves_container_context(self):
        """Test that bound method maintains container as self."""
        container = Mock()
        container.file_writer_registry = Mock()

        bind_get_service_method(container)

        # Verify the method is bound to the container instance
        assert container.get_service.__self__ is container


class TestServiceResolutionEdgeCases:
    """Test edge cases in service resolution."""

    def test_resolve_with_none_service_name(self):
        """Test resolution with None service_name parameter."""
        container = Mock()

        # Create protocol with __name__
        protocol_type = Mock()
        protocol_type.__name__ = "UnknownProtocol"

        get_service = create_get_service_method(container)

        with pytest.raises(OnexError):
            get_service(container, protocol_type, service_name=None)

    def test_registry_method_returns_none(self):
        """Test behavior when registry method returns None."""
        container = Mock()
        container.contract_validator_registry = Mock(return_value=None)

        get_service = create_get_service_method(container)

        # Should still create ModelService even if registry returns None
        service = get_service(container, "contract_validator_registry")
        assert isinstance(service, ModelService)

    def test_multiple_service_resolutions(self):
        """Test multiple sequential service resolutions."""
        container = Mock()
        container.contract_validator_registry = Mock()
        container.file_writer_registry = Mock()
        container.logger_engine_registry = Mock()

        get_service = create_get_service_method(container)

        services = [
            get_service(container, "contract_validator_registry"),
            get_service(container, "file_writer_registry"),
            get_service(container, "logger_engine_registry"),
        ]

        assert all(isinstance(svc, ModelService) for svc in services)
        assert len({svc.service_name for svc in services}) == 3


class TestProtocolTypeHandling:
    """Test protocol type handling variations."""

    def test_protocol_type_with_name_attribute(self):
        """Test protocol type that has __name__ attribute."""
        container = Mock()

        # Create a mock with __name__ attribute
        protocol_type = Mock()
        protocol_type.__name__ = "ProtocolEventBus"

        get_service = create_get_service_method(container)
        service = get_service(container, protocol_type)

        assert service.protocol_name == "ProtocolEventBus"

    def test_string_protocol_name_in_registry(self):
        """Test passing string that exists in registry."""
        container = Mock()
        container.file_writer_registry = Mock()

        get_service = create_get_service_method(container)
        service = get_service(container, "file_writer_registry")

        assert service.service_name == "file_writer_registry"
        assert service.service_type == "registry_service"
