"""
Unit tests for ReducerDocumentRegenerationSubreducer.

Tests the reference implementation of document regeneration subreducer
including workflow processing, parameter validation, error handling,
metrics collection, and ONEX standards compliance.
"""

import asyncio
import time
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration import (
    ReducerDocumentRegenerationSubreducer,
)
from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.models import (
    ModelSubreducerResult,
    ModelWorkflowRequest,
    WorkflowType,
)


@pytest.fixture
def subreducer():
    """Create a ReducerDocumentRegenerationSubreducer instance for testing."""
    with patch(
        "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
    ):
        return ReducerDocumentRegenerationSubreducer()


@pytest.fixture
def valid_workflow_request():
    """Create a valid workflow request for document regeneration."""
    return ModelWorkflowRequest(
        workflow_id=uuid4(),
        workflow_type=WorkflowType.DOCUMENT_REGENERATION,
        instance_id="test_instance_1",
        correlation_id=uuid4(),
        payload={
            "document_id": "doc_123",
            "content_type": "markdown",
            "template_id": "template_456",
            "regeneration_options": {"include_toc": True, "format": "structured"},
            "metadata": {"author": "test_user", "version": "2.1.0"},
        },
        metadata={"test": "metadata"},
    )


@pytest.fixture
def minimal_workflow_request():
    """Create a minimal valid workflow request."""
    return ModelWorkflowRequest(
        workflow_id=uuid4(),
        workflow_type=WorkflowType.DOCUMENT_REGENERATION,
        instance_id="minimal_instance",
        correlation_id=uuid4(),
        payload={"document_id": "doc_minimal", "content_type": "text"},
    )


class TestReducerDocumentRegenerationSubreducerInitialization:
    """Test subreducer initialization."""

    def test_subreducer_initialization(self):
        """Test that subreducer initializes correctly."""
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
        ) as mock_log:
            subreducer = ReducerDocumentRegenerationSubreducer()

            assert subreducer is not None
            assert subreducer.name == "reducer_document_regeneration"
            assert subreducer._processing_metrics is not None
            assert subreducer._processing_metrics["total_processed"] == 0
            assert subreducer._processing_metrics["successful_processes"] == 0
            assert subreducer._processing_metrics["failed_processes"] == 0
            assert subreducer._processing_metrics["average_processing_time_ms"] == 0.0

            # Verify initialization logging
            mock_log.assert_called()
            log_calls = [
                call
                for call in mock_log.call_args_list
                if "subreducer_initialized" in str(call)
            ]
            assert len(log_calls) > 0

    def test_subreducer_inherits_from_base(self, subreducer):
        """Test that subreducer properly inherits from BaseSubreducer."""
        from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.models import (
            BaseSubreducer,
        )

        assert isinstance(subreducer, BaseSubreducer)
        assert hasattr(subreducer, "supports_workflow_type")
        assert hasattr(subreducer, "process")
        assert subreducer.name == "reducer_document_regeneration"


class TestWorkflowTypeSupport:
    """Test workflow type support functionality."""

    def test_supports_document_regeneration_workflow(self, subreducer):
        """Test that subreducer supports DOCUMENT_REGENERATION workflow type."""
        assert (
            subreducer.supports_workflow_type(WorkflowType.DOCUMENT_REGENERATION)
            is True
        )

    def test_does_not_support_other_workflow_types(self, subreducer):
        """Test that subreducer only supports DOCUMENT_REGENERATION."""
        # Note: If more workflow types are added in the future, update this test
        # Currently only DOCUMENT_REGENERATION is defined
        assert (
            subreducer.supports_workflow_type(WorkflowType.DOCUMENT_REGENERATION)
            is True
        )

        # Test with mock workflow type (for future-proofing)
        from enum import Enum

        class MockWorkflowType(Enum):
            OTHER_TYPE = "other_type"

        # This should return False for any non-DOCUMENT_REGENERATION type
        # We'll test by creating a mock workflow type
        mock_type = MockWorkflowType.OTHER_TYPE
        result = subreducer.supports_workflow_type(mock_type)
        assert result is False


class TestSuccessfulWorkflowProcessing:
    """Test successful workflow processing scenarios."""

    @pytest.mark.asyncio
    async def test_successful_document_regeneration(
        self, subreducer, valid_workflow_request
    ):
        """Test successful document regeneration processing."""
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
        ) as mock_log:
            # Process the workflow
            result = await subreducer.process(valid_workflow_request)

        # Verify result structure
        assert isinstance(result, ModelSubreducerResult)
        assert result.workflow_id == valid_workflow_request.workflow_id
        assert result.subreducer_name == "reducer_document_regeneration"
        assert result.success is True
        assert result.error_message is None
        assert result.error_details is None
        assert result.processing_time_ms > 0

        # Verify result content
        assert result.result is not None
        assert "document_id" in result.result
        assert "regenerated_content" in result.result
        assert "processing_info" in result.result
        assert "metadata" in result.result

        # Verify regenerated content structure
        content = result.result["regenerated_content"]
        assert content["content_type"] == "markdown"
        assert content["template_id"] == "template_456"
        assert "generated_at" in content
        assert "content_length" in content
        assert "version" in content

        # Verify processing info
        proc_info = result.result["processing_info"]
        assert proc_info["instance_id"] == valid_workflow_request.instance_id
        assert proc_info["workflow_id"] == str(valid_workflow_request.workflow_id)
        assert proc_info["correlation_id"] == str(valid_workflow_request.correlation_id)
        assert proc_info["subreducer"] == "reducer_document_regeneration"

        # Verify metadata preservation and enhancement
        metadata = result.result["metadata"]
        assert metadata["author"] == "test_user"
        assert metadata["version"] == "2.1.0"
        assert metadata["processed_by"] == "ReducerDocumentRegenerationSubreducer"
        assert metadata["phase"] == "1"

        # Verify logging occurred
        log_calls = mock_log.call_args_list
        start_calls = [
            call for call in log_calls if "document_regeneration_started" in str(call)
        ]
        complete_calls = [
            call for call in log_calls if "document_regeneration_completed" in str(call)
        ]
        param_calls = [
            call for call in log_calls if "document_params_extracted" in str(call)
        ]
        processing_calls = [
            call
            for call in log_calls
            if "document_regeneration_processing" in str(call)
        ]

        assert len(start_calls) > 0
        assert len(complete_calls) > 0
        assert len(param_calls) > 0
        assert len(processing_calls) > 0

    @pytest.mark.asyncio
    async def test_successful_minimal_request(
        self, subreducer, minimal_workflow_request
    ):
        """Test successful processing with minimal required parameters."""
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
        ):
            result = await subreducer.process(minimal_workflow_request)

        # Verify success
        assert result.success is True
        assert result.result is not None

        # Verify defaults are applied
        content = result.result["regenerated_content"]
        assert content["content_type"] == "text"
        assert content["template_id"] == "default"  # Default template applied

        # Verify empty metadata handling
        metadata = result.result["metadata"]
        assert "processed_by" in metadata
        assert "phase" in metadata

    @pytest.mark.asyncio
    async def test_processing_time_measurement(
        self, subreducer, valid_workflow_request
    ):
        """Test that processing time is accurately measured."""
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
        ):
            start_time = time.perf_counter()
            result = await subreducer.process(valid_workflow_request)
            end_time = time.perf_counter()

        # Verify processing time is reasonable
        actual_time_ms = (end_time - start_time) * 1000
        measured_time_ms = result.processing_time_ms

        # Processing time should be positive and roughly match actual time
        assert measured_time_ms > 0
        assert measured_time_ms <= actual_time_ms + 50  # Allow some overhead
        # Should include the simulated 100ms sleep
        assert measured_time_ms >= 90  # At least close to the 100ms sleep


class TestFailedWorkflowProcessing:
    """Test failed workflow processing scenarios."""

    @pytest.mark.asyncio
    async def test_unsupported_workflow_type(self, subreducer):
        """Test handling of unsupported workflow type."""
        # Create request with mock workflow type
        from enum import Enum

        class MockWorkflowType(Enum):
            UNSUPPORTED_TYPE = "unsupported_type"

        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=MockWorkflowType.UNSUPPORTED_TYPE,
            instance_id="test_instance",
            payload={"document_id": "doc_123", "content_type": "markdown"},
        )

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
        ) as mock_log:
            result = await subreducer.process(request)

        # Verify failure result
        assert result.success is False
        assert "Unsupported workflow type" in result.error_message
        assert result.error_details is not None
        assert result.error_details["error_type"] == "OnexError"
        assert result.processing_time_ms > 0

        # Verify error logging
        error_calls = [
            call
            for call in mock_log.call_args_list
            if "document_regeneration_failed" in str(call)
        ]
        assert len(error_calls) > 0

    @pytest.mark.asyncio
    async def test_missing_required_parameters(self, subreducer):
        """Test handling of missing required parameters."""
        # Create request missing document_id
        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,
            instance_id="test_instance",
            payload={
                "content_type": "markdown"
                # Missing document_id
            },
        )

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
        ) as mock_log:
            result = await subreducer.process(request)

        # Verify failure result
        assert result.success is False
        assert "Missing required parameters" in result.error_message
        assert "document_id" in result.error_message
        assert result.error_details["error_type"] == "OnexError"

        # Verify error logging
        error_calls = [
            call
            for call in mock_log.call_args_list
            if "document_regeneration_failed" in str(call)
        ]
        assert len(error_calls) > 0

    @pytest.mark.asyncio
    async def test_missing_multiple_required_parameters(self, subreducer):
        """Test handling of multiple missing required parameters."""
        # Create request missing both required parameters
        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,
            instance_id="test_instance",
            payload={},  # Missing both document_id and content_type
        )

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
        ):
            result = await subreducer.process(request)

        # Verify failure result
        assert result.success is False
        assert "Missing required parameters" in result.error_message
        assert "document_id" in result.error_message
        assert "content_type" in result.error_message

    @pytest.mark.asyncio
    async def test_exception_during_processing(
        self, subreducer, valid_workflow_request
    ):
        """Test handling of unexpected exceptions during processing."""
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
        ) as mock_log:
            # Mock the document regeneration processing to raise an exception
            with patch.object(
                subreducer,
                "_process_document_regeneration",
                side_effect=RuntimeError("Simulated processing error"),
            ):
                result = await subreducer.process(valid_workflow_request)

        # Verify failure result
        assert result.success is False
        assert "Simulated processing error" in result.error_message
        assert result.error_details["error_type"] == "RuntimeError"
        assert result.processing_time_ms > 0

        # Verify error logging
        error_calls = [
            call
            for call in mock_log.call_args_list
            if "document_regeneration_failed" in str(call)
        ]
        assert len(error_calls) > 0


class TestParameterExtraction:
    """Test parameter extraction and validation."""

    def test_extract_valid_parameters(self, subreducer, valid_workflow_request):
        """Test extraction of valid parameters."""
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
        ):
            params = subreducer._extract_document_params(valid_workflow_request)

        # Verify required parameters
        assert params["document_id"] == "doc_123"
        assert params["content_type"] == "markdown"

        # Verify optional parameters with provided values
        assert params["template_id"] == "template_456"
        assert params["regeneration_options"]["include_toc"] is True
        assert params["regeneration_options"]["format"] == "structured"

        # Verify metadata is preserved
        assert params["metadata"]["author"] == "test_user"
        assert params["metadata"]["version"] == "2.1.0"

    def test_extract_minimal_parameters(self, subreducer, minimal_workflow_request):
        """Test extraction with minimal parameters and defaults."""
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
        ):
            params = subreducer._extract_document_params(minimal_workflow_request)

        # Verify required parameters
        assert params["document_id"] == "doc_minimal"
        assert params["content_type"] == "text"

        # Verify defaults are applied
        assert params["template_id"] == "default"
        assert params["regeneration_options"] == {}
        assert params["metadata"] == {}

    def test_extract_parameters_missing_required(self, subreducer):
        """Test parameter extraction with missing required parameters."""
        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,
            instance_id="test_instance",
            payload={"content_type": "markdown"},  # Missing document_id
        )

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
        ):
            with pytest.raises(OnexError) as exc_info:
                subreducer._extract_document_params(request)

            assert exc_info.value.error_code == CoreErrorCode.VALIDATION_ERROR
            assert "Missing required parameters" in str(exc_info.value)
            assert "document_id" in str(exc_info.value)


class TestMetrics:
    """Test metrics collection functionality."""

    @pytest.mark.asyncio
    async def test_success_metrics_update(self, subreducer, valid_workflow_request):
        """Test that success metrics are properly updated."""
        # Get initial metrics
        initial_metrics = subreducer.get_metrics()
        assert initial_metrics["total_processed"] == 0
        assert initial_metrics["successful_processes"] == 0
        assert initial_metrics["success_rate_percent"] == 0.0

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
        ):
            # Process successful workflow
            result = await subreducer.process(valid_workflow_request)

        assert result.success is True

        # Check updated metrics
        updated_metrics = subreducer.get_metrics()
        assert updated_metrics["total_processed"] == 1
        assert updated_metrics["successful_processes"] == 1
        assert updated_metrics["failed_processes"] == 0
        assert updated_metrics["success_rate_percent"] == 100.0
        assert updated_metrics["average_processing_time_ms"] > 0

    @pytest.mark.asyncio
    async def test_failure_metrics_update(self, subreducer):
        """Test that failure metrics are properly updated."""
        # Create invalid request
        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,
            instance_id="test_instance",
            payload={},  # Missing required parameters
        )

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
        ):
            result = await subreducer.process(request)

        assert result.success is False

        # Check updated metrics
        metrics = subreducer.get_metrics()
        assert metrics["total_processed"] == 1
        assert metrics["successful_processes"] == 0
        assert metrics["failed_processes"] == 1
        assert metrics["success_rate_percent"] == 0.0
        assert metrics["average_processing_time_ms"] > 0

    @pytest.mark.asyncio
    async def test_mixed_success_failure_metrics(
        self, subreducer, valid_workflow_request
    ):
        """Test metrics with both successful and failed workflows."""
        # Create invalid request
        invalid_request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,
            instance_id="test_instance",
            payload={},  # Missing required parameters
        )

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
        ):
            # Process one successful and one failed
            success_result = await subreducer.process(valid_workflow_request)
            failure_result = await subreducer.process(invalid_request)

        assert success_result.success is True
        assert failure_result.success is False

        # Check final metrics
        metrics = subreducer.get_metrics()
        assert metrics["total_processed"] == 2
        assert metrics["successful_processes"] == 1
        assert metrics["failed_processes"] == 1
        assert metrics["success_rate_percent"] == 50.0
        assert metrics["average_processing_time_ms"] > 0

    def test_get_metrics_structure(self, subreducer):
        """Test that get_metrics returns proper structure."""
        metrics = subreducer.get_metrics()

        # Verify required fields
        assert "total_processed" in metrics
        assert "successful_processes" in metrics
        assert "failed_processes" in metrics
        assert "average_processing_time_ms" in metrics
        assert "success_rate_percent" in metrics
        assert "subreducer_name" in metrics

        # Verify initial values
        assert metrics["total_processed"] == 0
        assert metrics["successful_processes"] == 0
        assert metrics["failed_processes"] == 0
        assert metrics["average_processing_time_ms"] == 0.0
        assert metrics["success_rate_percent"] == 0.0
        assert metrics["subreducer_name"] == "reducer_document_regeneration"

    @pytest.mark.asyncio
    async def test_average_processing_time_calculation(
        self, subreducer, valid_workflow_request
    ):
        """Test that average processing time is calculated correctly."""
        requests = []

        # Create multiple requests
        for i in range(3):
            req = ModelWorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.DOCUMENT_REGENERATION,
                instance_id=f"test_instance_{i}",
                payload={"document_id": f"doc_{i}", "content_type": "markdown"},
            )
            requests.append(req)

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
        ):
            # Process all requests
            for request in requests:
                await subreducer.process(request)

        # Check that average is reasonable
        metrics = subreducer.get_metrics()
        assert metrics["total_processed"] == 3
        assert metrics["successful_processes"] == 3
        assert metrics["average_processing_time_ms"] > 0
        # Should be around 100ms due to simulated sleep, but allow variance
        assert 50 <= metrics["average_processing_time_ms"] <= 200


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_empty_payload(self, subreducer):
        """Test handling of completely empty payload."""
        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,
            instance_id="test_instance",
            payload={},
        )

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
        ):
            result = await subreducer.process(request)

        assert result.success is False
        assert "Missing required parameters" in result.error_message

    @pytest.mark.asyncio
    async def test_none_payload_values(self, subreducer):
        """Test handling of None values in payload."""
        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,
            instance_id="test_instance",
            payload={"document_id": None, "content_type": "markdown"},
        )

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
        ):
            # This should still process since None is a valid value, just extract it
            params = subreducer._extract_document_params(request)
            assert params["document_id"] is None

    @pytest.mark.asyncio
    async def test_correlation_id_tracking(self, subreducer, valid_workflow_request):
        """Test that correlation ID is properly tracked throughout processing."""
        correlation_id = valid_workflow_request.correlation_id

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
        ) as mock_log:
            result = await subreducer.process(valid_workflow_request)

        assert result.success is True

        # Check that correlation ID appears in result
        proc_info = result.result["processing_info"]
        assert proc_info["correlation_id"] == str(correlation_id)

        # Check that correlation ID appears in logs
        log_calls = mock_log.call_args_list
        correlation_logs = [
            call for call in log_calls if str(correlation_id) in str(call)
        ]
        assert len(correlation_logs) > 0

    @pytest.mark.asyncio
    async def test_large_payload_handling(self, subreducer):
        """Test handling of large payloads."""
        # Create request with large payload
        large_metadata = {f"key_{i}": f"value_{i}" * 100 for i in range(100)}

        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,
            instance_id="test_instance",
            payload={
                "document_id": "large_doc",
                "content_type": "markdown",
                "metadata": large_metadata,
            },
        )

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
        ):
            result = await subreducer.process(request)

        # Should still succeed
        assert result.success is True

        # Metadata should be preserved
        result_metadata = result.result["metadata"]
        assert len(result_metadata) > 100  # Original large metadata plus added fields


class TestLoggingCompliance:
    """Test logging compliance and structured logging patterns."""

    @pytest.mark.asyncio
    async def test_structured_logging_events(self, subreducer, valid_workflow_request):
        """Test that all required structured logging events are emitted."""
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
        ) as mock_log:
            await subreducer.process(valid_workflow_request)

        # Get all log calls
        log_calls = mock_log.call_args_list

        # Verify specific events are logged
        events = [str(call) for call in log_calls]

        # Check for required events
        assert any("document_regeneration_started" in event for event in events)
        assert any("document_params_extracted" in event for event in events)
        assert any("document_regeneration_processing" in event for event in events)
        assert any("document_regeneration_completed" in event for event in events)

    @pytest.mark.asyncio
    async def test_error_logging_events(self, subreducer):
        """Test that error events are properly logged."""
        # Create invalid request
        request = ModelWorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,
            instance_id="test_instance",
            payload={},  # Missing required parameters
        )

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
        ) as mock_log:
            await subreducer.process(request)

        # Check for error logging
        log_calls = mock_log.call_args_list
        error_events = [
            str(call)
            for call in log_calls
            if "document_regeneration_failed" in str(call)
        ]
        assert len(error_events) > 0

    @pytest.mark.asyncio
    async def test_log_context_completeness(self, subreducer, valid_workflow_request):
        """Test that log contexts contain required information."""
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
        ) as mock_log:
            await subreducer.process(valid_workflow_request)

        # Find completion log
        completion_calls = [
            call
            for call in mock_log.call_args_list
            if "document_regeneration_completed" in str(call)
        ]
        assert len(completion_calls) > 0

        # Extract context from completion log (assuming standard call structure)
        completion_call = completion_calls[0]
        call_kwargs = (
            completion_call.kwargs
            if hasattr(completion_call, "kwargs")
            else completion_call[1]
        )

        if "context" in call_kwargs:
            context = call_kwargs["context"]

            # Verify required context fields
            required_fields = [
                "workflow_id",
                "instance_id",
                "correlation_id",
                "subreducer_name",
                "processing_time_ms",
            ]

            for field in required_fields:
                # Context should contain these fields or the log call should reference them
                assert field in str(completion_call)
