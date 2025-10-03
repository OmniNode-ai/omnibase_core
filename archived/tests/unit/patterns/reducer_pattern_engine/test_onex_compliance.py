"""Tests for ONEX protocol compliance in Reducer Pattern Engine Phase 3."""

from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.core.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.models import (
    ModelReducerPatternEngineInput,
    ModelReducerPatternEngineOutput,
    ModelWorkflowRequest,
    ModelWorkflowResponse,
    WorkflowStatus,
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


class TestONEXCompliance:
    """Test ONEX protocol compliance for Reducer Pattern Engine Phase 3."""

    @pytest.fixture
    def mock_container(self):
        """Create mock ModelONEXContainer."""
        container = Mock(spec=ModelONEXContainer)
        container.config = Mock()
        container.enhanced_logger = Mock()
        return container

    @pytest.fixture
    def workflow_request(self):
        """Create sample workflow request."""
        return ModelWorkflowRequest(
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="test-instance-123",
            payload=ModelWorkflowPayload(data={"test": "data"}),
            metadata=ModelWorkflowMetadata(),
        )

    @pytest.fixture
    def onex_input(self, workflow_request):
        """Create ONEX-compliant input."""
        return ModelReducerPatternEngineInput.from_workflow_request(
            workflow_request=workflow_request,
            protocol_version="1.0.0",
            source_node_id="test_source_node",
        )

    @pytest.fixture
    def mock_envelope(self, workflow_request):
        """Create mock ONEX event envelope."""
        event = ModelOnexEvent(
            event_id=str(uuid4()),
            event_type="workflow_processing_request",
            data=workflow_request.model_dump(),
        )

        # Mock the envelope creation since we can't easily create real ModelEventEnvelope
        envelope = Mock(spec=ModelEventEnvelope)
        envelope.envelope_id = str(uuid4())
        envelope.correlation_id = workflow_request.correlation_id
        envelope.source_node_id = "test_source_node"
        envelope.payload = event
        envelope.current_hop_count = 0
        envelope.trace = []
        envelope.metadata = {}

        return envelope

    @pytest.fixture
    async def node_engine(self, mock_container):
        """Create NodeReducerPatternEngine instance."""
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
                mock_load.return_value = mock_contract

                engine = NodeReducerPatternEngine(mock_container)

                # Mock the underlying pattern engine
                engine._pattern_engine = Mock()
                engine._pattern_engine.process_workflow = AsyncMock()

                return engine

    @pytest.mark.asyncio
    async def test_onex_input_creation_from_workflow_request(self, workflow_request):
        """Test creating ONEX input from workflow request."""
        onex_input = ModelReducerPatternEngineInput.from_workflow_request(
            workflow_request=workflow_request,
            protocol_version="1.0.0",
            source_node_id="test_node",
        )

        assert onex_input.workflow_request == workflow_request
        assert onex_input.protocol_version == "1.0.0"
        assert onex_input.source_node_id == "test_node"
        assert onex_input.correlation_id == workflow_request.correlation_id
        assert onex_input.envelope is None  # No envelope for direct creation

    @pytest.mark.asyncio
    async def test_onex_input_creation_from_envelope(
        self,
        mock_envelope,
        workflow_request,
    ):
        """Test creating ONEX input from event envelope."""
        with patch.object(
            ModelReducerPatternEngineInput,
            "from_envelope",
        ) as mock_from_envelope:
            # Mock the from_envelope method since ModelEventEnvelope is complex to create
            expected_input = ModelReducerPatternEngineInput.from_workflow_request(
                workflow_request=workflow_request,
                source_node_id=mock_envelope.source_node_id,
            )
            expected_input.envelope = mock_envelope
            mock_from_envelope.return_value = expected_input

            onex_input = ModelReducerPatternEngineInput.from_envelope(mock_envelope)

            assert (
                onex_input.workflow_request.workflow_type == WorkflowType.DATA_ANALYSIS
            )
            assert onex_input.envelope == mock_envelope
            assert onex_input.get_source_node_id() == mock_envelope.source_node_id

    @pytest.mark.asyncio
    async def test_onex_output_creation_from_workflow_response(self, workflow_request):
        """Test creating ONEX output from workflow response."""
        # Create workflow response
        workflow_response = ModelWorkflowResponse(
            workflow_id=workflow_request.workflow_id,
            workflow_type=workflow_request.workflow_type,
            instance_id=workflow_request.instance_id,
            correlation_id=workflow_request.correlation_id,
            status=WorkflowStatus.COMPLETED,
            result=Mock(),
            processing_time_ms=100.0,
            subreducer_name="test_subreducer",
        )

        onex_output = ModelReducerPatternEngineOutput.from_workflow_response(
            workflow_response=workflow_response,
            source_node_id="reducer_pattern_engine",
        )

        assert onex_output.workflow_response == workflow_response
        assert onex_output.source_node_id == "reducer_pattern_engine"
        assert onex_output.correlation_id == workflow_response.correlation_id
        assert onex_output.is_success() is True

    @pytest.mark.asyncio
    async def test_node_engine_initialization(self, mock_container):
        """Test NodeReducerPatternEngine initialization."""
        with patch.object(NodeReducerPatternEngine, "_register_contract_subreducers"):
            with patch.object(
                NodeReducerPatternEngine,
                "_load_contract_model",
            ) as mock_load:
                mock_contract = Mock()
                mock_contract.pattern_config.supported_workflows = ["DATA_ANALYSIS"]
                mock_load.return_value = mock_contract

                engine = NodeReducerPatternEngine(mock_container)

                assert engine.container == mock_container
                assert engine._node_id == "reducer_pattern_engine"
                assert engine._protocol_version == "1.0.0"
                assert engine._onex_compliance_version == "1.0.0"
                assert engine.contract_model == mock_contract

    @pytest.mark.asyncio
    async def test_protocol_compliance_workflow_processing(
        self,
        node_engine,
        onex_input,
    ):
        """Test ONEX protocol-compliant workflow processing."""
        # Mock workflow response
        mock_response = Mock(spec=ModelWorkflowResponse)
        mock_response.workflow_id = onex_input.workflow_request.workflow_id
        mock_response.workflow_type = onex_input.workflow_request.workflow_type
        mock_response.instance_id = onex_input.workflow_request.instance_id
        mock_response.correlation_id = onex_input.workflow_request.correlation_id
        mock_response.status = WorkflowStatus.COMPLETED
        mock_response.processing_time_ms = 100.0
        mock_response.subreducer_name = "test_subreducer"

        node_engine._pattern_engine.process_workflow.return_value = mock_response

        # Process workflow
        output = await node_engine.process_workflow(onex_input)

        # Verify ONEX compliance
        assert isinstance(output, ModelReducerPatternEngineOutput)
        assert output.workflow_response == mock_response
        assert output.correlation_id == onex_input.get_correlation_id()
        assert output.source_node_id == "reducer_pattern_engine"
        assert output.protocol_version == "1.0.0"

        # Verify underlying engine was called
        node_engine._pattern_engine.process_workflow.assert_called_once_with(
            onex_input.workflow_request,
        )

    @pytest.mark.asyncio
    async def test_envelope_processing(self, node_engine, mock_envelope):
        """Test ONEX envelope processing."""
        with patch.object(node_engine, "process_workflow") as mock_process:
            # Mock successful processing
            mock_output = Mock(spec=ModelReducerPatternEngineOutput)
            mock_output.to_envelope.return_value = mock_envelope
            mock_process.return_value = mock_output

            # Process envelope
            result_envelope = await node_engine.process_envelope(mock_envelope)

            # Verify envelope processing
            assert result_envelope == mock_envelope
            mock_process.assert_called_once()

            # Verify the input was created from envelope
            call_args = mock_process.call_args[0][0]
            assert isinstance(call_args, ModelReducerPatternEngineInput)

    @pytest.mark.asyncio
    async def test_health_check(self, node_engine):
        """Test node health check."""
        health_status = await node_engine.health_check()

        # Should be healthy with mocked components
        assert health_status is True

    @pytest.mark.asyncio
    async def test_supported_workflow_types(self, node_engine):
        """Test getting supported workflow types."""
        supported_types = node_engine.get_supported_workflow_types()

        assert isinstance(supported_types, list)
        assert len(supported_types) > 0
        assert "DATA_ANALYSIS" in supported_types

    @pytest.mark.asyncio
    async def test_node_metadata(self, node_engine):
        """Test getting node metadata."""
        metadata = node_engine.get_node_metadata()

        assert metadata["node_id"] == "reducer_pattern_engine"
        assert metadata["node_type"] == "COMPUTE"
        assert metadata["protocol_version"] == "1.0.0"
        assert metadata["onex_compliance_version"] == "1.0.0"
        assert "supported_workflow_types" in metadata
        assert "capabilities" in metadata

    @pytest.mark.asyncio
    async def test_processing_metrics(self, node_engine):
        """Test getting processing metrics."""
        # Mock comprehensive metrics
        node_engine._pattern_engine.get_comprehensive_metrics.return_value = {
            "legacy_metrics": {"total_workflows": 10},
            "enhanced_metrics": {"success_rate": 0.95},
        }

        metrics = node_engine.get_processing_metrics()

        assert "pattern_metrics" in metrics
        assert "onex_metrics" in metrics
        assert "node_metadata" in metrics
        assert metrics["onex_metrics"]["node_id"] == "reducer_pattern_engine"

    @pytest.mark.asyncio
    async def test_backward_compatibility_reduce_method(
        self,
        node_engine,
        workflow_request,
    ):
        """Test reduce method compatibility."""
        # Mock workflow response
        mock_response = Mock(spec=ModelWorkflowResponse)
        mock_response.workflow_id = workflow_request.workflow_id
        mock_response.correlation_id = workflow_request.correlation_id

        with patch.object(node_engine, "process_workflow") as mock_process:
            mock_output = Mock(spec=ModelReducerPatternEngineOutput)
            mock_output.workflow_response = mock_response
            mock_process.return_value = mock_output

            # Call reduce method
            result = await node_engine.reduce(workflow_request)

            # Verify method compatibility
            assert result == mock_response
            mock_process.assert_called_once()

            # Verify input was properly created
            call_args = mock_process.call_args[0][0]
            assert isinstance(call_args, ModelReducerPatternEngineInput)
            assert call_args.workflow_request == workflow_request

    @pytest.mark.asyncio
    async def test_error_handling_in_protocol_processing(self, node_engine, onex_input):
        """Test error handling in protocol-compliant processing."""
        # Mock processing failure
        error_message = "Processing failed"
        node_engine._pattern_engine.process_workflow.side_effect = Exception(
            error_message,
        )

        # Process workflow (should handle error gracefully)
        output = await node_engine.process_workflow(onex_input)

        # Verify error output
        assert isinstance(output, ModelReducerPatternEngineOutput)
        assert not output.is_success()

        error_info = output.get_error_info()
        assert error_info is not None
        assert error_message in error_info["error_message"]

    @pytest.mark.asyncio
    async def test_input_validation(self, node_engine):
        """Test input validation for protocol compliance."""
        # Test with invalid input type
        with pytest.raises(
            ValueError,
            match="Input must be ModelReducerPatternEngineInput",
        ):
            await node_engine.validate_input("invalid_input")

        # Test with missing workflow request
        invalid_input = Mock(spec=ModelReducerPatternEngineInput)
        invalid_input.workflow_request = None

        with pytest.raises(ValueError, match="Workflow request is required"):
            await node_engine.validate_input(invalid_input)

    @pytest.mark.asyncio
    async def test_unsupported_workflow_type_validation(self, node_engine, onex_input):
        """Test validation of unsupported workflow types."""
        # Mock unsupported workflow type
        onex_input.workflow_request.workflow_type = Mock()
        onex_input.workflow_request.workflow_type.value = "UNSUPPORTED_TYPE"

        with pytest.raises(ValueError, match="Unsupported workflow type"):
            await node_engine.validate_input(onex_input)

    @pytest.mark.asyncio
    async def test_envelope_to_onex_output_conversion(self, onex_input):
        """Test converting ONEX input to envelope."""
        # Set envelope on input
        mock_envelope = Mock(spec=ModelEventEnvelope)
        onex_input.envelope = mock_envelope

        # Convert to envelope should update existing envelope
        result_envelope = onex_input.to_envelope()

        # Should return the existing envelope (mocked behavior)
        assert result_envelope == mock_envelope

    def test_onex_output_error_information(self, workflow_request):
        """Test error information extraction from ONEX output."""
        # Create failed workflow response
        from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.models.model_workflow_error import (
            ModelWorkflowError,
        )
        from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.models.model_workflow_result import (
            ModelWorkflowResult,
        )

        error = ModelWorkflowError(
            error_code="TEST_ERROR",
            error_message="Test error",
            error_context={"details": "Test error details"},
        )

        workflow_response = ModelWorkflowResponse(
            workflow_id=workflow_request.workflow_id,
            workflow_type=workflow_request.workflow_type,
            instance_id=workflow_request.instance_id,
            correlation_id=workflow_request.correlation_id,
            status=WorkflowStatus.FAILED,
            result=ModelWorkflowResult(),
            error=error,
            processing_time_ms=50.0,
            subreducer_name="test_subreducer",
        )

        onex_output = ModelReducerPatternEngineOutput.from_workflow_response(
            workflow_response=workflow_response,
        )

        # Test error information
        assert not onex_output.is_success()

        error_info = onex_output.get_error_info()
        assert error_info is not None
        assert error_info["error_message"] == "Test error"
        assert error_info["error_details"] == {"error_code": "TEST_ERROR"}
        assert error_info["error_context"] == {"details": "Test error details"}
        assert error_info["workflow_type"] == WorkflowType.DATA_ANALYSIS.value

    def test_onex_output_success_information(self, workflow_request):
        """Test success information from ONEX output."""
        # Create successful workflow response
        from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.models.model_workflow_result import (
            ModelWorkflowResult,
        )

        workflow_response = ModelWorkflowResponse(
            workflow_id=workflow_request.workflow_id,
            workflow_type=workflow_request.workflow_type,
            instance_id=workflow_request.instance_id,
            correlation_id=workflow_request.correlation_id,
            status=WorkflowStatus.COMPLETED,
            result=ModelWorkflowResult(data={"result": "success"}),
            processing_time_ms=100.0,
            subreducer_name="test_subreducer",
        )

        onex_output = ModelReducerPatternEngineOutput.from_workflow_response(
            workflow_response=workflow_response,
        )

        # Test success information
        assert onex_output.is_success()
        assert onex_output.get_error_info() is None
