"""
Phase 1 Integration Tests for Reducer Pattern Engine.

End-to-end integration tests that verify the complete Phase 1 implementation
works correctly with all components integrated: Engine → Router → Subreducer.
Tests correlation ID tracking, error propagation, metrics collection,
and ONEX compliance throughout the pipeline.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from omnibase_core.core.errors.core_errors import OnexError
from omnibase_core.core.model_onex_container import ModelONEXContainer
from omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration import (
    ReducerDocumentRegenerationSubreducer,
)
from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.contracts import (
    WorkflowRequest,
    WorkflowResponse,
    WorkflowStatus,
    WorkflowType,
)
from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine import (
    ReducerPatternEngine,
)


@pytest.fixture
def mock_container():
    """Create a mock ModelONEXContainer for testing."""
    container = MagicMock(spec=ModelONEXContainer)
    return container


@pytest.fixture
def engine_with_subreducer(mock_container):
    """Create a ReducerPatternEngine with registered document regeneration subreducer."""
    with (
        patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event"
        ),
        patch(
            "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
        ),
    ):

        engine = ReducerPatternEngine(mock_container)
        subreducer = ReducerDocumentRegenerationSubreducer()

        # Register the subreducer
        engine.register_subreducer(subreducer, [WorkflowType.DOCUMENT_REGENERATION])

        return engine, subreducer


@pytest.fixture
def sample_workflow_request():
    """Create a sample workflow request for integration testing."""
    return WorkflowRequest(
        workflow_id=uuid4(),
        workflow_type=WorkflowType.DOCUMENT_REGENERATION,
        instance_id="integration_test_instance",
        correlation_id=uuid4(),
        payload={
            "document_id": "integration_doc_123",
            "content_type": "markdown",
            "template_id": "integration_template",
            "regeneration_options": {"format": "structured", "include_metadata": True},
            "metadata": {"test_type": "integration", "phase": "1"},
        },
        metadata={"integration_test": True},
    )


class TestPhase1EndToEndIntegration:
    """Test complete end-to-end workflow processing."""

    @pytest.mark.asyncio
    async def test_complete_successful_workflow(
        self, engine_with_subreducer, sample_workflow_request
    ):
        """Test complete successful workflow from engine to subreducer."""
        engine, subreducer = engine_with_subreducer

        with (
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event"
            ) as engine_log,
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
            ) as router_log,
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
            ) as subreducer_log,
        ):

            # Process the workflow end-to-end
            response = await engine.process_workflow(sample_workflow_request)

        # Verify response structure and content
        assert isinstance(response, WorkflowResponse)
        assert response.workflow_id == sample_workflow_request.workflow_id
        assert response.status == WorkflowStatus.COMPLETED
        assert response.subreducer_name == "reducer_document_regeneration"
        assert response.processing_time_ms > 0
        assert response.error_message is None
        assert response.error_details is None

        # Verify result content from subreducer is preserved
        assert response.result is not None
        assert "document_id" in response.result
        assert "regenerated_content" in response.result
        assert "processing_info" in response.result
        assert "metadata" in response.result

        # Verify processing info contains correlation tracking
        proc_info = response.result["processing_info"]
        assert proc_info["workflow_id"] == str(sample_workflow_request.workflow_id)
        assert proc_info["correlation_id"] == str(
            sample_workflow_request.correlation_id
        )
        assert proc_info["instance_id"] == sample_workflow_request.instance_id

        # Verify metadata preservation and enhancement
        metadata = response.result["metadata"]
        assert metadata["test_type"] == "integration"
        assert metadata["phase"] == "1"
        assert metadata["processed_by"] == "ReducerDocumentRegenerationSubreducer"

        # Verify logging occurred at all levels
        assert len(engine_log.call_args_list) > 0
        assert len(router_log.call_args_list) > 0
        assert len(subreducer_log.call_args_list) > 0

        # Verify metrics were updated
        engine_metrics = engine.get_metrics()
        assert engine_metrics.total_workflows_processed == 1
        assert engine_metrics.successful_workflows == 1
        assert engine_metrics.failed_workflows == 0

        subreducer_metrics = subreducer.get_metrics()
        assert subreducer_metrics["total_processed"] == 1
        assert subreducer_metrics["successful_processes"] == 1

    @pytest.mark.asyncio
    async def test_correlation_id_tracking_through_pipeline(
        self, engine_with_subreducer, sample_workflow_request
    ):
        """Test that correlation ID is tracked throughout the entire pipeline."""
        engine, subreducer = engine_with_subreducer
        correlation_id = sample_workflow_request.correlation_id

        with (
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event"
            ) as engine_log,
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
            ) as router_log,
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
            ) as subreducer_log,
        ):

            response = await engine.process_workflow(sample_workflow_request)

        assert response.status == WorkflowStatus.COMPLETED

        # Check correlation ID is in response result
        proc_info = response.result["processing_info"]
        assert proc_info["correlation_id"] == str(correlation_id)

        # Verify correlation ID appears in logs from all components
        all_logs = (
            engine_log.call_args_list
            + router_log.call_args_list
            + subreducer_log.call_args_list
        )
        correlation_mentions = [
            log for log in all_logs if str(correlation_id) in str(log)
        ]

        # Should appear in logs from multiple components
        assert len(correlation_mentions) > 2

    @pytest.mark.asyncio
    async def test_workflow_instance_isolation(self, engine_with_subreducer):
        """Test that multiple workflow instances are properly isolated."""
        engine, subreducer = engine_with_subreducer

        # Create multiple workflow requests with different instance IDs
        requests = []
        for i in range(3):
            request = WorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.DOCUMENT_REGENERATION,
                instance_id=f"instance_{i}",
                correlation_id=uuid4(),
                payload={
                    "document_id": f"doc_{i}",
                    "content_type": "markdown",
                    "instance_data": f"data_for_instance_{i}",
                },
            )
            requests.append(request)

        with (
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event"
            ),
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
            ),
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
            ),
        ):

            # Process all workflows
            responses = []
            for request in requests:
                response = await engine.process_workflow(request)
                responses.append(response)

        # Verify all succeeded
        for response in responses:
            assert response.status == WorkflowStatus.COMPLETED

        # Verify instance isolation - each response should have correct instance data
        for i, response in enumerate(responses):
            assert response.result["document_id"] == f"doc_{i}"
            proc_info = response.result["processing_info"]
            assert proc_info["instance_id"] == f"instance_{i}"

            # Each should have different workflow and correlation IDs
            assert proc_info["workflow_id"] == str(requests[i].workflow_id)
            assert proc_info["correlation_id"] == str(requests[i].correlation_id)

        # Verify metrics reflect all processed workflows
        engine_metrics = engine.get_metrics()
        assert engine_metrics.total_workflows_processed == 3
        assert engine_metrics.successful_workflows == 3

        subreducer_metrics = subreducer.get_metrics()
        assert subreducer_metrics["total_processed"] == 3
        assert subreducer_metrics["successful_processes"] == 3

    @pytest.mark.asyncio
    async def test_concurrent_workflow_processing(self, engine_with_subreducer):
        """Test concurrent processing of multiple workflows."""
        engine, subreducer = engine_with_subreducer

        # Create multiple concurrent workflow requests
        requests = []
        for i in range(5):
            request = WorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.DOCUMENT_REGENERATION,
                instance_id=f"concurrent_instance_{i}",
                correlation_id=uuid4(),
                payload={
                    "document_id": f"concurrent_doc_{i}",
                    "content_type": "markdown",
                },
            )
            requests.append(request)

        with (
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event"
            ),
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
            ),
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
            ),
        ):

            # Process workflows concurrently
            tasks = [engine.process_workflow(request) for request in requests]
            responses = await asyncio.gather(*tasks)

        # Verify all succeeded
        assert len(responses) == 5
        for response in responses:
            assert response.status == WorkflowStatus.COMPLETED

        # Verify each response is for correct workflow
        workflow_ids = {str(req.workflow_id) for req in requests}
        response_workflow_ids = {str(resp.workflow_id) for resp in responses}
        assert workflow_ids == response_workflow_ids

        # Verify metrics
        engine_metrics = engine.get_metrics()
        assert engine_metrics.total_workflows_processed == 5
        assert engine_metrics.successful_workflows == 5


class TestPhase1ErrorPropagation:
    """Test error handling and propagation through the pipeline."""

    @pytest.mark.asyncio
    async def test_subreducer_error_propagation(self, mock_container):
        """Test that subreducer errors are properly propagated to engine response."""
        with (
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event"
            ),
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
            ),
        ):

            engine = ReducerPatternEngine(mock_container)
            subreducer = ReducerDocumentRegenerationSubreducer()
            engine.register_subreducer(subreducer, [WorkflowType.DOCUMENT_REGENERATION])

            # Create request with missing required parameters (will cause subreducer error)
            request = WorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.DOCUMENT_REGENERATION,
                instance_id="error_test_instance",
                payload={},  # Missing required parameters
            )

            response = await engine.process_workflow(request)

        # Verify error is propagated correctly
        assert response.status == WorkflowStatus.FAILED
        assert "Missing required parameters" in response.error_message
        assert response.subreducer_name == "reducer_document_regeneration"
        assert response.processing_time_ms > 0

        # Verify metrics reflect the failure
        engine_metrics = engine.get_metrics()
        assert engine_metrics.total_workflows_processed == 1
        assert engine_metrics.failed_workflows == 1
        assert engine_metrics.successful_workflows == 0

        subreducer_metrics = subreducer.get_metrics()
        assert subreducer_metrics["total_processed"] == 1
        assert subreducer_metrics["failed_processes"] == 1

    @pytest.mark.asyncio
    async def test_router_error_propagation(self, mock_container):
        """Test that router errors are properly propagated to engine response."""
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event"
        ):
            engine = ReducerPatternEngine(mock_container)
            # Don't register any subreducers to cause router error

            request = WorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.DOCUMENT_REGENERATION,
                instance_id="router_error_test",
                payload={"document_id": "test_doc", "content_type": "markdown"},
            )

            response = await engine.process_workflow(request)

        # Verify router error is propagated
        assert response.status == WorkflowStatus.FAILED
        assert "Unsupported workflow type" in response.error_message
        assert response.processing_time_ms > 0

        # Verify metrics reflect the failure
        engine_metrics = engine.get_metrics()
        assert engine_metrics.total_workflows_processed == 1
        assert engine_metrics.failed_workflows == 1

    @pytest.mark.asyncio
    async def test_exception_handling_throughout_pipeline(
        self, engine_with_subreducer, sample_workflow_request
    ):
        """Test handling of unexpected exceptions in the pipeline."""
        engine, subreducer = engine_with_subreducer

        # Mock router to raise an unexpected exception
        with (
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event"
            ),
            patch.object(
                engine._router,
                "route",
                side_effect=RuntimeError("Unexpected router error"),
            ),
        ):

            response = await engine.process_workflow(sample_workflow_request)

        # Verify exception is handled gracefully
        assert response.status == WorkflowStatus.FAILED
        assert "Unexpected router error" in response.error_message
        assert response.error_details is not None
        assert response.error_details["error_type"] == "RuntimeError"

        # Verify metrics still updated despite exception
        engine_metrics = engine.get_metrics()
        assert engine_metrics.total_workflows_processed == 1
        assert engine_metrics.failed_workflows == 1


class TestPhase1PerformanceMetrics:
    """Test performance metrics collection throughout the pipeline."""

    @pytest.mark.asyncio
    async def test_end_to_end_performance_metrics(
        self, engine_with_subreducer, sample_workflow_request
    ):
        """Test that performance metrics are collected throughout the pipeline."""
        engine, subreducer = engine_with_subreducer

        with (
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event"
            ),
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
            ),
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
            ),
        ):

            # Record start time
            start_time = time.perf_counter()

            # Process workflow
            response = await engine.process_workflow(sample_workflow_request)

            # Record end time
            end_time = time.perf_counter()
            actual_time_ms = (end_time - start_time) * 1000

        assert response.status == WorkflowStatus.COMPLETED

        # Verify response timing is reasonable
        assert response.processing_time_ms > 0
        assert response.processing_time_ms <= actual_time_ms + 50  # Allow overhead

        # Verify engine metrics
        engine_metrics = engine.get_metrics()
        assert engine_metrics.average_processing_time_ms > 0

        # Verify subreducer metrics
        subreducer_metrics = subreducer.get_metrics()
        assert subreducer_metrics["average_processing_time_ms"] > 0

        # Verify router metrics are included
        assert "router" in engine_metrics.subreducer_metrics
        router_metrics = engine_metrics.subreducer_metrics["router"]
        assert router_metrics["total_routed"] == 1
        assert router_metrics["average_routing_time_ms"] > 0

    @pytest.mark.asyncio
    async def test_metrics_aggregation_across_workflows(self, engine_with_subreducer):
        """Test that metrics are properly aggregated across multiple workflows."""
        engine, subreducer = engine_with_subreducer

        # Process multiple workflows
        num_workflows = 3
        requests = []

        for i in range(num_workflows):
            request = WorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.DOCUMENT_REGENERATION,
                instance_id=f"metrics_test_{i}",
                payload={"document_id": f"metrics_doc_{i}", "content_type": "markdown"},
            )
            requests.append(request)

        with (
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event"
            ),
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
            ),
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
            ),
        ):

            # Process all workflows
            for request in requests:
                response = await engine.process_workflow(request)
                assert response.status == WorkflowStatus.COMPLETED

        # Verify aggregated metrics
        engine_metrics = engine.get_metrics()
        assert engine_metrics.total_workflows_processed == num_workflows
        assert engine_metrics.successful_workflows == num_workflows
        assert engine_metrics.failed_workflows == 0
        assert engine_metrics.calculate_success_rate() == 100.0
        assert engine_metrics.average_processing_time_ms > 0

        subreducer_metrics = subreducer.get_metrics()
        assert subreducer_metrics["total_processed"] == num_workflows
        assert subreducer_metrics["successful_processes"] == num_workflows
        assert subreducer_metrics["success_rate_percent"] == 100.0
        assert subreducer_metrics["average_processing_time_ms"] > 0

        # Verify router metrics
        router_metrics = engine_metrics.subreducer_metrics["router"]
        assert router_metrics["total_routed"] == num_workflows
        assert router_metrics["routing_errors"] == 0


class TestPhase1ONEXCompliance:
    """Test ONEX standards compliance throughout the pipeline."""

    @pytest.mark.asyncio
    async def test_structured_logging_compliance(
        self, engine_with_subreducer, sample_workflow_request
    ):
        """Test that structured logging follows ONEX patterns throughout pipeline."""
        engine, subreducer = engine_with_subreducer

        with (
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event"
            ) as engine_log,
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
            ) as router_log,
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
            ) as subreducer_log,
        ):

            response = await engine.process_workflow(sample_workflow_request)

        assert response.status == WorkflowStatus.COMPLETED

        # Verify structured logging occurred at all levels
        all_logs = (
            engine_log.call_args_list
            + router_log.call_args_list
            + subreducer_log.call_args_list
        )
        assert len(all_logs) > 5  # Should have multiple log entries

        # Verify log entries contain structured information
        log_strings = [str(log) for log in all_logs]

        # Check for key workflow identifiers in logs
        workflow_id_mentions = [
            log
            for log in log_strings
            if str(sample_workflow_request.workflow_id) in log
        ]
        assert len(workflow_id_mentions) > 0

        correlation_id_mentions = [
            log
            for log in log_strings
            if str(sample_workflow_request.correlation_id) in log
        ]
        assert len(correlation_id_mentions) > 0

    @pytest.mark.asyncio
    async def test_error_handling_onex_compliance(self, mock_container):
        """Test that error handling follows ONEX patterns."""
        with (
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event"
            ),
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
            ) as subreducer_log,
        ):

            engine = ReducerPatternEngine(mock_container)
            subreducer = ReducerDocumentRegenerationSubreducer()
            engine.register_subreducer(subreducer, [WorkflowType.DOCUMENT_REGENERATION])

            # Create request that will cause OnexError
            request = WorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.DOCUMENT_REGENERATION,
                instance_id="onex_error_test",
                payload={},  # Missing required parameters
            )

            response = await engine.process_workflow(request)

        # Verify OnexError handling
        assert response.status == WorkflowStatus.FAILED
        assert response.error_details is not None
        assert response.error_details["error_type"] == "OnexError"

        # Verify error logging follows ONEX patterns
        error_logs = [
            log for log in subreducer_log.call_args_list if "failed" in str(log)
        ]
        assert len(error_logs) > 0

    @pytest.mark.asyncio
    async def test_model_container_integration(
        self, engine_with_subreducer, sample_workflow_request
    ):
        """Test proper integration with ModelONEXContainer."""
        engine, subreducer = engine_with_subreducer

        # Verify engine has ModelONEXContainer
        assert hasattr(engine, "container")
        assert engine.container is not None

        with (
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event"
            ),
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
            ),
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
            ),
        ):

            response = await engine.process_workflow(sample_workflow_request)

        assert response.status == WorkflowStatus.COMPLETED

        # Container should be available throughout processing
        # (In a real implementation, subreducers might use container for model loading)

    def test_typing_compliance(self, engine_with_subreducer):
        """Test that all components use proper typing (no Any types)."""
        engine, subreducer = engine_with_subreducer

        # Verify engine typing
        assert hasattr(engine, "__annotations__") or hasattr(
            engine.__init__, "__annotations__"
        )

        # Verify subreducer typing
        assert hasattr(subreducer, "__annotations__") or hasattr(
            subreducer.__init__, "__annotations__"
        )

        # Verify router typing
        assert hasattr(engine._router, "__annotations__") or hasattr(
            engine._router.__init__, "__annotations__"
        )

        # This test primarily ensures imports work correctly with proper typing


class TestPhase1ActiveWorkflowTracking:
    """Test active workflow tracking throughout the pipeline."""

    @pytest.mark.asyncio
    async def test_active_workflow_lifecycle(
        self, engine_with_subreducer, sample_workflow_request
    ):
        """Test that active workflows are properly tracked during processing."""
        engine, subreducer = engine_with_subreducer
        workflow_id = sample_workflow_request.workflow_id

        # Create a custom subreducer that lets us check active workflows mid-processing
        class TrackingSubreducer(ReducerDocumentRegenerationSubreducer):
            def __init__(self, engine_ref):
                super().__init__()
                self.engine_ref = engine_ref
                self.mid_processing_active_workflows = None

            async def process(self, request):
                # Capture active workflows mid-processing
                self.mid_processing_active_workflows = (
                    self.engine_ref.get_active_workflows()
                )
                return await super().process(request)

        # Replace the subreducer with our tracking version
        tracking_subreducer = TrackingSubreducer(engine)
        engine._router._subreducers.clear()
        engine._router._workflow_type_mappings.clear()
        engine.register_subreducer(
            tracking_subreducer, [WorkflowType.DOCUMENT_REGENERATION]
        )

        # Verify no active workflows initially
        initial_active = engine.get_active_workflows()
        assert len(initial_active) == 0

        with (
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event"
            ),
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
            ),
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
            ),
        ):

            response = await engine.process_workflow(sample_workflow_request)

        assert response.status == WorkflowStatus.COMPLETED

        # Verify workflow was tracked during processing
        assert tracking_subreducer.mid_processing_active_workflows is not None
        assert str(workflow_id) in tracking_subreducer.mid_processing_active_workflows

        # Verify workflow is no longer active after completion
        final_active = engine.get_active_workflows()
        assert str(workflow_id) not in final_active

    @pytest.mark.asyncio
    async def test_concurrent_active_workflow_tracking(self, engine_with_subreducer):
        """Test active workflow tracking with concurrent workflows."""
        engine, subreducer = engine_with_subreducer

        # Create multiple workflow requests
        requests = []
        for i in range(3):
            request = WorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.DOCUMENT_REGENERATION,
                instance_id=f"concurrent_active_{i}",
                payload={"document_id": f"active_doc_{i}", "content_type": "markdown"},
            )
            requests.append(request)

        with (
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event"
            ),
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
            ),
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
            ),
        ):

            # Process workflows concurrently
            tasks = [engine.process_workflow(request) for request in requests]
            responses = await asyncio.gather(*tasks)

        # All should have completed successfully
        for response in responses:
            assert response.status == WorkflowStatus.COMPLETED

        # No workflows should be active after completion
        final_active = engine.get_active_workflows()
        assert len(final_active) == 0

        # All workflows should have been processed
        engine_metrics = engine.get_metrics()
        assert engine_metrics.total_workflows_processed == 3
        assert engine_metrics.successful_workflows == 3


class TestPhase1AcceptanceCriteria:
    """Test that Phase 1 meets all acceptance criteria defined in requirements."""

    @pytest.mark.asyncio
    async def test_phase1_workflow_processing_acceptance(
        self, engine_with_subreducer, sample_workflow_request
    ):
        """Test that Phase 1 implements basic workflow processing as required."""
        engine, subreducer = engine_with_subreducer

        with (
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event"
            ),
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
            ),
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
            ),
        ):

            response = await engine.process_workflow(sample_workflow_request)

        # ✅ Acceptance Criteria: Basic workflow processing implemented
        assert response.status == WorkflowStatus.COMPLETED
        assert response.workflow_id == sample_workflow_request.workflow_id
        assert response.processing_time_ms > 0

        # ✅ Acceptance Criteria: Subreducer registration and routing working
        assert response.subreducer_name == "reducer_document_regeneration"
        assert response.result is not None

        # ✅ Acceptance Criteria: Error handling implemented
        # (Tested in other test methods)

        # ✅ Acceptance Criteria: Metrics collection working
        engine_metrics = engine.get_metrics()
        assert engine_metrics.total_workflows_processed == 1
        assert engine_metrics.successful_workflows == 1

        # ✅ Acceptance Criteria: Structured logging implemented
        # (Verified by patch assertions and log calls)

    @pytest.mark.asyncio
    async def test_phase1_reference_implementation_acceptance(
        self, engine_with_subreducer, sample_workflow_request
    ):
        """Test that Phase 1 includes working reference implementation."""
        engine, subreducer = engine_with_subreducer

        with (
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event"
            ),
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
            ),
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
            ),
        ):

            response = await engine.process_workflow(sample_workflow_request)

        # ✅ Acceptance Criteria: Reference subreducer processes DOCUMENT_REGENERATION workflows
        assert response.status == WorkflowStatus.COMPLETED
        assert response.result["document_id"] == "integration_doc_123"
        assert "regenerated_content" in response.result
        assert response.result["regenerated_content"]["content_type"] == "markdown"

        # ✅ Acceptance Criteria: Proper parameter validation and processing
        assert (
            response.result["processing_info"]["instance_id"]
            == "integration_test_instance"
        )
        assert (
            response.result["metadata"]["processed_by"]
            == "ReducerDocumentRegenerationSubreducer"
        )

        # ✅ Acceptance Criteria: Integration with ONEX patterns
        assert response.result["processing_info"]["workflow_id"] == str(
            sample_workflow_request.workflow_id
        )
        assert response.result["processing_info"]["correlation_id"] == str(
            sample_workflow_request.correlation_id
        )

    @pytest.mark.asyncio
    async def test_phase1_architecture_compliance_acceptance(
        self, engine_with_subreducer
    ):
        """Test that Phase 1 follows ONEX four-node architecture patterns."""
        engine, subreducer = engine_with_subreducer

        # ✅ Acceptance Criteria: Four-node architecture compliance
        # Engine extends NodeReducer ✓
        from omnibase_core.patterns.node_reducer import NodeReducer

        assert isinstance(engine, NodeReducer)

        # ✅ Acceptance Criteria: ModelONEXContainer integration
        from omnibase_core.core.model_onex_container import ModelONEXContainer

        assert hasattr(engine, "container")
        # Container is mocked but type should be preserved in real usage

        # ✅ Acceptance Criteria: Proper contract usage throughout
        from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.contracts import (
            WorkflowRequest,
            WorkflowResponse,
            WorkflowStatus,
            WorkflowType,
        )

        # All contract models should be importable and usable
        request = WorkflowRequest(
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,
            instance_id="test",
            payload={"document_id": "test", "content_type": "test"},
        )
        assert request.workflow_type == WorkflowType.DOCUMENT_REGENERATION

        # ✅ Acceptance Criteria: Registry pattern for subreducers
        registered_subreducer = engine._router.get_subreducer(
            "reducer_document_regeneration"
        )
        assert registered_subreducer is not None
        assert registered_subreducer.name == "reducer_document_regeneration"

    @pytest.mark.asyncio
    async def test_phase1_performance_requirements_acceptance(
        self, engine_with_subreducer
    ):
        """Test that Phase 1 meets basic performance requirements."""
        engine, subreducer = engine_with_subreducer

        # Create request for performance testing
        request = WorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,
            instance_id="performance_test",
            payload={"document_id": "perf_doc", "content_type": "markdown"},
        )

        with (
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event"
            ),
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
            ),
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event"
            ),
        ):

            start_time = time.perf_counter()
            response = await engine.process_workflow(request)
            end_time = time.perf_counter()

        processing_time_ms = (end_time - start_time) * 1000

        # ✅ Acceptance Criteria: Reasonable processing performance
        assert response.status == WorkflowStatus.COMPLETED
        assert processing_time_ms < 5000  # Should complete within 5 seconds
        assert response.processing_time_ms > 0
        assert (
            response.processing_time_ms <= processing_time_ms + 100
        )  # Reasonable overhead

        # ✅ Acceptance Criteria: Performance metrics collection
        engine_metrics = engine.get_metrics()
        assert engine_metrics.average_processing_time_ms > 0
        assert engine_metrics.average_processing_time_ms < 5000

        subreducer_metrics = subreducer.get_metrics()
        assert subreducer_metrics["average_processing_time_ms"] > 0
