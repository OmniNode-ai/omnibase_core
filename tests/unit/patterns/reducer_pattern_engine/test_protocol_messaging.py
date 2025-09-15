"""Tests for protocol messaging in Reducer Pattern Engine Phase 3."""

import pytest

from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.models import (
    ModelReducerPatternEngineInput,
    ModelReducerPatternEngineOutput,
    ModelWorkflowRequest,
    ModelWorkflowResponse,
    ModelWorkflowResult,
    ModelWorkflowResultData,
    WorkflowType,
)
from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.models.model_workflow_metadata import (
    ModelWorkflowMetadata,
)
from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.models.model_workflow_payload import (
    ModelWorkflowPayload,
)
from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.models.model_workflow_result import (
    ModelWorkflowResult,
)
from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.protocols.protocol_reducer_pattern_engine import (
    BaseReducerPatternEngine,
    ProtocolReducerPatternEngine,
)


class MockReducerPatternEngineImplementation(BaseReducerPatternEngine):
    """Mock implementation of ProtocolReducerPatternEngine for testing."""

    def __init__(self):
        # Use actual enum values, not uppercase strings
        self.supported_workflow_types = [
            WorkflowType.DATA_ANALYSIS.value,
            WorkflowType.REPORT_GENERATION.value,
        ]
        self.is_healthy = True

    async def process_workflow(
        self,
        engine_input: ModelReducerPatternEngineInput,
    ) -> ModelReducerPatternEngineOutput:
        """Mock workflow processing."""
        # Handle both enum and string values for workflow_type
        workflow_type_value = (
            engine_input.workflow_request.workflow_type.value
            if hasattr(engine_input.workflow_request.workflow_type, "value")
            else engine_input.workflow_request.workflow_type
        )
        if workflow_type_value not in self.supported_workflow_types:
            return self.create_error_output(
                engine_input=engine_input,
                error_message="Unsupported workflow type",
                error_details={"workflow_type": workflow_type_value},
            )

        # Create successful response
        workflow_response = ModelWorkflowResponse(
            workflow_id=engine_input.workflow_request.workflow_id,
            workflow_type=engine_input.workflow_request.workflow_type,
            instance_id=engine_input.workflow_request.instance_id,
            correlation_id=engine_input.workflow_request.correlation_id,
            status="completed",
            result=ModelWorkflowResult(
                success=True,
                data=ModelWorkflowResultData(validation_passed=True),
            ),
            processing_time_ms=100.0,
            subreducer_name="mock_subreducer",
        )

        return ModelReducerPatternEngineOutput.from_workflow_response(
            workflow_response=workflow_response,
            source_node_id="mock_engine",
        )

    async def health_check(self) -> bool:
        """Mock health check."""
        return self.is_healthy

    def get_supported_workflow_types(self) -> list[str]:
        """Mock supported workflow types."""
        return self.supported_workflow_types


class TestProtocolMessaging:
    """Test protocol messaging for Reducer Pattern Engine Phase 3."""

    @pytest.fixture
    def mock_engine(self):
        """Create mock engine implementation."""
        return MockReducerPatternEngineImplementation()

    @pytest.fixture
    def workflow_request(self):
        """Create sample workflow request."""
        return ModelWorkflowRequest(
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="test-instance-123",
            payload=ModelWorkflowPayload(data={"analysis_type": "descriptive"}),
            metadata=ModelWorkflowMetadata(
                priority=5,
                timeout_seconds=300,
                tags=["test", "analysis"],
            ),
        )

    @pytest.fixture
    def engine_input(self, workflow_request):
        """Create engine input."""
        return ModelReducerPatternEngineInput.from_workflow_request(
            workflow_request=workflow_request,
            protocol_version="1.0.0",
            source_node_id="test_client",
        )

    @pytest.mark.asyncio
    async def test_protocol_compliance_interface(self, mock_engine):
        """Test that mock engine implements protocol interface."""
        assert isinstance(mock_engine, ProtocolReducerPatternEngine)

        # Test protocol methods exist
        assert hasattr(mock_engine, "process_workflow")
        assert hasattr(mock_engine, "health_check")
        assert hasattr(mock_engine, "get_supported_workflow_types")

    @pytest.mark.asyncio
    async def test_successful_workflow_processing(self, mock_engine, engine_input):
        """Test successful workflow processing through protocol."""
        output = await mock_engine.process_workflow(engine_input)

        # Verify protocol-compliant output
        assert isinstance(output, ModelReducerPatternEngineOutput)
        assert output.is_success()
        assert output.workflow_response.status == "completed"
        assert output.workflow_response.result.success is True

    @pytest.mark.asyncio
    async def test_error_workflow_processing(self, mock_engine):
        """Test error workflow processing through protocol."""
        # Create input with unsupported workflow type
        unsupported_request = ModelWorkflowRequest(
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,  # Not supported by mock
            instance_id="error-test-123",
            payload=ModelWorkflowPayload(data={"doc_type": "report"}),
            metadata=ModelWorkflowMetadata(priority=1, timeout_seconds=60),
        )

        unsupported_input = ModelReducerPatternEngineInput.from_workflow_request(
            workflow_request=unsupported_request,
            protocol_version="1.0.0",
            source_node_id="test_client",
        )

        output = await mock_engine.process_workflow(unsupported_input)

        # Verify error output
        assert isinstance(output, ModelReducerPatternEngineOutput)
        assert not output.is_success()
        assert output.workflow_response.status == "failed"
        assert output.workflow_response.error is not None

    def test_health_check_protocol(self, mock_engine):
        """Test health check protocol method."""
        health = mock_engine.health_check()

        # Health check should be a coroutine, not a bool
        import asyncio

        if asyncio.iscoroutine(health):
            # For async health check
            health_result = asyncio.run(health)
            assert health_result is True
        else:
            # For sync health check (shouldn't happen but handle gracefully)
            assert health is True

        # Test unhealthy state
        mock_engine.is_healthy = False
        health = mock_engine.health_check()
        if asyncio.iscoroutine(health):
            health_result = asyncio.run(health)
            assert health_result is False
        else:
            assert health is False

    def test_supported_workflow_types_protocol(self, mock_engine):
        """Test supported workflow types protocol method."""
        supported_types = mock_engine.get_supported_workflow_types()

        assert isinstance(supported_types, list)
        assert len(supported_types) == 2
        assert WorkflowType.DATA_ANALYSIS.value in supported_types
        assert WorkflowType.REPORT_GENERATION.value in supported_types

    @pytest.mark.asyncio
    async def test_input_validation_protocol(self, mock_engine, engine_input):
        """Test input validation in protocol implementation."""
        # Valid input should pass
        await mock_engine.validate_input(engine_input)  # Should not raise

        # Invalid input type should fail
        with pytest.raises(
            ValueError,
            match="Input must be ModelReducerPatternEngineInput",
        ):
            await mock_engine.validate_input("invalid_input")

        # Missing workflow request should fail
        invalid_input = ModelReducerPatternEngineInput(
            workflow_request=None,
            protocol_version="1.0.0",
        )

        with pytest.raises(ValueError, match="Workflow request is required"):
            await mock_engine.validate_input(invalid_input)

    @pytest.mark.asyncio
    async def test_error_output_creation(self, mock_engine, engine_input):
        """Test error output creation in protocol."""
        error_output = mock_engine.create_error_output(
            engine_input=engine_input,
            error_message="Test error",
            error_details={"detail": "test_detail"},
        )

        assert isinstance(error_output, ModelReducerPatternEngineOutput)
        assert not error_output.is_success()
        assert error_output.workflow_response.status == "failed"
        assert error_output.workflow_response.error.error_message == "Test error"

    @pytest.mark.asyncio
    async def test_message_structure_validation(self, mock_engine, engine_input):
        """Test message structure validation in protocol."""
        output = await mock_engine.process_workflow(engine_input)

        # Verify message structure
        assert hasattr(output, "workflow_response")
        assert hasattr(output, "protocol_version")
        assert hasattr(output.workflow_response, "workflow_id")
        assert hasattr(output.workflow_response, "workflow_type")
        assert hasattr(output.workflow_response, "instance_id")
        assert hasattr(output.workflow_response, "correlation_id")
        assert hasattr(output.workflow_response, "status")

    @pytest.mark.asyncio
    async def test_protocol_metadata_handling(self, mock_engine, engine_input):
        """Test protocol metadata handling."""
        output = await mock_engine.process_workflow(engine_input)

        # Verify metadata preservation
        assert (
            output.workflow_response.workflow_id
            == engine_input.workflow_request.workflow_id
        )
        assert (
            output.workflow_response.workflow_type
            == engine_input.workflow_request.workflow_type
        )
        assert (
            output.workflow_response.instance_id
            == engine_input.workflow_request.instance_id
        )

    @pytest.mark.asyncio
    async def test_correlation_id_propagation(self, mock_engine, engine_input):
        """Test correlation ID propagation through protocol."""
        output = await mock_engine.process_workflow(engine_input)

        # Verify correlation ID propagation
        assert (
            output.workflow_response.correlation_id
            == engine_input.workflow_request.correlation_id
        )

    @pytest.mark.asyncio
    async def test_node_id_routing(self, mock_engine, engine_input):
        """Test node ID routing in protocol messaging."""
        output = await mock_engine.process_workflow(engine_input)

        # Verify node routing information
        assert hasattr(output, "get_source_node_id")
        # Source should be the processing engine
        source_node = output.get_source_node_id()
        assert source_node == "mock_engine"

    @pytest.mark.asyncio
    async def test_protocol_version_compatibility(self, mock_engine, workflow_request):
        """Test protocol version compatibility checking."""
        # Test with different protocol versions
        engine_input_v1 = ModelReducerPatternEngineInput.from_workflow_request(
            workflow_request=workflow_request,
            protocol_version="1.0.0",
            source_node_id="test_client",
        )

        output = await mock_engine.process_workflow(engine_input_v1)
        assert output.protocol_version == "1.0.0"

        # Test compatibility with different versions
        engine_input_future = ModelReducerPatternEngineInput.from_workflow_request(
            workflow_request=workflow_request,
            protocol_version="2.0.0",
            source_node_id="test_client",
        )

        # Should work with proper protocol interface
        output = await mock_engine.process_workflow(engine_input_future)
        assert isinstance(output, ModelReducerPatternEngineOutput)

    @pytest.mark.asyncio
    async def test_onex_compliance_metadata(self, mock_engine, engine_input):
        """Test ONEX compliance metadata in protocol responses."""
        output = await mock_engine.process_workflow(engine_input)

        # Verify ONEX compliance metadata
        assert hasattr(output, "workflow_response")
        assert hasattr(output.workflow_response, "processing_time_ms")
        assert output.workflow_response.processing_time_ms >= 0.0

        # Verify proper envelope structure when available
        assert hasattr(output, "envelope")
        # For successful processing, envelope may be None (that's OK)
