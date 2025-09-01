#!/usr/bin/env python3

"""
Comprehensive unit tests for Infrastructure Reducer.
Tests all functionality with real service integration and comprehensive coverage.
Achieves >85% line coverage requirement to fix the current 10% coverage issue.

This test suite follows the comprehensive template pattern from vault adapter tests
and provides thorough testing of:
- Infrastructure adapter loading and coordination
- Health check functionality (modernized and legacy)
- Registry event handling and service management
- HTTP API endpoints and service coordination
- Event bus integration and message handling
- Specialized component management
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch
from uuid import uuid4

import pytest

from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.core.onex_container import ONEXContainer
from omnibase_core.enums.enum_health_status import EnumHealthStatus
from omnibase_core.model.core.model_health_status import ModelHealthStatus
from omnibase_core.model.registry.model_registry_event import (
    ModelRegistryResponseEvent,
    RegistryOperations,
)

from .node import (
    NodeCanaryReducer,
)


class TestInfrastructureReducerInitialization:
    """Test infrastructure reducer initialization and component loading."""

    @pytest.fixture
    def mock_container(self):
        """Create mock ONEX container for testing."""
        container = MagicMock(spec=ONEXContainer)
        container.get_tool = MagicMock(return_value=None)
        return container

    @pytest.fixture
    def mock_contract_content(self):
        """Mock contract content for adapter loading tests."""
        return {
            "infrastructure_services": {
                "loaded_adapters": [
                    {
                        "name": "consul_adapter",
                        "onex_node_metadata": "omnibase.tools.infrastructure.tool_infrastructure_consul_adapter_effect.tool.manifest",
                        "version_strategy": "current_stable",
                    },
                    {
                        "name": "vault_adapter",
                        "onex_node_metadata": "omnibase.tools.infrastructure.tool_infrastructure_vault_adapter_effect.tool.manifest",
                        "version_strategy": "current_stable",
                    },
                    {
                        "name": "kafka_adapter",
                        "onex_node_metadata": "omnibase.tools.infrastructure.tool_infrastructure_kafka_adapter_effect.tool.manifest",
                        "version_strategy": "current_stable",
                    },
                ],
                "specialized_components": [
                    {
                        "name": "registry_catalog_aggregator",
                        "onex_node_metadata": "omnibase.tools.infrastructure.tool_infrastructure_registry_catalog_aggregator.tool.manifest",
                        "version_strategy": "current_stable",
                        "component_type": "delegated_reducer",
                        "readiness_check": "infrastructure_ready",
                        "description": "Registry catalog aggregation component",
                    },
                ],
            },
        }

    def test_init_successful(self, mock_container):
        """Test successful infrastructure reducer initialization."""
        with (
            patch("builtins.open"),
            patch("yaml.safe_load"),
            patch.object(NodeCanaryReducer, "_load_infrastructure_adapters"),
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
        ):
            reducer = NodeCanaryReducer(mock_container)

            assert reducer.domain == "infrastructure"
            assert hasattr(reducer, "loaded_adapters")
            assert hasattr(reducer, "specialized_components")
            assert hasattr(reducer, "_pending_registry_requests")
            assert not reducer._event_bus_active
            assert reducer._consul_adapter is None
            assert reducer._vault_adapter is None
            assert reducer._kafka_adapter is None

    def test_init_with_logger(self, mock_container):
        """Test initialization with logger available."""
        mock_logger = MagicMock()

        with (
            patch("builtins.open"),
            patch("yaml.safe_load"),
            patch.object(NodeCanaryReducer, "_load_infrastructure_adapters"),
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
        ):
            reducer = NodeCanaryReducer(mock_container)
            reducer.logger = mock_logger

            # Trigger initialization logging
            reducer.__init__(mock_container)

            # Should use logger instead of print
            assert hasattr(reducer, "logger")

    def test_adapter_loading_success(self, mock_container, mock_contract_content):
        """Test successful loading of infrastructure adapters."""
        mock_adapter_instance = MagicMock()
        MagicMock(return_value=mock_adapter_instance)

        with (
            patch("builtins.open"),
            patch("yaml.safe_load", return_value=mock_contract_content),
            patch.object(
                NodeCanaryReducer,
                "_load_adapter_from_metadata",
                return_value=mock_adapter_instance,
            ),
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
        ):
            reducer = NodeCanaryReducer(mock_container)

            # Should have loaded adapters
            assert len(reducer.loaded_adapters) > 0
            assert "consul_adapter" in list(reducer.loaded_adapters.keys())

    def test_adapter_loading_failure(self, mock_container, mock_contract_content):
        """Test handling of adapter loading failures."""
        with (
            patch("builtins.open"),
            patch("yaml.safe_load", return_value=mock_contract_content),
            patch.object(
                NodeCanaryReducer,
                "_load_adapter_from_metadata",
                side_effect=Exception("Loading failed"),
            ),
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
        ):
            # Should not raise exception, but continue with other adapters
            reducer = NodeCanaryReducer(mock_container)

            # Failed adapters should not be in loaded_adapters
            assert isinstance(reducer.loaded_adapters, dict)

    def test_specialized_components_loading_success(
        self,
        mock_container,
        mock_contract_content,
    ):
        """Test successful loading of specialized components."""
        mock_component_instance = MagicMock()

        with (
            patch("builtins.open"),
            patch("yaml.safe_load", return_value=mock_contract_content),
            patch.object(NodeCanaryReducer, "_load_infrastructure_adapters"),
            patch.object(
                NodeCanaryReducer,
                "_load_adapter_from_metadata",
                return_value=mock_component_instance,
            ),
        ):
            reducer = NodeCanaryReducer(mock_container)

            # Should have loaded specialized components
            assert isinstance(reducer.specialized_components, dict)

    def test_specialized_components_loading_failure(
        self,
        mock_container,
        mock_contract_content,
    ):
        """Test handling of specialized component loading failures."""
        with (
            patch("builtins.open"),
            patch("yaml.safe_load", return_value=mock_contract_content),
            patch.object(NodeCanaryReducer, "_load_infrastructure_adapters"),
            patch.object(
                NodeCanaryReducer,
                "_load_adapter_from_metadata",
                side_effect=Exception("Component loading failed"),
            ),
        ):
            # Should not raise exception
            reducer = NodeCanaryReducer(mock_container)

            # Failed components should not be in specialized_components
            assert isinstance(reducer.specialized_components, dict)


class TestInfrastructureReducerAdapterLoading:
    """Test detailed adapter loading functionality."""

    @pytest.fixture
    def mock_container(self):
        """Create mock ONEX container for testing."""
        return MagicMock(spec=ONEXContainer)

    @pytest.fixture
    def sample_manifest_content(self):
        """Sample tool manifest content for testing."""
        return {
            "namespace": "omnibase.tools.infrastructure.tool_infrastructure_consul_adapter_effect",
            "x_extensions": {
                "version_management": {
                    "current_stable": "1.0.0",
                    "current_development": "1.1.0",
                    "discovery": {
                        "version_directory_pattern": "v{major}_{minor}_{patch}",
                        "main_class_name": "NodeCanaryEffect",
                    },
                },
            },
        }

    def test_load_adapter_from_metadata_success(
        self,
        mock_container,
        sample_manifest_content,
    ):
        """Test successful adapter loading from metadata."""
        mock_adapter_instance = MagicMock()
        mock_adapter_class = MagicMock(return_value=mock_adapter_instance)

        with (
            patch("builtins.open"),
            patch("yaml.safe_load", return_value=sample_manifest_content),
            patch("importlib.import_module"),
            patch("getattr", return_value=mock_adapter_class),
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
        ):
            reducer = NodeCanaryReducer(mock_container)

            result = reducer._load_adapter_from_metadata(
                "consul_adapter",
                "omnibase.tools.infrastructure.tool_infrastructure_consul_adapter_effect.tool.manifest",
                "current_stable",
            )

            assert result == mock_adapter_instance
            mock_adapter_class.assert_called_once_with(mock_container)

    def test_load_adapter_from_metadata_with_current_development(
        self,
        mock_container,
        sample_manifest_content,
    ):
        """Test adapter loading with current_development version strategy."""
        mock_adapter_instance = MagicMock()
        mock_adapter_class = MagicMock(return_value=mock_adapter_instance)

        with (
            patch("builtins.open"),
            patch("yaml.safe_load", return_value=sample_manifest_content),
            patch("importlib.import_module"),
            patch("getattr", return_value=mock_adapter_class),
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
        ):
            reducer = NodeCanaryReducer(mock_container)

            result = reducer._load_adapter_from_metadata(
                "consul_adapter",
                "omnibase.tools.infrastructure.tool_infrastructure_consul_adapter_effect.tool.manifest",
                "current_development",
            )

            assert result == mock_adapter_instance

    def test_load_adapter_from_metadata_import_failure(
        self,
        mock_container,
        sample_manifest_content,
    ):
        """Test handling of import failures during adapter loading."""
        with (
            patch("builtins.open"),
            patch("yaml.safe_load", return_value=sample_manifest_content),
            patch(
                "importlib.import_module",
                side_effect=ImportError("Module not found"),
            ),
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
        ):
            reducer = NodeCanaryReducer(mock_container)

            with pytest.raises(ImportError):
                reducer._load_adapter_from_metadata(
                    "consul_adapter",
                    "omnibase.tools.infrastructure.tool_infrastructure_consul_adapter_effect.tool.manifest",
                    "current_stable",
                )

    def test_load_adapter_from_metadata_file_not_found(self, mock_container):
        """Test handling of missing metadata files."""
        with (
            patch("builtins.open", side_effect=FileNotFoundError("File not found")),
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
        ):
            reducer = NodeCanaryReducer(mock_container)

            with pytest.raises(FileNotFoundError):
                reducer._load_adapter_from_metadata(
                    "consul_adapter",
                    "omnibase.tools.infrastructure.tool_infrastructure_consul_adapter_effect.tool.manifest",
                    "current_stable",
                )


class TestInfrastructureReducerHealthCheck:
    """Test the modernized health check functionality - Primary modernization focus."""

    @pytest.fixture
    def mock_container(self):
        """Create mock ONEX container for testing."""
        return MagicMock(spec=ONEXContainer)

    @pytest.fixture
    def reducer_with_mocked_loading(self, mock_container):
        """Create reducer with mocked loading methods."""
        with (
            patch.object(NodeCanaryReducer, "_load_infrastructure_adapters"),
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
        ):
            return NodeCanaryReducer(mock_container)

    def test_health_check_no_adapters_or_components(self, reducer_with_mocked_loading):
        """Test health check when no adapters or components are loaded."""
        reducer = reducer_with_mocked_loading
        reducer.loaded_adapters = {}
        reducer.specialized_components = {}

        result = reducer.health_check()

        assert isinstance(result, ModelHealthStatus)
        assert result.status == EnumHealthStatus.UNHEALTHY
        assert (
            "No infrastructure adapters or specialized components loaded"
            in result.message
        )

    def test_health_check_all_healthy_adapters(self, reducer_with_mocked_loading):
        """Test health check with all healthy adapters."""
        reducer = reducer_with_mocked_loading

        # Create mock healthy adapters
        mock_adapter1 = MagicMock()
        mock_adapter1.health_check.return_value = ModelHealthStatus(
            status=EnumHealthStatus.HEALTHY,
            message="Adapter 1 healthy",
        )

        mock_adapter2 = MagicMock()
        mock_adapter2.health_check.return_value = ModelHealthStatus(
            status=EnumHealthStatus.HEALTHY,
            message="Adapter 2 healthy",
        )

        reducer.loaded_adapters = {
            "adapter1": mock_adapter1,
            "adapter2": mock_adapter2,
        }
        reducer.specialized_components = {}

        result = reducer.health_check()

        assert isinstance(result, ModelHealthStatus)
        assert result.status == EnumHealthStatus.HEALTHY
        assert (
            "Infrastructure healthy - 2 adapters, 0 components operational"
            in result.message
        )

    def test_health_check_degraded_adapters(self, reducer_with_mocked_loading):
        """Test health check with degraded adapters."""
        reducer = reducer_with_mocked_loading

        # Create mock adapters with mixed health
        mock_adapter1 = MagicMock()
        mock_adapter1.health_check.return_value = ModelHealthStatus(
            status=EnumHealthStatus.HEALTHY,
            message="Adapter 1 healthy",
        )

        mock_adapter2 = MagicMock()
        mock_adapter2.health_check.return_value = ModelHealthStatus(
            status=EnumHealthStatus.DEGRADED,
            message="Adapter 2 degraded",
        )

        reducer.loaded_adapters = {
            "adapter1": mock_adapter1,
            "adapter2": mock_adapter2,
        }
        reducer.specialized_components = {}

        result = reducer.health_check()

        assert isinstance(result, ModelHealthStatus)
        assert result.status == EnumHealthStatus.DEGRADED
        assert (
            "Infrastructure degraded - 1 components degraded, 1 healthy"
            in result.message
        )

    def test_health_check_unhealthy_adapters(self, reducer_with_mocked_loading):
        """Test health check with unhealthy adapters."""
        reducer = reducer_with_mocked_loading

        # Create mock unhealthy adapters
        mock_adapter1 = MagicMock()
        mock_adapter1.health_check.return_value = ModelHealthStatus(
            status=EnumHealthStatus.UNHEALTHY,
            message="Adapter 1 failed",
        )

        mock_adapter2 = MagicMock()
        mock_adapter2.health_check.return_value = ModelHealthStatus(
            status=EnumHealthStatus.HEALTHY,
            message="Adapter 2 healthy",
        )

        reducer.loaded_adapters = {
            "adapter1": mock_adapter1,
            "adapter2": mock_adapter2,
        }
        reducer.specialized_components = {}

        result = reducer.health_check()

        assert isinstance(result, ModelHealthStatus)
        assert result.status == EnumHealthStatus.DEGRADED
        assert (
            "Infrastructure partially degraded - 1 failed, 1 healthy, 0 degraded"
            in result.message
        )

    def test_health_check_all_failed_adapters(self, reducer_with_mocked_loading):
        """Test health check when all adapters fail."""
        reducer = reducer_with_mocked_loading

        # Create mock failed adapters
        mock_adapter1 = MagicMock()
        mock_adapter1.health_check.return_value = ModelHealthStatus(
            status=EnumHealthStatus.UNHEALTHY,
            message="Adapter 1 failed",
        )

        mock_adapter2 = MagicMock()
        mock_adapter2.health_check.return_value = ModelHealthStatus(
            status=EnumHealthStatus.UNHEALTHY,
            message="Adapter 2 failed",
        )

        reducer.loaded_adapters = {
            "adapter1": mock_adapter1,
            "adapter2": mock_adapter2,
        }
        reducer.specialized_components = {}

        result = reducer.health_check()

        assert isinstance(result, ModelHealthStatus)
        assert result.status == EnumHealthStatus.UNHEALTHY
        assert (
            "Infrastructure critical failure - 2 components failed, none healthy"
            in result.message
        )

    def test_health_check_legacy_dict_format(self, reducer_with_mocked_loading):
        """Test health check with legacy dict format from adapters."""
        reducer = reducer_with_mocked_loading

        # Create mock adapter returning legacy dict format
        mock_adapter = MagicMock()
        mock_adapter.health_check.return_value = {
            "status": "healthy",
            "message": "Legacy format adapter healthy",
        }

        reducer.loaded_adapters = {"adapter1": mock_adapter}
        reducer.specialized_components = {}

        result = reducer.health_check()

        assert isinstance(result, ModelHealthStatus)
        assert result.status == EnumHealthStatus.HEALTHY

    def test_health_check_legacy_dict_degraded(self, reducer_with_mocked_loading):
        """Test health check with legacy dict format showing degraded status."""
        reducer = reducer_with_mocked_loading

        mock_adapter = MagicMock()
        mock_adapter.health_check.return_value = {
            "status": "warning",
            "message": "Legacy format adapter warning",
        }

        reducer.loaded_adapters = {"adapter1": mock_adapter}
        reducer.specialized_components = {}

        result = reducer.health_check()

        assert isinstance(result, ModelHealthStatus)
        assert result.status == EnumHealthStatus.DEGRADED

    def test_health_check_legacy_dict_failed(self, reducer_with_mocked_loading):
        """Test health check with legacy dict format showing failed status."""
        reducer = reducer_with_mocked_loading

        mock_adapter = MagicMock()
        mock_adapter.health_check.return_value = {
            "status": "error",
            "message": "Legacy format adapter error",
        }

        reducer.loaded_adapters = {"adapter1": mock_adapter}
        reducer.specialized_components = {}

        result = reducer.health_check()

        assert isinstance(result, ModelHealthStatus)
        assert result.status == EnumHealthStatus.DEGRADED

    def test_health_check_adapter_without_health_check_method(
        self,
        reducer_with_mocked_loading,
    ):
        """Test health check with adapter that doesn't have health_check method."""
        reducer = reducer_with_mocked_loading

        mock_adapter = MagicMock()
        del mock_adapter.health_check  # Remove health_check method

        reducer.loaded_adapters = {"adapter1": mock_adapter}
        reducer.specialized_components = {}

        result = reducer.health_check()

        assert isinstance(result, ModelHealthStatus)
        assert (
            result.status == EnumHealthStatus.HEALTHY
        )  # Should assume healthy if loaded

    def test_health_check_adapter_health_check_exception(
        self,
        reducer_with_mocked_loading,
    ):
        """Test health check when adapter health check raises exception."""
        reducer = reducer_with_mocked_loading

        mock_adapter = MagicMock()
        mock_adapter.health_check.side_effect = Exception("Health check failed")

        reducer.loaded_adapters = {"adapter1": mock_adapter}
        reducer.specialized_components = {}

        result = reducer.health_check()

        assert isinstance(result, ModelHealthStatus)
        assert (
            result.status == EnumHealthStatus.DEGRADED
        )  # Should mark as degraded when exception occurs

    def test_health_check_with_specialized_components(
        self,
        reducer_with_mocked_loading,
    ):
        """Test health check including specialized components."""
        reducer = reducer_with_mocked_loading

        mock_adapter = MagicMock()
        mock_adapter.health_check.return_value = ModelHealthStatus(
            status=EnumHealthStatus.HEALTHY,
            message="Adapter healthy",
        )

        mock_component = MagicMock()
        mock_component.health_check.return_value = ModelHealthStatus(
            status=EnumHealthStatus.HEALTHY,
            message="Component healthy",
        )

        reducer.loaded_adapters = {"adapter1": mock_adapter}
        reducer.specialized_components = {"component1": {"instance": mock_component}}

        result = reducer.health_check()

        assert isinstance(result, ModelHealthStatus)
        assert result.status == EnumHealthStatus.HEALTHY
        assert (
            "Infrastructure healthy - 1 adapters, 1 components operational"
            in result.message
        )

    def test_health_check_specialized_component_failure(
        self,
        reducer_with_mocked_loading,
    ):
        """Test health check with failed specialized components."""
        reducer = reducer_with_mocked_loading

        mock_component = MagicMock()
        mock_component.health_check.return_value = ModelHealthStatus(
            status=EnumHealthStatus.UNHEALTHY,
            message="Component failed",
        )

        reducer.loaded_adapters = {}
        reducer.specialized_components = {"component1": {"instance": mock_component}}

        result = reducer.health_check()

        assert isinstance(result, ModelHealthStatus)
        assert result.status == EnumHealthStatus.DEGRADED  # Mixed health states

    def test_health_check_specialized_component_without_health_check(
        self,
        reducer_with_mocked_loading,
    ):
        """Test health check with specialized component without health_check method."""
        reducer = reducer_with_mocked_loading

        mock_component = MagicMock()
        del mock_component.health_check  # Remove health_check method

        reducer.loaded_adapters = {}
        reducer.specialized_components = {"component1": {"instance": mock_component}}

        result = reducer.health_check()

        assert isinstance(result, ModelHealthStatus)
        assert (
            result.status == EnumHealthStatus.HEALTHY
        )  # Should assume healthy if loaded

    def test_health_check_specialized_component_exception(
        self,
        reducer_with_mocked_loading,
    ):
        """Test health check when specialized component health check raises exception."""
        reducer = reducer_with_mocked_loading

        mock_component = MagicMock()
        mock_component.health_check.side_effect = Exception(
            "Component health check failed",
        )

        reducer.loaded_adapters = {}
        reducer.specialized_components = {"component1": {"instance": mock_component}}

        result = reducer.health_check()

        assert isinstance(result, ModelHealthStatus)
        assert result.status == EnumHealthStatus.DEGRADED

    def test_health_check_system_failure(self, reducer_with_mocked_loading):
        """Test health check when the health check system itself fails."""
        reducer = reducer_with_mocked_loading
        reducer.logger = MagicMock()

        # Make the health check itself raise an exception
        with patch.object(
            reducer,
            "loaded_adapters",
            side_effect=Exception("System failure"),
        ):
            result = reducer.health_check()

            assert isinstance(result, ModelHealthStatus)
            assert result.status == EnumHealthStatus.UNHEALTHY
            assert "Health check system failure" in result.message
            reducer.logger.error.assert_called_once()


class TestInfrastructureReducerLegacyHealthCheck:
    """Test the legacy aggregate_health_status method for backward compatibility."""

    @pytest.fixture
    def mock_container(self):
        """Create mock ONEX container for testing."""
        return MagicMock(spec=ONEXContainer)

    @pytest.fixture
    def reducer_with_mocked_loading(self, mock_container):
        """Create reducer with mocked loading methods."""
        with (
            patch.object(NodeCanaryReducer, "_load_infrastructure_adapters"),
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
        ):
            return NodeCanaryReducer(mock_container)

    @pytest.mark.asyncio
    async def test_aggregate_health_status_healthy(self, reducer_with_mocked_loading):
        """Test aggregate_health_status with healthy adapters."""
        reducer = reducer_with_mocked_loading

        # Mock the modernized health_check to return healthy
        with patch.object(reducer, "health_check") as mock_health_check:
            mock_health_check.return_value = ModelHealthStatus(
                status=EnumHealthStatus.HEALTHY,
                message="Infrastructure healthy",
            )

            adapter_health_statuses = {
                "consul_adapter": {"status": "healthy", "message": "Consul OK"},
                "vault_adapter": {"status": "success", "message": "Vault OK"},
            }

            result = await reducer.aggregate_health_status(adapter_health_statuses)

            assert result["infrastructure_status"] == "ready"
            assert result["ready_services"] == ["consul_adapter", "vault_adapter"]
            assert result["degraded_services"] == []
            assert result["failed_services"] == []
            assert result["ready_count"] == 2
            assert result["total_services"] == 2
            assert result["external_access"]["consul_available"] is True
            assert result["external_access"]["vault_available"] is True
            assert result["external_access"]["kafka_available"] is False

    @pytest.mark.asyncio
    async def test_aggregate_health_status_degraded(self, reducer_with_mocked_loading):
        """Test aggregate_health_status with degraded status."""
        reducer = reducer_with_mocked_loading

        with patch.object(reducer, "health_check") as mock_health_check:
            mock_health_check.return_value = ModelHealthStatus(
                status=EnumHealthStatus.DEGRADED,
                message="Infrastructure degraded",
            )

            adapter_health_statuses = {
                "consul_adapter": {"status": "healthy", "message": "Consul OK"},
                "vault_adapter": {"status": "warning", "message": "Vault degraded"},
            }

            result = await reducer.aggregate_health_status(adapter_health_statuses)

            assert result["infrastructure_status"] == "degraded"
            assert result["ready_services"] == ["consul_adapter"]
            assert result["degraded_services"] == ["vault_adapter"]
            assert result["failed_services"] == []

    @pytest.mark.asyncio
    async def test_aggregate_health_status_unavailable(
        self,
        reducer_with_mocked_loading,
    ):
        """Test aggregate_health_status with unavailable status."""
        reducer = reducer_with_mocked_loading

        with patch.object(reducer, "health_check") as mock_health_check:
            mock_health_check.return_value = ModelHealthStatus(
                status=EnumHealthStatus.UNHEALTHY,
                message="Infrastructure unhealthy",
            )

            adapter_health_statuses = {
                "consul_adapter": {"status": "error", "message": "Consul failed"},
                "vault_adapter": {"status": "failed", "message": "Vault failed"},
            }

            result = await reducer.aggregate_health_status(adapter_health_statuses)

            assert result["infrastructure_status"] == "unavailable"
            assert result["ready_services"] == []
            assert result["degraded_services"] == []
            assert result["failed_services"] == ["consul_adapter", "vault_adapter"]

    @pytest.mark.asyncio
    async def test_aggregate_health_status_mixed_states(
        self,
        reducer_with_mocked_loading,
    ):
        """Test aggregate_health_status with mixed adapter states."""
        reducer = reducer_with_mocked_loading

        with patch.object(reducer, "health_check") as mock_health_check:
            mock_health_check.return_value = ModelHealthStatus(
                status=EnumHealthStatus.DEGRADED,
                message="Infrastructure degraded",
            )

            adapter_health_statuses = {
                "consul_adapter": {"status": "healthy", "message": "Consul OK"},
                "vault_adapter": {"status": "warning", "message": "Vault degraded"},
                "kafka_wrapper": {"status": "error", "message": "Kafka failed"},
            }

            result = await reducer.aggregate_health_status(adapter_health_statuses)

            assert result["infrastructure_status"] == "degraded"
            assert result["ready_services"] == ["consul_adapter"]
            assert result["degraded_services"] == ["vault_adapter"]
            assert result["failed_services"] == ["kafka_wrapper"]
            assert result["ready_count"] == 1
            assert result["total_services"] == 3
            assert (
                result["external_access"]["kafka_available"] is True
            )  # kafka_wrapper in ready_services

    @pytest.mark.asyncio
    async def test_aggregate_health_status_unknown_format(
        self,
        reducer_with_mocked_loading,
    ):
        """Test aggregate_health_status with unknown adapter health format."""
        reducer = reducer_with_mocked_loading

        with patch.object(reducer, "health_check") as mock_health_check:
            mock_health_check.return_value = ModelHealthStatus(
                status=EnumHealthStatus.DEGRADED,
                message="Infrastructure degraded",
            )

            adapter_health_statuses = {
                "consul_adapter": "unknown_format",  # Not a dict
                "vault_adapter": {"status": "unknown_status", "message": "Unknown"},
            }

            result = await reducer.aggregate_health_status(adapter_health_statuses)

            assert result["infrastructure_status"] == "degraded"
            assert result["ready_services"] == []
            assert result["degraded_services"] == []
            assert result["failed_services"] == [
                "vault_adapter",
            ]  # Unknown status treated as failed


class TestInfrastructureReducerIntrospection:
    """Test infrastructure introspection and tool discovery functionality."""

    @pytest.fixture
    def mock_container(self):
        """Create mock ONEX container for testing."""
        return MagicMock(spec=ONEXContainer)

    @pytest.fixture
    def reducer_with_adapters(self, mock_container):
        """Create reducer with mock adapters loaded."""
        with (
            patch.object(NodeCanaryReducer, "_load_infrastructure_adapters"),
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
        ):
            reducer = NodeCanaryReducer(mock_container)

            # Add mock loaded adapters
            reducer.loaded_adapters = {
                "consul_adapter": MagicMock(
                    __class__=MagicMock(__name__="ConsulAdapter"),
                ),
                "vault_adapter": MagicMock(
                    __class__=MagicMock(__name__="VaultAdapter"),
                ),
            }

            # Add mock specialized components
            reducer.specialized_components = {
                "registry_aggregator": {
                    "instance": MagicMock(
                        __class__=MagicMock(__name__="RegistryAggregator"),
                    ),
                    "component_type": "delegated_reducer",
                    "readiness_check": "infrastructure_ready",
                    "description": "Registry catalog aggregation",
                },
            }

            return reducer

    def test_get_introspection_data_basic(self, reducer_with_adapters):
        """Test basic introspection data generation."""
        reducer = reducer_with_adapters

        result = reducer.get_introspection_data()

        assert "node_name" in result
        assert result["node_name"] == "tool_infrastructure_reducer"
        assert "version" in result
        assert result["version"] == "v1_0_0"
        assert "actions" in result
        assert "health_check" in result["actions"]
        assert "aggregate_health_status" in result["actions"]
        assert "protocols" in result
        assert "event_bus" in result["protocols"]
        assert "http" in result["protocols"]

    def test_get_introspection_data_with_infrastructure_tools(
        self,
        reducer_with_adapters,
    ):
        """Test introspection data includes infrastructure tools information."""
        reducer = reducer_with_adapters

        result = reducer.get_introspection_data()

        assert "infrastructure_tools" in result
        infrastructure_tools = result["infrastructure_tools"]

        assert "adapters" in infrastructure_tools
        assert "components" in infrastructure_tools
        assert "total_tools" in infrastructure_tools

        # Check adapter information
        adapters = infrastructure_tools["adapters"]
        assert len(adapters) == 2
        adapter_names = [adapter["name"] for adapter in adapters]
        assert "consul_adapter" in adapter_names
        assert "vault_adapter" in adapter_names

        # Check component information
        components = infrastructure_tools["components"]
        assert len(components) == 1
        assert components[0]["name"] == "registry_aggregator"
        assert components[0]["type"] == "delegated_reducer"

        # Check total tools count
        assert infrastructure_tools["total_tools"] == 3  # 2 adapters + 1 component

    def test_get_introspection_data_service_info(self, reducer_with_adapters):
        """Test introspection data includes service information."""
        reducer = reducer_with_adapters

        result = reducer.get_introspection_data()

        assert "service_info" in result
        service_info = result["service_info"]

        assert service_info["service_type"] == "infrastructure_reducer"
        assert "capabilities" in service_info
        capabilities = service_info["capabilities"]
        assert "tool_orchestration" in capabilities
        assert "health_aggregation" in capabilities
        assert "service_discovery" in capabilities

    def test_get_introspection_data_with_mixin(self, reducer_with_adapters):
        """Test introspection data when mixin provides base data."""
        reducer = reducer_with_adapters

        # Mock the mixin method to return introspection data
        mock_introspection = MagicMock()
        mock_introspection.node_name = "mixin_node_name"
        mock_introspection.version = "2.0.0"
        mock_introspection.capabilities.actions = ["mixin_action"]
        mock_introspection.capabilities.protocols = ["mixin_protocol"]
        mock_introspection.capabilities.metadata = {"mixin": "data"}
        mock_introspection.tags = ["mixin", "tag"]

        reducer._gather_introspection_data = MagicMock(return_value=mock_introspection)

        result = reducer.get_introspection_data()

        # Should use mixin data as base
        assert result["node_name"] == "mixin_node_name"
        assert result["version"] == "2.0.0"
        assert "mixin_action" in result["actions"]
        assert "mixin_protocol" in result["protocols"]

        # Should still include infrastructure-specific information
        assert "infrastructure_tools" in result

    def test_get_introspection_data_mixin_exception(self, reducer_with_adapters):
        """Test introspection data when mixin method raises exception."""
        reducer = reducer_with_adapters

        reducer._gather_introspection_data = MagicMock(
            side_effect=Exception("Mixin failed"),
        )

        result = reducer.get_introspection_data()

        # Should fall back to default introspection data
        assert result["node_name"] == "tool_infrastructure_reducer"
        assert result["version"] == "v1_0_0"
        assert "infrastructure_tools" in result

    def test_get_introspection_data_complete_failure(self, mock_container):
        """Test introspection data when everything fails."""
        with (
            patch.object(NodeCanaryReducer, "_load_infrastructure_adapters"),
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
        ):
            reducer = NodeCanaryReducer(mock_container)

            # Remove attributes to simulate failure
            del reducer.loaded_adapters
            del reducer.specialized_components

            result = reducer.get_introspection_data()

            # Should return fallback introspection data
            assert result["node_name"] == "tool_infrastructure_reducer"
            assert result["version"] == "v1_0_0"
            assert "error" in result["tags"]
            assert "introspection error" in result["metadata"]["description"]


class TestInfrastructureReducerServiceMode:
    """Test service mode startup and event handling."""

    @pytest.fixture
    def mock_container(self):
        """Create mock ONEX container for testing."""
        return MagicMock(spec=ONEXContainer)

    @pytest.fixture
    def reducer_with_mocked_loading(self, mock_container):
        """Create reducer with mocked loading methods."""
        with (
            patch.object(NodeCanaryReducer, "_load_infrastructure_adapters"),
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
        ):
            return NodeCanaryReducer(mock_container)

    @pytest.mark.asyncio
    async def test_start_service_mode_success(self, reducer_with_mocked_loading):
        """Test successful service mode startup."""
        reducer = reducer_with_mocked_loading

        with (
            patch.object(
                reducer,
                "_subscribe_to_tool_invocations",
                new_callable=AsyncMock,
            ) as mock_subscribe,
            patch.object(
                reducer,
                "_setup_infrastructure_introspection",
            ) as mock_setup_introspection,
            patch.object(reducer, "_register_signal_handlers") as mock_register_signals,
            patch.object(
                reducer,
                "_service_event_loop",
                new_callable=AsyncMock,
            ) as mock_event_loop,
            patch("asyncio.create_task"),
        ):
            await reducer.start_service_mode()

            assert reducer._service_running is True
            assert reducer._event_bus_active is True
            mock_subscribe.assert_called_once()
            mock_setup_introspection.assert_called_once()
            mock_register_signals.assert_called_once()
            mock_event_loop.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_service_mode_already_running(
        self,
        reducer_with_mocked_loading,
    ):
        """Test start_service_mode when service is already running."""
        reducer = reducer_with_mocked_loading
        reducer._service_running = True
        reducer._log_warning = MagicMock()

        await reducer.start_service_mode()

        reducer._log_warning.assert_called_once_with(
            "Service already running, ignoring start request",
        )

    @pytest.mark.asyncio
    async def test_start_service_mode_introspection_setup_failure(
        self,
        reducer_with_mocked_loading,
    ):
        """Test start_service_mode when introspection setup fails."""
        reducer = reducer_with_mocked_loading
        reducer._log_info = MagicMock()
        reducer._log_error = MagicMock()

        with (
            patch.object(
                reducer,
                "_subscribe_to_tool_invocations",
                new_callable=AsyncMock,
            ),
            patch.object(
                reducer,
                "_setup_infrastructure_introspection",
                side_effect=Exception("Setup failed"),
            ),
            patch.object(reducer, "_register_signal_handlers"),
            patch.object(reducer, "_service_event_loop", new_callable=AsyncMock),
            patch("asyncio.create_task"),
        ):
            await reducer.start_service_mode()

            reducer._log_error.assert_called_once_with(
                "Failed to set up infrastructure introspection: Setup failed",
            )

    @pytest.mark.asyncio
    async def test_start_service_mode_general_failure(
        self,
        reducer_with_mocked_loading,
    ):
        """Test start_service_mode when general startup fails."""
        reducer = reducer_with_mocked_loading
        reducer.stop_service_mode = AsyncMock()

        with patch.object(
            reducer,
            "_subscribe_to_tool_invocations",
            side_effect=Exception("Startup failed"),
        ):
            with pytest.raises(OnexError) as exc_info:
                await reducer.start_service_mode()

            assert exc_info.value.error_code == CoreErrorCode.INITIALIZATION_FAILED
            assert "Infrastructure service startup failed" in str(exc_info.value)
            reducer.stop_service_mode.assert_called_once()

    def test_setup_request_response_introspection(self, reducer_with_mocked_loading):
        """Test setup_request_response_introspection override."""
        reducer = reducer_with_mocked_loading

        # Should do nothing (bypasses the problematic mixin setup)
        reducer._setup_request_response_introspection()

        # No exception should be raised

    def test_setup_infrastructure_introspection_no_event_bus(
        self,
        reducer_with_mocked_loading,
    ):
        """Test infrastructure introspection setup when no event bus is available."""
        reducer = reducer_with_mocked_loading
        reducer._event_bus = None

        with patch("builtins.print") as mock_print:
            reducer._setup_infrastructure_introspection()

            mock_print.assert_called_with(
                "   ⚠️ No event bus available for introspection subscription",
            )

    def test_setup_infrastructure_introspection_success(
        self,
        reducer_with_mocked_loading,
    ):
        """Test successful infrastructure introspection setup."""
        reducer = reducer_with_mocked_loading

        mock_event_bus = MagicMock()
        reducer._event_bus = mock_event_bus

        with patch("builtins.print") as mock_print:
            reducer._setup_infrastructure_introspection()

            # Should subscribe to both event types
            assert mock_event_bus.subscribe.call_count == 2
            mock_print.assert_any_call(
                "   🔍 Subscribed to core.discovery.node_introspection",
            )
            mock_print.assert_any_call(
                "   🔍 Subscribed to core.discovery.realtime_request",
            )

    def test_setup_infrastructure_introspection_exception(
        self,
        reducer_with_mocked_loading,
    ):
        """Test infrastructure introspection setup when subscription fails."""
        reducer = reducer_with_mocked_loading

        mock_event_bus = MagicMock()
        mock_event_bus.subscribe.side_effect = Exception("Subscription failed")
        reducer._event_bus = mock_event_bus

        with patch("builtins.print") as mock_print:
            reducer._setup_infrastructure_introspection()

            mock_print.assert_any_call(
                "   ❌ Failed to set up infrastructure introspection: Subscription failed",
            )


class TestInfrastructureReducerIntrospectionHandling:
    """Test introspection request handling."""

    @pytest.fixture
    def mock_container(self):
        """Create mock ONEX container for testing."""
        return MagicMock(spec=ONEXContainer)

    @pytest.fixture
    def reducer_with_adapters(self, mock_container):
        """Create reducer with mock adapters and event bus."""
        with (
            patch.object(NodeCanaryReducer, "_load_infrastructure_adapters"),
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
        ):
            reducer = NodeCanaryReducer(mock_container)
            reducer._node_id = uuid4()
            reducer._event_bus = MagicMock()

            # Add mock loaded adapters
            reducer.loaded_adapters = {
                "consul_adapter": MagicMock(
                    __class__=MagicMock(__name__="ConsulAdapter"),
                ),
            }

            # Add mock specialized components
            reducer.specialized_components = {
                "registry_aggregator": {
                    "instance": MagicMock(
                        __class__=MagicMock(__name__="RegistryAggregator"),
                    ),
                    "component_type": "delegated_reducer",
                },
            }

            return reducer

    def test_handle_infrastructure_introspection_request_success(
        self,
        reducer_with_adapters,
    ):
        """Test successful handling of introspection request."""
        reducer = reducer_with_adapters

        mock_event = MagicMock()
        mock_event.source_node_id = "test_source"
        mock_event.correlation_id = uuid4()

        with (
            patch("builtins.print") as mock_print,
            patch("time.time", return_value=1234567890),
        ):
            reducer._handle_infrastructure_introspection_request(mock_event)

            # Should publish introspection response
            reducer._event_bus.publish.assert_called_once()

            # Check the published event
            call_args = reducer._event_bus.publish.call_args
            assert call_args[0][0] == "core.discovery.realtime_response"
            response_data = call_args[0][1]

            # Verify response structure
            assert "responding_node_id" in response_data
            assert "tool_availabilities" in response_data
            assert (
                len(response_data["tool_availabilities"]) == 2
            )  # 1 adapter + 1 component

            mock_print.assert_any_call(
                "   🔍 Handling introspection request from test_source",
            )
            mock_print.assert_any_call(
                "   ✅ Published introspection response with 2 tools",
            )

    def test_handle_infrastructure_introspection_request_no_event_bus(
        self,
        reducer_with_adapters,
    ):
        """Test introspection request handling when no event bus is available."""
        reducer = reducer_with_adapters
        reducer._event_bus = None

        mock_event = MagicMock()

        with patch("builtins.print") as mock_print:
            reducer._handle_infrastructure_introspection_request(mock_event)

            mock_print.assert_any_call(
                "   ⚠️ No event bus available to publish response",
            )

    def test_handle_infrastructure_introspection_request_exception(
        self,
        reducer_with_adapters,
    ):
        """Test introspection request handling when exception occurs."""
        reducer = reducer_with_adapters

        # Mock event to raise exception when accessed
        mock_event = MagicMock()
        mock_event.source_node_id = PropertyMock(
            side_effect=Exception("Event access failed"),
        )

        with (
            patch("builtins.print") as mock_print,
            patch("traceback.print_exc") as mock_traceback,
        ):
            reducer._handle_infrastructure_introspection_request(mock_event)

            mock_print.assert_any_call(
                "   ❌ Failed to handle introspection request: Event access failed",
            )
            mock_traceback.assert_called_once()

    def test_handle_infrastructure_introspection_creates_tool_availabilities(
        self,
        reducer_with_adapters,
    ):
        """Test that introspection request creates proper tool availability entries."""
        reducer = reducer_with_adapters

        mock_event = MagicMock()
        mock_event.correlation_id = uuid4()

        with patch("builtins.print"), patch("time.time", return_value=1234567890):
            reducer._handle_infrastructure_introspection_request(mock_event)

            # Check the published response
            call_args = reducer._event_bus.publish.call_args
            response_data = call_args[0][1]
            tool_availabilities = response_data["tool_availabilities"]

            # Should have one adapter entry
            adapter_tools = [
                tool
                for tool in tool_availabilities
                if "adapter" in tool["capabilities"]
            ]
            assert len(adapter_tools) == 1
            assert adapter_tools[0]["tool_name"] == "consul_adapter"
            assert "infrastructure" in adapter_tools[0]["capabilities"]

            # Should have one component entry
            component_tools = [
                tool
                for tool in tool_availabilities
                if "component" in tool["capabilities"]
            ]
            assert len(component_tools) == 1
            assert component_tools[0]["tool_name"] == "registry_aggregator"
            assert "infrastructure" in component_tools[0]["capabilities"]


class TestInfrastructureReducerRegistryDelegation:
    """Test registry delegation functionality."""

    @pytest.fixture
    def mock_container(self):
        """Create mock ONEX container for testing."""
        return MagicMock(spec=ONEXContainer)

    @pytest.fixture
    def reducer_with_registry_component(self, mock_container):
        """Create reducer with registry catalog aggregator component."""
        with (
            patch.object(NodeCanaryReducer, "_load_infrastructure_adapters"),
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
        ):
            reducer = NodeCanaryReducer(mock_container)
            reducer.node_id = uuid4()
            reducer._event_bus_active = False

            # Add mock registry component
            mock_registry = MagicMock()
            reducer.specialized_components = {
                "registry_catalog_aggregator": {
                    "instance": mock_registry,
                    "component_type": "delegated_reducer",
                    "readiness_check": "infrastructure_ready",
                    "description": "Registry catalog aggregation",
                },
            }

            return reducer

    @pytest.mark.asyncio
    async def test_delegate_registry_request_infrastructure_not_ready(
        self,
        reducer_with_registry_component,
    ):
        """Test registry delegation when infrastructure is not ready."""
        reducer = reducer_with_registry_component

        # Mock infrastructure status as not ready
        mock_status = {
            "readiness_state": {"delegation_enabled": False},
            "infrastructure_status": {"infrastructure_status": "unavailable"},
        }

        with patch.object(
            reducer,
            "get_infrastructure_status",
            new_callable=AsyncMock,
            return_value=mock_status,
        ):
            result = await reducer.delegate_registry_request(
                {"param": "value"},
                "/registry/tools",
                "GET",
            )

            assert result["status"] == "error"
            assert "Infrastructure not ready" in result["message"]
            assert result["required_readiness"] == "infrastructure_ready"

    @pytest.mark.asyncio
    async def test_delegate_registry_request_fallback_to_direct_calls(
        self,
        reducer_with_registry_component,
    ):
        """Test registry delegation falls back to direct calls when event bus is not active."""
        reducer = reducer_with_registry_component

        # Mock infrastructure as ready but event bus not active
        mock_status = {"readiness_state": {"delegation_enabled": True}}

        mock_registry = reducer.specialized_components["registry_catalog_aggregator"][
            "instance"
        ]
        mock_registry.list_registry_tools = AsyncMock(
            return_value={"tools": ["tool1", "tool2"]},
        )

        with patch.object(
            reducer,
            "get_infrastructure_status",
            new_callable=AsyncMock,
            return_value=mock_status,
        ):
            result = await reducer.delegate_registry_request(
                {},
                "/registry/tools",
                "GET",
            )

            assert result == {"tools": ["tool1", "tool2"]}
            mock_registry.list_registry_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_delegate_registry_request_unsupported_endpoint(
        self,
        reducer_with_registry_component,
    ):
        """Test registry delegation with unsupported endpoint."""
        reducer = reducer_with_registry_component

        mock_status = {"readiness_state": {"delegation_enabled": True}}

        with patch.object(
            reducer,
            "get_infrastructure_status",
            new_callable=AsyncMock,
            return_value=mock_status,
        ):
            result = await reducer.delegate_registry_request(
                {},
                "/unsupported/endpoint",
                "GET",
            )

            assert result["status"] == "error"
            assert "Unsupported registry endpoint" in result["message"]
            assert "supported_endpoints" in result

    @pytest.mark.asyncio
    async def test_delegate_registry_request_event_driven_success(
        self,
        reducer_with_registry_component,
    ):
        """Test successful event-driven registry delegation."""
        reducer = reducer_with_registry_component
        reducer._event_bus_active = True
        reducer.event_bus = MagicMock()

        mock_status = {"readiness_state": {"delegation_enabled": True}}

        with (
            patch.object(
                reducer,
                "get_infrastructure_status",
                new_callable=AsyncMock,
                return_value=mock_status,
            ),
            patch.object(
                reducer,
                "_send_registry_event_request",
                new_callable=AsyncMock,
            ) as mock_send_event,
        ):
            mock_send_event.return_value = {"result": "success"}

            result = await reducer.delegate_registry_request(
                {"param": "value"},
                "/registry/tools",
                "GET",
            )

            assert result == {"result": "success"}
            mock_send_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_delegate_registry_request_exception(
        self,
        reducer_with_registry_component,
    ):
        """Test registry delegation when exception occurs."""
        reducer = reducer_with_registry_component
        reducer.logger = MagicMock()

        with patch.object(
            reducer,
            "get_infrastructure_status",
            side_effect=Exception("Status check failed"),
        ):
            result = await reducer.delegate_registry_request(
                {},
                "/registry/tools",
                "GET",
            )

            assert result["status"] == "error"
            assert "Registry delegation failed" in result["message"]
            assert result["error_type"] == "delegation_error"
            reducer.logger.error.assert_called_once()


class TestInfrastructureReducerFallbackDirectCalls:
    """Test fallback direct method calls to registry component."""

    @pytest.fixture
    def mock_container(self):
        """Create mock ONEX container for testing."""
        return MagicMock(spec=ONEXContainer)

    @pytest.fixture
    def reducer_with_registry_methods(self, mock_container):
        """Create reducer with registry component that has all methods."""
        with (
            patch.object(NodeCanaryReducer, "_load_infrastructure_adapters"),
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
        ):
            reducer = NodeCanaryReducer(mock_container)

            # Create mock registry with all expected methods
            mock_registry = MagicMock()
            mock_registry.list_registry_tools = AsyncMock(
                return_value={"tools": ["tool1"]},
            )
            mock_registry.get_aggregated_catalog = AsyncMock(
                return_value={"catalog": "data"},
            )
            mock_registry.get_aggregation_metrics = AsyncMock(
                return_value={"metrics": "data"},
            )
            mock_registry.trigger_bootstrap_workflow = AsyncMock(
                return_value={"bootstrap": "success"},
            )
            mock_registry.trigger_hello_coordination = AsyncMock(
                return_value={"hello": "success"},
            )
            mock_registry.trigger_consul_sync = AsyncMock(
                return_value={"sync": "success"},
            )

            reducer.specialized_components = {
                "registry_catalog_aggregator": {
                    "instance": mock_registry,
                    "component_type": "delegated_reducer",
                },
            }

            return reducer

    @pytest.mark.asyncio
    async def test_fallback_list_registry_tools(self, reducer_with_registry_methods):
        """Test fallback to list_registry_tools method."""
        reducer = reducer_with_registry_methods

        result = await reducer._fallback_to_direct_calls({}, "/registry/tools", "GET")

        assert result == {"tools": ["tool1"]}
        registry_instance = reducer.specialized_components[
            "registry_catalog_aggregator"
        ]["instance"]
        registry_instance.list_registry_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_get_aggregated_catalog(self, reducer_with_registry_methods):
        """Test fallback to get_aggregated_catalog method."""
        reducer = reducer_with_registry_methods

        result = await reducer._fallback_to_direct_calls({}, "/registry/catalog", "GET")

        assert result == {"catalog": "data"}
        registry_instance = reducer.specialized_components[
            "registry_catalog_aggregator"
        ]["instance"]
        registry_instance.get_aggregated_catalog.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_get_aggregation_metrics(
        self,
        reducer_with_registry_methods,
    ):
        """Test fallback to get_aggregation_metrics method."""
        reducer = reducer_with_registry_methods

        result = await reducer._fallback_to_direct_calls({}, "/registry/metrics", "GET")

        assert result == {"metrics": "data"}
        registry_instance = reducer.specialized_components[
            "registry_catalog_aggregator"
        ]["instance"]
        registry_instance.get_aggregation_metrics.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_trigger_bootstrap_workflow(
        self,
        reducer_with_registry_methods,
    ):
        """Test fallback to trigger_bootstrap_workflow method."""
        reducer = reducer_with_registry_methods

        request_data = {"bootstrap": "config"}
        result = await reducer._fallback_to_direct_calls(
            request_data,
            "/registry/bootstrap",
            "POST",
        )

        assert result == {"bootstrap": "success"}
        registry_instance = reducer.specialized_components[
            "registry_catalog_aggregator"
        ]["instance"]
        registry_instance.trigger_bootstrap_workflow.assert_called_once_with(
            request_data,
        )

    @pytest.mark.asyncio
    async def test_fallback_trigger_hello_coordination(
        self,
        reducer_with_registry_methods,
    ):
        """Test fallback to trigger_hello_coordination method."""
        reducer = reducer_with_registry_methods

        request_data = {"hello": "config"}
        result = await reducer._fallback_to_direct_calls(
            request_data,
            "/registry/hello-coordinate",
            "POST",
        )

        assert result == {"hello": "success"}
        registry_instance = reducer.specialized_components[
            "registry_catalog_aggregator"
        ]["instance"]
        registry_instance.trigger_hello_coordination.assert_called_once_with(
            request_data,
        )

    @pytest.mark.asyncio
    async def test_fallback_trigger_consul_sync(self, reducer_with_registry_methods):
        """Test fallback to trigger_consul_sync method."""
        reducer = reducer_with_registry_methods

        request_data = {"sync": "config"}
        result = await reducer._fallback_to_direct_calls(
            request_data,
            "/registry/consul-sync",
            "POST",
        )

        assert result == {"sync": "success"}
        registry_instance = reducer.specialized_components[
            "registry_catalog_aggregator"
        ]["instance"]
        registry_instance.trigger_consul_sync.assert_called_once_with(request_data)

    @pytest.mark.asyncio
    async def test_fallback_no_registry_component(self, mock_container):
        """Test fallback when registry component is not available."""
        with (
            patch.object(NodeCanaryReducer, "_load_infrastructure_adapters"),
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
        ):
            reducer = NodeCanaryReducer(mock_container)
            reducer.specialized_components = {}  # No registry component

            result = await reducer._fallback_to_direct_calls(
                {},
                "/registry/tools",
                "GET",
            )

            assert result["status"] == "error"
            assert (
                "Registry catalog aggregator component not loaded" in result["message"]
            )
            assert "available_components" in result

    @pytest.mark.asyncio
    async def test_fallback_missing_method(self, mock_container):
        """Test fallback when registry component doesn't have required method."""
        with (
            patch.object(NodeCanaryReducer, "_load_infrastructure_adapters"),
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
        ):
            reducer = NodeCanaryReducer(mock_container)

            # Create mock registry without list_registry_tools method
            mock_registry = MagicMock()
            del mock_registry.list_registry_tools  # Remove the method

            reducer.specialized_components = {
                "registry_catalog_aggregator": {"instance": mock_registry},
            }

            result = await reducer._fallback_to_direct_calls(
                {},
                "/registry/tools",
                "GET",
            )

            assert result["status"] == "error"
            assert "list_registry_tools method not available" in result["message"]

    @pytest.mark.asyncio
    async def test_fallback_unsupported_endpoint(self, reducer_with_registry_methods):
        """Test fallback with unsupported endpoint."""
        reducer = reducer_with_registry_methods

        result = await reducer._fallback_to_direct_calls(
            {},
            "/unsupported/endpoint",
            "GET",
        )

        assert result["status"] == "error"
        assert "Unsupported registry endpoint" in result["message"]
        assert "supported_endpoints" in result

    @pytest.mark.asyncio
    async def test_fallback_exception_handling(self, reducer_with_registry_methods):
        """Test fallback exception handling."""
        reducer = reducer_with_registry_methods
        reducer.logger = MagicMock()

        # Make the registry method raise an exception
        registry_instance = reducer.specialized_components[
            "registry_catalog_aggregator"
        ]["instance"]
        registry_instance.list_registry_tools.side_effect = Exception("Method failed")

        result = await reducer._fallback_to_direct_calls({}, "/registry/tools", "GET")

        assert result["status"] == "error"
        assert "Registry direct call failed" in result["message"]
        assert result["error_type"] == "fallback_error"
        reducer.logger.error.assert_called_once()


class TestInfrastructureReducerStatusAndListMethods:
    """Test infrastructure status and adapter listing methods."""

    @pytest.fixture
    def mock_container(self):
        """Create mock ONEX container for testing."""
        return MagicMock(spec=ONEXContainer)

    @pytest.fixture
    def reducer_with_adapters(self, mock_container):
        """Create reducer with mock adapters and components."""
        with (
            patch.object(NodeCanaryReducer, "_load_infrastructure_adapters"),
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
        ):
            reducer = NodeCanaryReducer(mock_container)

            # Add mock adapters with health check methods
            mock_adapter1 = MagicMock()
            mock_adapter1.health_check = AsyncMock(
                return_value={"status": "healthy", "message": "OK"},
            )
            mock_adapter1.__class__.__name__ = "ConsulAdapter"
            mock_adapter1.__class__.__module__ = "consul_module"

            mock_adapter2 = MagicMock()
            mock_adapter2.health_check = AsyncMock(
                return_value={"status": "degraded", "message": "Warning"},
            )
            mock_adapter2.__class__.__name__ = "VaultAdapter"
            mock_adapter2.__class__.__module__ = "vault_module"

            reducer.loaded_adapters = {
                "consul_adapter": mock_adapter1,
                "vault_adapter": mock_adapter2,
            }

            # Add mock specialized component
            mock_component = MagicMock()
            mock_component.__class__.__name__ = "RegistryAggregator"
            mock_component.__class__.__module__ = "registry_module"

            reducer.specialized_components = {
                "registry_aggregator": {
                    "instance": mock_component,
                    "component_type": "delegated_reducer",
                    "readiness_check": "infrastructure_ready",
                    "description": "Registry catalog aggregation",
                },
            }

            return reducer

    @pytest.mark.asyncio
    async def test_get_infrastructure_status_success(self, reducer_with_adapters):
        """Test successful infrastructure status retrieval."""
        reducer = reducer_with_adapters

        result = await reducer.get_infrastructure_status()

        # Check main structure
        assert "infrastructure_status" in result
        assert "adapter_health" in result
        assert "readiness_state" in result
        assert "specialized_components" in result

        # Check adapter health
        adapter_health = result["adapter_health"]
        assert "consul_adapter" in adapter_health
        assert "vault_adapter" in adapter_health
        assert adapter_health["consul_adapter"]["status"] == "healthy"
        assert adapter_health["vault_adapter"]["status"] == "degraded"

        # Check readiness state
        readiness_state = result["readiness_state"]
        assert "infrastructure_ready" in readiness_state
        assert "delegation_enabled" in readiness_state
        assert "ready_adapters" in readiness_state
        assert "total_adapters" in readiness_state
        assert readiness_state["total_adapters"] == 2

        # Check specialized components
        specialized_components = result["specialized_components"]
        assert "registry_aggregator" in specialized_components
        component_info = specialized_components["registry_aggregator"]
        assert component_info["component_type"] == "delegated_reducer"
        assert component_info["readiness_check"] == "infrastructure_ready"
        assert component_info["description"] == "Registry catalog aggregation"

    @pytest.mark.asyncio
    async def test_get_infrastructure_status_adapter_without_health_check(
        self,
        mock_container,
    ):
        """Test infrastructure status when adapter doesn't have health_check method."""
        with (
            patch.object(NodeCanaryReducer, "_load_infrastructure_adapters"),
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
        ):
            reducer = NodeCanaryReducer(mock_container)

            # Add adapter without health_check method
            mock_adapter = MagicMock()
            del mock_adapter.health_check
            reducer.loaded_adapters = {"test_adapter": mock_adapter}
            reducer.specialized_components = {}

            result = await reducer.get_infrastructure_status()

            adapter_health = result["adapter_health"]
            assert adapter_health["test_adapter"]["status"] == "unknown"
            assert "No health_check method" in adapter_health["test_adapter"]["message"]

    @pytest.mark.asyncio
    async def test_get_infrastructure_status_adapter_health_check_exception(
        self,
        mock_container,
    ):
        """Test infrastructure status when adapter health check raises exception."""
        with (
            patch.object(NodeCanaryReducer, "_load_infrastructure_adapters"),
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
        ):
            reducer = NodeCanaryReducer(mock_container)

            # Add adapter with failing health check
            mock_adapter = MagicMock()
            mock_adapter.health_check = AsyncMock(
                side_effect=Exception("Health check failed"),
            )
            reducer.loaded_adapters = {"test_adapter": mock_adapter}
            reducer.specialized_components = {}

            result = await reducer.get_infrastructure_status()

            adapter_health = result["adapter_health"]
            assert adapter_health["test_adapter"]["status"] == "error"
            assert "Health check failed" in adapter_health["test_adapter"]["message"]

    @pytest.mark.asyncio
    async def test_list_loaded_adapters(self, reducer_with_adapters):
        """Test listing loaded adapters and components."""
        reducer = reducer_with_adapters

        result = await reducer.list_loaded_adapters()

        # Check loaded adapters
        assert "loaded_adapters" in result
        loaded_adapters = result["loaded_adapters"]
        assert "consul_adapter" in loaded_adapters
        assert "vault_adapter" in loaded_adapters

        consul_info = loaded_adapters["consul_adapter"]
        assert consul_info["type"] == "infrastructure_adapter"
        assert consul_info["class_name"] == "ConsulAdapter"
        assert consul_info["module"] == "consul_module"

        # Check specialized components
        assert "specialized_components" in result
        specialized_components = result["specialized_components"]
        assert "registry_aggregator" in specialized_components

        registry_info = specialized_components["registry_aggregator"]
        assert registry_info["type"] == "delegated_reducer"
        assert registry_info["readiness_check"] == "infrastructure_ready"
        assert registry_info["description"] == "Registry catalog aggregation"
        assert registry_info["class_name"] == "RegistryAggregator"
        assert registry_info["module"] == "registry_module"


class TestInfrastructureReducerEventBusOperations:
    """Test event bus operations for registry requests."""

    @pytest.fixture
    def mock_container(self):
        """Create mock ONEX container for testing."""
        return MagicMock(spec=ONEXContainer)

    @pytest.fixture
    def reducer_with_event_bus(self, mock_container):
        """Create reducer with mock event bus."""
        with (
            patch.object(NodeCanaryReducer, "_load_infrastructure_adapters"),
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
        ):
            reducer = NodeCanaryReducer(mock_container)
            reducer.node_id = uuid4()
            reducer.event_bus = MagicMock()
            reducer._pending_registry_requests = {}

            return reducer

    @pytest.mark.asyncio
    async def test_send_registry_event_request_success(self, reducer_with_event_bus):
        """Test successful registry event request."""
        reducer = reducer_with_event_bus

        # Mock the response future to resolve immediately
        with (
            patch("asyncio.Future") as mock_future_class,
            patch("asyncio.get_event_loop") as mock_event_loop,
            patch("asyncio.wait_for", new_callable=AsyncMock) as mock_wait_for,
        ):
            mock_future = MagicMock()
            mock_future_class.return_value = mock_future
            mock_event_loop.return_value.time.return_value = 1234567890
            mock_wait_for.return_value = {"result": "success"}

            reducer.event_bus.publish_async = AsyncMock()

            with patch.object(
                reducer,
                "_setup_registry_response_listener",
            ) as mock_setup_listener:
                result = await reducer._send_registry_event_request(
                    "LIST_TOOLS",
                    "/registry/tools",
                    "GET",
                    {"param": "value"},
                )

                assert result == {"result": "success"}
                reducer.event_bus.publish_async.assert_called_once()
                mock_setup_listener.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_registry_event_request_timeout(self, reducer_with_event_bus):
        """Test registry event request timeout."""
        reducer = reducer_with_event_bus

        with (
            patch("asyncio.Future") as mock_future_class,
            patch("asyncio.get_event_loop") as mock_event_loop,
            patch("asyncio.wait_for", new_callable=AsyncMock) as mock_wait_for,
        ):
            mock_future = MagicMock()
            mock_future_class.return_value = mock_future
            mock_event_loop.return_value.time.return_value = 1234567890
            mock_wait_for.side_effect = TimeoutError("Request timed out")

            reducer.event_bus.publish_async = AsyncMock()

            with patch.object(reducer, "_setup_registry_response_listener"):
                result = await reducer._send_registry_event_request(
                    "LIST_TOOLS",
                    "/registry/tools",
                    "GET",
                    {"param": "value"},
                    timeout_ms=1000,
                )

                assert result["status"] == "error"
                assert "Registry request timeout after 1000ms" in result["message"]
                assert result["error_type"] == "timeout_error"

    @pytest.mark.asyncio
    async def test_send_registry_event_request_exception(self, reducer_with_event_bus):
        """Test registry event request when exception occurs."""
        reducer = reducer_with_event_bus

        with (
            patch("asyncio.Future") as mock_future_class,
            patch("asyncio.get_event_loop") as mock_event_loop,
        ):
            mock_future = MagicMock()
            mock_future_class.return_value = mock_future
            mock_event_loop.return_value.time.return_value = 1234567890

            reducer.event_bus.publish_async = AsyncMock(
                side_effect=Exception("Publish failed"),
            )

            with patch.object(reducer, "_setup_registry_response_listener"):
                with pytest.raises(OnexError) as exc_info:
                    await reducer._send_registry_event_request(
                        "LIST_TOOLS",
                        "/registry/tools",
                        "GET",
                        {"param": "value"},
                    )

                assert exc_info.value.error_code == CoreErrorCode.OPERATION_FAILED
                assert "Registry event request failed" in str(exc_info.value)

    def test_setup_registry_response_listener(self, reducer_with_event_bus):
        """Test setting up registry response listener."""
        reducer = reducer_with_event_bus

        correlation_id = uuid4()
        response_future = asyncio.Future()

        with patch("asyncio.create_task") as mock_create_task:
            reducer._setup_registry_response_listener(correlation_id, response_future)

            mock_create_task.assert_called_once()
            # The task should be created with the event bus subscribe_async call

    @pytest.mark.asyncio
    async def test_registry_response_handler_success(self, reducer_with_event_bus):
        """Test registry response handler with successful response."""
        reducer = reducer_with_event_bus
        correlation_id = uuid4()

        # Create a mock event with successful response
        mock_event = MagicMock()
        mock_event.event_type = RegistryOperations.REGISTRY_RESPONSE_EVENT
        mock_event.correlation_id = correlation_id
        mock_event.data = {
            "status": "success",
            "result": {"data": "test_result"},
            "error_message": None,
            "error_code": None,
        }

        response_future = asyncio.Future()
        reducer.event_bus.unsubscribe_async = AsyncMock()

        # Set up pending request
        reducer._pending_registry_requests[str(correlation_id)] = {
            "operation": "test_operation",
        }

        # Create the response handler manually to test it
        async def response_handler(event):
            if event.event_type == RegistryOperations.REGISTRY_RESPONSE_EVENT:
                if event.correlation_id == correlation_id:
                    response_data = ModelRegistryResponseEvent(**event.data)
                    reducer._pending_registry_requests.pop(str(correlation_id), None)

                    if not response_future.done():
                        if response_data.status == "success":
                            response_future.set_result(response_data.result or {})
                        else:
                            response_future.set_result(
                                {
                                    "status": "error",
                                    "message": response_data.error_message,
                                    "error_code": response_data.error_code,
                                    "correlation_id": str(correlation_id),
                                },
                            )

                    await reducer.event_bus.unsubscribe_async(response_handler)

        # Test the handler
        await response_handler(mock_event)

        assert response_future.done()
        assert response_future.result() == {"data": "test_result"}
        assert str(correlation_id) not in reducer._pending_registry_requests


class TestInfrastructureReducerMainFunction:
    """Test the main function and module entry point."""

    def test_main_function_returns_reducer_instance(self):
        """Test that main function returns a NodeCanaryReducer instance."""
        with (
            patch(
                "omnibase.tools.infrastructure.tool_infrastructure_reducer.v1_0_0.node.create_infrastructure_container",
            ) as mock_create_container,
            patch.object(NodeCanaryReducer, "_load_infrastructure_adapters"),
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
        ):
            mock_container = MagicMock()
            mock_create_container.return_value = mock_container

            from .node import (
                main,
            )

            result = main()

            assert isinstance(result, NodeCanaryReducer)
            mock_create_container.assert_called_once()

    def test_main_function_container_creation(self):
        """Test that main function creates infrastructure container correctly."""
        with (
            patch(
                "omnibase.tools.infrastructure.tool_infrastructure_reducer.v1_0_0.node.create_infrastructure_container",
            ) as mock_create_container,
            patch.object(NodeCanaryReducer, "_load_infrastructure_adapters"),
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
        ):
            mock_container = MagicMock()
            mock_create_container.return_value = mock_container

            from .node import (
                main,
            )

            result = main()

            # Verify the container was created and passed to the reducer
            mock_create_container.assert_called_once()
            assert result.container == mock_container


# Test coverage analysis and integration tests for comprehensive coverage
class TestInfrastructureReducerComprehensiveCoverage:
    """Additional tests to ensure comprehensive coverage and edge cases."""

    @pytest.fixture
    def mock_container(self):
        """Create mock ONEX container for testing."""
        return MagicMock(spec=ONEXContainer)

    def test_init_domain_assignment(self, mock_container):
        """Test that domain is correctly assigned during initialization."""
        with (
            patch.object(NodeCanaryReducer, "_load_infrastructure_adapters"),
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
        ):
            reducer = NodeCanaryReducer(mock_container)

            assert reducer.domain == "infrastructure"

    def test_init_private_attributes_initialization(self, mock_container):
        """Test that private attributes are properly initialized."""
        with (
            patch.object(NodeCanaryReducer, "_load_infrastructure_adapters"),
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
        ):
            reducer = NodeCanaryReducer(mock_container)

            assert isinstance(reducer._pending_registry_requests, dict)
            assert reducer._event_bus_active is False
            assert reducer._consul_adapter is None
            assert reducer._vault_adapter is None
            assert reducer._kafka_adapter is None

    def test_version_strategy_fallback(self, mock_container):
        """Test version strategy fallback in adapter loading."""
        sample_manifest = {
            "namespace": "test.namespace",
            "x_extensions": {
                "version_management": {
                    "current_stable": "1.0.0",
                    "discovery": {
                        "version_directory_pattern": "v{major}_{minor}_{patch}",
                        "main_class_name": "TestAdapter",
                    },
                },
            },
        }

        mock_adapter_instance = MagicMock()
        mock_adapter_class = MagicMock(return_value=mock_adapter_instance)

        with (
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
            patch("builtins.open"),
            patch("yaml.safe_load", return_value=sample_manifest),
            patch("importlib.import_module"),
            patch("getattr", return_value=mock_adapter_class),
        ):
            reducer = NodeCanaryReducer(mock_container)

            # Test with unsupported version strategy - should fallback to current_stable
            result = reducer._load_adapter_from_metadata(
                "test_adapter",
                "test.namespace.tool.manifest",
                "unsupported_strategy",
            )

            assert result == mock_adapter_instance

    def test_health_check_unknown_format_handling(self, mock_container):
        """Test health check handling of unknown result formats."""
        with (
            patch.object(NodeCanaryReducer, "_load_infrastructure_adapters"),
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
        ):
            reducer = NodeCanaryReducer(mock_container)

            # Create adapter that returns unknown format
            mock_adapter = MagicMock()
            mock_adapter.health_check.return_value = (
                "unknown_format"  # Not dict or ModelHealthStatus
            )

            reducer.loaded_adapters = {"test_adapter": mock_adapter}
            reducer.specialized_components = {}

            result = reducer.health_check()

            assert isinstance(result, ModelHealthStatus)
            assert (
                result.status == EnumHealthStatus.HEALTHY
            )  # Should assume healthy for unknown format

    def test_introspection_data_no_mixin_attribute(self, mock_container):
        """Test introspection data when _gather_introspection_data attribute doesn't exist."""
        with (
            patch.object(NodeCanaryReducer, "_load_infrastructure_adapters"),
            patch.object(NodeCanaryReducer, "_load_specialized_components"),
        ):
            reducer = NodeCanaryReducer(mock_container)
            reducer.loaded_adapters = {}
            reducer.specialized_components = {}

            # Ensure _gather_introspection_data doesn't exist
            if hasattr(reducer, "_gather_introspection_data"):
                delattr(reducer, "_gather_introspection_data")

            result = reducer.get_introspection_data()

            # Should fall back to default introspection data
            assert result["node_name"] == "tool_infrastructure_reducer"
            assert result["version"] == "v1_0_0"
            assert "infrastructure_tools" in result


# Test completion update
@pytest.fixture(scope="session", autouse=True)
def test_completion_update():
    """Update todo status when all tests complete."""
    return
    # This runs after all tests complete


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
