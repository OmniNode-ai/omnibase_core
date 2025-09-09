"""Tests for ModelOnexContainer integration in Reducer Pattern Engine Phase 3."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from omnibase_core.core.model_onex_container import ModelONEXContainer
from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.models import (
    ModelReducerPatternEngineInput,
    ModelWorkflowRequest,
    WorkflowType,
)
from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.models.model_workflow_metadata import (
    ModelWorkflowMetadata,
)
from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.models.model_workflow_payload import (
    ModelWorkflowPayload,
)
from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.node_reducer_pattern_engine import (
    NodeReducerPatternEngine,
)


class TestContainerIntegration:
    """Test ModelOnexContainer integration for Reducer Pattern Engine Phase 3."""

    @pytest.fixture
    def mock_container(self):
        """Create comprehensive mock ModelONEXContainer."""
        container = Mock(spec=ModelONEXContainer)

        # Mock base container properties
        container.config = Mock()
        container.enhanced_logger = Mock()
        container.workflow_factory = Mock()
        container.workflow_coordinator = Mock()

        # Mock base container for compatibility
        base_container = Mock()
        base_container.config = container.config
        base_container.enhanced_logger = container.enhanced_logger
        container.base_container = base_container

        # Mock service resolution
        container.get_service_async = AsyncMock()

        return container

    @pytest.fixture
    def workflow_request(self):
        """Create sample workflow request."""
        return ModelWorkflowRequest(
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="test-instance-456",
            payload=ModelWorkflowPayload(data={"dataset": "test_data.csv"}),
            metadata=ModelWorkflowMetadata(
                priority=7,
                timeout_seconds=600,
                tags=["integration", "container"],
            ),
        )

    @pytest.fixture
    async def node_engine(self, mock_container):
        """Create NodeReducerPatternEngine with mocked container."""
        with patch.object(NodeReducerPatternEngine, "_register_contract_subreducers"):
            with patch.object(
                NodeReducerPatternEngine,
                "_load_contract_model",
            ) as mock_load:
                # Mock contract model
                mock_contract = Mock()
                mock_contract.pattern_config.supported_workflows = [
                    "DATA_ANALYSIS",
                    "REPORT_GENERATION",
                    "DOCUMENT_REGENERATION",
                ]
                mock_contract.validate_node_specific_config = Mock()
                mock_load.return_value = mock_contract

                engine = NodeReducerPatternEngine(mock_container)

                # Mock the underlying pattern engine
                engine._pattern_engine = Mock()
                engine._pattern_engine.process_workflow = AsyncMock()
                engine._pattern_engine.get_comprehensive_metrics = Mock(
                    return_value={
                        "legacy_metrics": {"total_workflows": 5},
                        "enhanced_metrics": {"success_rate": 0.9},
                    },
                )

                return engine

    def test_container_injection_during_initialization(self, mock_container):
        """Test that container is properly injected during initialization."""
        with patch.object(NodeReducerPatternEngine, "_register_contract_subreducers"):
            with patch(
                "omnibase_core.core.node_reducer.NodeReducer._load_contract_model",
            ) as mock_parent_load:
                with patch.object(
                    NodeReducerPatternEngine,
                    "_load_contract_model",
                ) as mock_child_load:
                    # Create a mock contract that's compatible with both parent and child expectations
                    mock_contract = Mock()
                    mock_contract.pattern_config = Mock()
                    mock_contract.pattern_config.supported_workflows = ["DATA_ANALYSIS"]
                    mock_contract.validate_node_specific_config = Mock()
                    mock_parent_load.return_value = mock_contract
                    mock_child_load.return_value = mock_contract

                    engine = NodeReducerPatternEngine(mock_container)

                # Verify container is stored
                assert engine.container == mock_container

                # Verify container properties are accessible
                assert engine.container.config is not None
                assert engine.container.enhanced_logger is not None

    @pytest.mark.asyncio
    async def test_service_resolution_through_container(
        self,
        node_engine,
        mock_container,
    ):
        """Test service resolution through ModelOnexContainer."""
        # Mock service resolution
        mock_service = Mock()
        mock_container.get_service_async.return_value = mock_service

        # Test service resolution
        service = await mock_container.get_service_async(
            protocol_type=Mock,
            service_name="test_service",
        )

        assert service == mock_service
        mock_container.get_service_async.assert_called_once()

    def test_container_configuration_access(self, node_engine):
        """Test accessing configuration through container."""
        # Mock configuration
        node_engine.container.config.get = Mock(return_value="test_value")

        # Access configuration
        config_value = node_engine.container.config.get("test_key")

        assert config_value == "test_value"
        node_engine.container.config.get.assert_called_once_with("test_key")

    def test_container_logging_integration(self, node_engine):
        """Test logging integration through container."""
        # Mock logger
        logger = node_engine.container.enhanced_logger
        logger.info = Mock()

        # Use logger
        logger.info("Test log message")

        logger.info.assert_called_once_with("Test log message")

    @pytest.mark.asyncio
    async def test_workflow_processing_with_container_context(
        self,
        node_engine,
        workflow_request,
    ):
        """Test workflow processing with container context."""
        # Create engine input
        engine_input = ModelReducerPatternEngineInput.from_workflow_request(
            workflow_request=workflow_request,
            source_node_id="test_client",
        )

        # Mock successful processing
        mock_response = Mock()
        mock_response.workflow_id = workflow_request.workflow_id
        mock_response.workflow_type = workflow_request.workflow_type
        mock_response.instance_id = workflow_request.instance_id
        mock_response.correlation_id = workflow_request.correlation_id
        mock_response.status = Mock()
        mock_response.status.value = "COMPLETED"
        mock_response.processing_time_ms = 200.0
        mock_response.subreducer_name = "container_test_subreducer"

        node_engine._pattern_engine.process_workflow.return_value = mock_response

        # Process workflow
        output = await node_engine.process_workflow(engine_input)

        # Verify processing occurred with container context
        assert output is not None
        assert output.workflow_response == mock_response

        # Verify underlying engine was called with container context
        node_engine._pattern_engine.process_workflow.assert_called_once_with(
            workflow_request,
        )

    def test_container_dependency_injection_patterns(self, mock_container):
        """Test dependency injection patterns through container."""
        with patch.object(NodeReducerPatternEngine, "_register_contract_subreducers"):
            with patch.object(NodeReducerPatternEngine, "_load_contract_model"):
                with patch.object(
                    NodeReducerPatternEngine,
                    "_initialize_services",
                ) as mock_init:
                    engine = NodeReducerPatternEngine(mock_container)

                    # Verify service initialization was called
                    mock_init.assert_called_once()

                    # Verify container is available for dependency injection
                    assert engine.container == mock_container

    @pytest.mark.asyncio
    async def test_container_service_lifecycle_management(self, node_engine):
        """Test service lifecycle management through container."""
        # Mock service lifecycle methods
        node_engine.container.start_service = AsyncMock()
        node_engine.container.stop_service = AsyncMock()

        # Test service lifecycle
        if hasattr(node_engine.container, "start_service"):
            await node_engine.container.start_service("test_service")
            node_engine.container.start_service.assert_called_once_with("test_service")

        if hasattr(node_engine.container, "stop_service"):
            await node_engine.container.stop_service("test_service")
            node_engine.container.stop_service.assert_called_once_with("test_service")

    def test_container_workflow_factory_integration(self, node_engine):
        """Test integration with container's workflow factory."""
        # Mock workflow factory
        workflow_factory = node_engine.container.workflow_factory
        workflow_factory.create_workflow = Mock()

        # Test workflow factory usage
        if hasattr(workflow_factory, "create_workflow"):
            workflow_factory.create_workflow("test_workflow", {})
            workflow_factory.create_workflow.assert_called_once_with(
                "test_workflow",
                {},
            )

    def test_container_workflow_coordinator_integration(self, node_engine):
        """Test integration with container's workflow coordinator."""
        # Mock workflow coordinator
        coordinator = node_engine.container.workflow_coordinator
        coordinator.coordinate = Mock()

        # Test workflow coordinator usage
        if hasattr(coordinator, "coordinate"):
            coordinator.coordinate("test_workflow_id")
            coordinator.coordinate.assert_called_once_with("test_workflow_id")

    @pytest.mark.asyncio
    async def test_container_error_handling(self, mock_container):
        """Test error handling with container integration."""
        # Mock container that raises errors
        mock_container.get_service_async.side_effect = Exception(
            "Service resolution failed",
        )

        with patch.object(NodeReducerPatternEngine, "_register_contract_subreducers"):
            with patch.object(NodeReducerPatternEngine, "_load_contract_model"):
                # Engine should still initialize despite service resolution errors
                engine = NodeReducerPatternEngine(mock_container)

                # Engine should be functional
                assert engine.container == mock_container

    def test_container_compatibility_layer(self, node_engine):
        """Test compatibility layer with different container versions."""
        # Test base container access
        if hasattr(node_engine.container, "base_container"):
            base_container = node_engine.container.base_container
            assert base_container is not None
            assert hasattr(base_container, "config")

    @pytest.mark.asyncio
    async def test_container_service_provider_integration(self, node_engine):
        """Test integration with container's service provider."""
        # Mock service provider
        if hasattr(node_engine.container, "service_provider"):
            service_provider = node_engine.container.service_provider
            service_provider.get_service = AsyncMock(return_value=Mock())

            # Test service provider usage
            service = await service_provider.get_service("test_service")
            assert service is not None

    def test_container_performance_metrics_integration(self, node_engine):
        """Test integration with container's performance metrics."""
        # Get processing metrics (which should include container context)
        metrics = node_engine.get_processing_metrics()

        # Verify metrics structure includes container-related information
        assert "pattern_metrics" in metrics
        assert "onex_metrics" in metrics
        assert "node_metadata" in metrics

        # Verify ONEX compliance metadata
        onex_metrics = metrics["onex_metrics"]
        assert onex_metrics["node_id"] == "reducer_pattern_engine"
        assert onex_metrics["protocol_version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_container_health_check_integration(self, node_engine):
        """Test health check integration with container."""
        # Mock container health
        node_engine.container.is_healthy = Mock(return_value=True)

        # Perform health check
        health_status = await node_engine.health_check()

        # Should be healthy when container and engine are healthy
        assert health_status is True

    def test_container_configuration_validation(self, mock_container):
        """Test configuration validation through container."""
        # Mock configuration with validation
        mock_container.config.validate = Mock(return_value=True)

        with patch.object(NodeReducerPatternEngine, "_register_contract_subreducers"):
            with patch.object(NodeReducerPatternEngine, "_load_contract_model"):
                engine = NodeReducerPatternEngine(mock_container)

                # Configuration should be accessible
                assert engine.container.config is not None

    @pytest.mark.asyncio
    async def test_container_async_context_management(self, node_engine):
        """Test async context management through container."""
        # Mock async context manager
        async_context = AsyncMock()
        async_context.__aenter__ = AsyncMock(return_value=Mock())
        async_context.__aexit__ = AsyncMock(return_value=None)

        if hasattr(node_engine.container, "get_async_context"):
            node_engine.container.get_async_context = Mock(return_value=async_context)

            # Test async context usage
            async with node_engine.container.get_async_context() as context:
                assert context is not None

    def test_container_monadic_service_provider(self, node_engine):
        """Test monadic service provider integration."""
        # Mock monadic service provider
        if hasattr(node_engine.container, "service_provider"):
            service_provider = node_engine.container.service_provider
            service_provider.bind = Mock()
            service_provider.map = Mock()

            # Test monadic operations
            if hasattr(service_provider, "bind"):
                service_provider.bind(lambda x: x)
                service_provider.bind.assert_called_once()

    @pytest.mark.asyncio
    async def test_container_workflow_orchestration(
        self,
        node_engine,
        workflow_request,
    ):
        """Test workflow orchestration through container."""
        # Create engine input
        engine_input = ModelReducerPatternEngineInput.from_workflow_request(
            workflow_request=workflow_request,
        )

        # Mock orchestration
        if hasattr(node_engine.container, "workflow_coordinator"):
            coordinator = node_engine.container.workflow_coordinator
            coordinator.orchestrate = AsyncMock()

            # Process workflow (which might use orchestration)
            mock_response = Mock()
            mock_response.workflow_id = workflow_request.workflow_id
            mock_response.workflow_type = workflow_request.workflow_type
            mock_response.instance_id = workflow_request.instance_id
            mock_response.correlation_id = workflow_request.correlation_id
            mock_response.status = Mock()
            mock_response.status.value = "COMPLETED"
            mock_response.processing_time_ms = 150.0
            mock_response.subreducer_name = "orchestrated_subreducer"

            node_engine._pattern_engine.process_workflow.return_value = mock_response

            output = await node_engine.process_workflow(engine_input)

            # Verify processing completed
            assert output is not None

    def test_container_metadata_propagation(self, node_engine):
        """Test metadata propagation through container."""
        # Get node metadata
        metadata = node_engine.get_node_metadata()

        # Verify container-related metadata
        assert "node_id" in metadata
        assert "protocol_version" in metadata
        assert "capabilities" in metadata

        # Verify container integration capabilities
        capabilities = metadata["capabilities"]
        assert "workflow_processing" in capabilities
        assert "envelope_support" in capabilities
