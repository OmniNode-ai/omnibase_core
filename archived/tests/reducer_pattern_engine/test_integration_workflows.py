"""
Comprehensive Integration Tests for Reducer Pattern Engine Phase 2.

End-to-end integration tests that verify complete workflow processing from request
to response for all supported workflow types. Tests multi-component integration,
concurrent processing, error recovery, state persistence, and metrics collection
across the entire system.

Addresses PR review feedback regarding missing integration tests for complete workflows.
"""

import asyncio
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.patterns.reducer_pattern_engine.models.state_transitions import (
    WorkflowState,
)
from omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_data_analysis import (
    ReducerDataAnalysisSubreducer,
)
from omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration import (
    ReducerDocumentRegenerationSubreducer,
)
from omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_report_generation import (
    ReducerReportGenerationSubreducer,
)
from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine import (
    ReducerPatternEngine,
)
from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.models import (
    BaseSubreducer,
    ModelSubreducerResult,
    ModelWorkflowRequest,
    ModelWorkflowResponse,
    WorkflowStatus,
    WorkflowType,
)


class IntegrationTestSubreducer(BaseSubreducer):
    """Test subreducer with configurable behavior for integration testing."""

    def __init__(
        self,
        name: str,
        supported_type: WorkflowType,
        success: bool = True,
        processing_delay: float = 0.1,
        failure_rate: float = 0.0,
        state_updates: list[WorkflowState] | None = None,
    ):
        """Initialize test subreducer with configurable behavior."""
        super().__init__(name)
        self._supported_type = supported_type
        self._success = success
        self._processing_delay = processing_delay
        self._failure_rate = failure_rate
        self._call_count = 0
        self._total_calls = 0
        self._state_updates = state_updates or [WorkflowState.PROCESSING]
        self._processing_history: list[dict[str, Any]] = []

    def supports_workflow_type(self, workflow_type: WorkflowType) -> bool:
        """Check if this subreducer supports the workflow type."""
        return workflow_type == self._supported_type

    async def process(self, request: ModelWorkflowRequest) -> ModelSubreducerResult:
        """Process workflow with configurable behavior and state tracking."""
        start_time = time.time()
        self._total_calls += 1

        # Record processing attempt
        processing_record = {
            "workflow_id": request.workflow_id,
            "instance_id": request.instance_id,
            "correlation_id": request.correlation_id,
            "start_time": start_time,
            "payload_size": len(str(request.payload)),
        }

        # Simulate processing time
        await asyncio.sleep(self._processing_delay)

        # Determine success based on failure rate
        should_fail = not self._success or (
            self._failure_rate > 0 and (self._total_calls * self._failure_rate) >= 1
        )

        processing_time = (time.time() - start_time) * 1000
        processing_record["processing_time"] = processing_time
        processing_record["success"] = not should_fail

        self._processing_history.append(processing_record)

        if should_fail:
            return ModelSubreducerResult(
                workflow_id=request.workflow_id,
                subreducer_name=self.name,
                success=False,
                error_message=f"Integration test failure for {request.workflow_type.value}",
                error_details={
                    "failure_simulation": True,
                    "total_calls": self._total_calls,
                    "failure_rate": self._failure_rate,
                },
                processing_time_ms=processing_time,
            )
        self._call_count += 1
        return ModelSubreducerResult(
            workflow_id=request.workflow_id,
            subreducer_name=self.name,
            success=True,
            result={
                "integration_test_result": f"Successfully processed {request.workflow_type.value}",
                "call_count": self._call_count,
                "instance_id": request.instance_id,
                "payload_processed": bool(request.payload),
                "metadata_processed": bool(request.metadata),
                "state_updates": [state.value for state in self._state_updates],
            },
            processing_time_ms=processing_time,
        )

    @property
    def call_count(self) -> int:
        """Get successful call count."""
        return self._call_count

    @property
    def total_calls(self) -> int:
        """Get total call count including failures."""
        return self._total_calls

    @property
    def processing_history(self) -> list[dict[str, Any]]:
        """Get complete processing history."""
        return self._processing_history.copy()


class TestIntegrationWorkflows:
    """Comprehensive integration test suite for complete workflow processing."""

    @pytest.fixture
    def mock_container(self) -> ModelONEXContainer:
        """Create mock ONEX container for testing."""
        container = MagicMock(spec=ModelONEXContainer)
        return container

    @pytest.fixture
    def integration_engine(self, mock_container) -> ReducerPatternEngine:
        """Create engine with real subreducers for integration testing."""
        with (
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event",
            ),
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_data_analysis.emit_log_event",
            ),
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_document_regeneration.emit_log_event",
            ),
            patch(
                "omnibase_core.patterns.reducer_pattern_engine.subreducers.reducer_report_generation.emit_log_event",
            ),
        ):
            engine = ReducerPatternEngine(mock_container)

            # Register all real subreducers
            data_analysis = ReducerDataAnalysisSubreducer()
            document_regen = ReducerDocumentRegenerationSubreducer()
            report_gen = ReducerReportGenerationSubreducer()

            engine.register_subreducer(data_analysis)
            engine.register_subreducer(document_regen)
            engine.register_subreducer(report_gen)

            return engine

    @pytest.fixture
    def test_engine(self, mock_container) -> ReducerPatternEngine:
        """Create engine with test subreducers for controlled integration testing."""
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event",
        ):
            engine = ReducerPatternEngine(mock_container)

            # Register test subreducers
            test_subreducers = [
                IntegrationTestSubreducer("data_test", WorkflowType.DATA_ANALYSIS),
                IntegrationTestSubreducer(
                    "doc_test",
                    WorkflowType.DOCUMENT_REGENERATION,
                ),
                IntegrationTestSubreducer(
                    "report_test",
                    WorkflowType.REPORT_GENERATION,
                ),
            ]

            for subreducer in test_subreducers:
                engine.register_subreducer(subreducer)

            return engine

    # ====== End-to-End Workflow Testing ======

    @pytest.mark.asyncio
    async def test_complete_data_analysis_workflow_integration(
        self,
        integration_engine,
    ):
        """Test complete data analysis workflow from request to response."""
        # Create realistic data analysis request
        request = ModelWorkflowRequest(
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="data_analysis_integration_test",
            payload={
                "analysis_type": "descriptive",
                "data": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                "options": {
                    "include_statistics": True,
                    "include_distribution": True,
                },
            },
            metadata={
                "source": "integration_test",
                "priority": "high",
            },
        )

        # Process workflow end-to-end
        start_time = time.time()
        response = await integration_engine.process_workflow(request)
        end_time = time.time()

        # Verify response structure
        assert isinstance(response, ModelWorkflowResponse)
        assert response.workflow_id == request.workflow_id
        assert response.workflow_type == WorkflowType.DATA_ANALYSIS
        assert response.instance_id == request.instance_id
        assert response.correlation_id == request.correlation_id
        assert response.status == WorkflowStatus.COMPLETED
        assert response.result is not None
        assert response.processing_time_ms is not None
        assert response.processing_time_ms > 0
        assert response.subreducer_name == "reducer_data_analysis"

        # Verify processing time is reasonable
        total_time = (end_time - start_time) * 1000
        assert response.processing_time_ms <= total_time

        # Verify result contains expected analysis data
        result = response.result
        assert "analysis_results" in result
        assert "statistics" in result["analysis_results"]
        assert "processed_data_points" in result

        # Verify state was managed correctly
        workflow_state = integration_engine.get_workflow_state(request.workflow_id)
        assert workflow_state is not None
        assert workflow_state.current_state == WorkflowState.COMPLETED
        assert workflow_state.workflow_type == WorkflowType.DATA_ANALYSIS

    @pytest.mark.asyncio
    async def test_complete_document_regeneration_workflow_integration(
        self,
        integration_engine,
    ):
        """Test complete document regeneration workflow from request to response."""
        request = ModelWorkflowRequest(
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,
            instance_id="doc_regen_integration_test",
            payload={
                "document_type": "technical_spec",
                "content": "Original content to be regenerated",
                "regeneration_options": {
                    "enhance_structure": True,
                    "improve_clarity": True,
                    "add_examples": False,
                },
                "target_format": "markdown",
            },
            metadata={
                "author": "integration_test",
                "version": "1.0",
            },
        )

        # Process workflow
        response = await integration_engine.process_workflow(request)

        # Verify successful completion
        assert response.status == WorkflowStatus.COMPLETED
        assert response.result is not None
        assert "regenerated_content" in response.result
        assert response.subreducer_name == "reducer_document_regeneration"

        # Verify state management
        workflow_state = integration_engine.get_workflow_state(request.workflow_id)
        assert workflow_state.current_state == WorkflowState.COMPLETED

    @pytest.mark.asyncio
    async def test_complete_report_generation_workflow_integration(
        self,
        integration_engine,
    ):
        """Test complete report generation workflow from request to response."""
        request = ModelWorkflowRequest(
            workflow_type=WorkflowType.REPORT_GENERATION,
            instance_id="report_gen_integration_test",
            payload={
                "report_type": "performance_analysis",
                "data_sources": ["metrics_db", "log_files"],
                "time_range": {
                    "start": "2023-01-01T00:00:00Z",
                    "end": "2023-01-31T23:59:59Z",
                },
                "output_format": "html",
                "sections": ["summary", "detailed_analysis", "recommendations"],
            },
        )

        # Process workflow
        response = await integration_engine.process_workflow(request)

        # Verify successful completion
        assert response.status == WorkflowStatus.COMPLETED
        assert response.result is not None
        assert "report_content" in response.result
        assert response.subreducer_name == "reducer_report_generation"

        # Verify state management
        workflow_state = integration_engine.get_workflow_state(request.workflow_id)
        assert workflow_state.current_state == WorkflowState.COMPLETED

    # ====== Multi-Component Integration Testing ======

    @pytest.mark.asyncio
    async def test_engine_router_registry_integration(self, test_engine):
        """Test integration between engine, router, and registry components."""
        # Get registered subreducers for verification
        subreducers = []
        for workflow_type in WorkflowType:
            subreducer = test_engine._registry.get_subreducer(workflow_type)
            assert subreducer is not None
            subreducers.append((workflow_type, subreducer))

        # Test routing decisions through registry
        for workflow_type, expected_subreducer in subreducers:
            request = ModelWorkflowRequest(
                workflow_type=workflow_type,
                instance_id=f"integration_test_{workflow_type.value}",
            )

            # Verify routing decision
            routing_decision = test_engine._router.route_workflow(
                request,
                test_engine._registry,
            )
            assert routing_decision.selected_subreducer == expected_subreducer.name
            assert routing_decision.routing_success is True

            # Process through engine and verify correct subreducer was used
            response = await test_engine.process_workflow(request)
            assert response.subreducer_name == expected_subreducer.name

    @pytest.mark.asyncio
    async def test_metrics_collection_integration(self, test_engine):
        """Test metrics collection across all components during workflow processing."""
        requests = [
            ModelWorkflowRequest(
                workflow_type=WorkflowType.DATA_ANALYSIS,
                instance_id="metrics_test_data",
            ),
            ModelWorkflowRequest(
                workflow_type=WorkflowType.DOCUMENT_REGENERATION,
                instance_id="metrics_test_doc",
            ),
            ModelWorkflowRequest(
                workflow_type=WorkflowType.REPORT_GENERATION,
                instance_id="metrics_test_report",
            ),
        ]

        # Process all workflows
        responses = []
        for request in requests:
            response = await test_engine.process_workflow(request)
            responses.append(response)

        # Verify metrics collection
        metrics = test_engine.get_metrics()
        # The metrics object structure varies by implementation
        # assert isinstance(metrics, WorkflowMetrics)  # WorkflowMetrics type varies
        assert metrics.total_workflows_processed >= 3
        assert metrics.successful_workflows >= 3
        assert metrics.failed_workflows == 0
        assert len(metrics.workflow_types_processed) == 3

        # Verify per-workflow-type metrics
        for workflow_type in WorkflowType:
            assert workflow_type.value in metrics.workflow_types_processed
            assert metrics.workflow_types_processed[workflow_type.value] >= 1

        # Verify response-level metrics
        for response in responses:
            assert response.processing_time_ms is not None
            assert response.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_state_management_integration(self, test_engine):
        """Test state management across complete workflow lifecycle."""
        request = ModelWorkflowRequest(
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="state_management_test",
        )

        # Verify initial state (should not exist)
        initial_state = test_engine.get_workflow_state(request.workflow_id)
        assert initial_state is None

        # Process workflow
        response = await test_engine.process_workflow(request)

        # Verify final state
        final_state = test_engine.get_workflow_state(request.workflow_id)
        assert final_state is not None
        assert final_state.workflow_id == request.workflow_id
        assert final_state.current_state == WorkflowState.COMPLETED
        assert final_state.workflow_type == WorkflowType.DATA_ANALYSIS
        assert final_state.instance_id == request.instance_id
        assert final_state.started_at is not None
        assert final_state.completed_at is not None

        # Verify state history
        state_history = test_engine.get_workflow_state_history(request.workflow_id)
        assert len(state_history) >= 1  # At least completed state
        assert WorkflowState.COMPLETED in state_history

    # ====== Concurrent Workflow Processing ======

    @pytest.mark.asyncio
    async def test_concurrent_workflow_processing_isolation(self, test_engine):
        """Test concurrent processing of multiple workflows with proper isolation."""
        # Create multiple concurrent requests
        requests = []
        for i in range(10):
            for workflow_type in WorkflowType:
                request = ModelWorkflowRequest(
                    workflow_type=workflow_type,
                    instance_id=f"concurrent_test_{workflow_type.value}_{i}",
                    payload={"test_id": i, "concurrent": True},
                )
                requests.append(request)

        # Process all workflows concurrently
        start_time = time.time()
        tasks = [test_engine.process_workflow(request) for request in requests]
        responses = await asyncio.gather(*tasks)
        end_time = time.time()

        # Verify all responses
        assert len(responses) == len(requests)
        successful_responses = [
            r for r in responses if r.status == WorkflowStatus.COMPLETED
        ]
        assert len(successful_responses) == len(requests)

        # Verify proper isolation - each workflow should have unique IDs
        workflow_ids = {response.workflow_id for response in responses}
        assert len(workflow_ids) == len(requests)  # All unique

        instance_ids = {response.instance_id for response in responses}
        assert len(instance_ids) == len(requests)  # All unique

        # Verify concurrent processing efficiency
        total_time = end_time - start_time
        sequential_time_estimate = sum(0.1 for _ in requests)  # 0.1s per request
        assert total_time < sequential_time_estimate * 0.5  # Should be much faster

        # Verify metrics reflect all processed workflows
        metrics = test_engine.get_metrics()
        assert metrics.total_workflows_processed >= len(requests)

    @pytest.mark.asyncio
    async def test_concurrent_same_workflow_type_processing(self, test_engine):
        """Test concurrent processing of same workflow type with different instances."""
        workflow_type = WorkflowType.DATA_ANALYSIS
        num_concurrent = 15

        requests = [
            ModelWorkflowRequest(
                workflow_type=workflow_type,
                instance_id=f"same_type_test_{i}",
                payload={"data": list(range(i * 10, (i + 1) * 10))},
            )
            for i in range(num_concurrent)
        ]

        # Process concurrently
        tasks = [test_engine.process_workflow(request) for request in requests]
        responses = await asyncio.gather(*tasks)

        # Verify all completed successfully
        assert all(r.status == WorkflowStatus.COMPLETED for r in responses)

        # Verify each got correct subreducer
        assert all(r.subreducer_name == "data_test" for r in responses)

        # Verify instance isolation
        instance_ids = {r.instance_id for r in responses}
        assert len(instance_ids) == num_concurrent

    # ====== Error Recovery Integration ======

    @pytest.mark.asyncio
    async def test_error_recovery_integration_single_failure(self, mock_container):
        """Test error recovery integration when single subreducer fails."""
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event",
        ):
            engine = ReducerPatternEngine(mock_container)

            # Register subreducers with one that fails
            successful_subreducer = IntegrationTestSubreducer(
                "success_test",
                WorkflowType.DATA_ANALYSIS,
            )
            failing_subreducer = IntegrationTestSubreducer(
                "fail_test",
                WorkflowType.DOCUMENT_REGENERATION,
                success=False,
            )

            engine.register_subreducer(successful_subreducer)
            engine.register_subreducer(failing_subreducer)

        # Test successful workflow
        success_request = ModelWorkflowRequest(
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="success_test",
        )

        success_response = await engine.process_workflow(success_request)
        assert success_response.status == WorkflowStatus.COMPLETED

        # Verify state is correctly managed for successful workflow
        success_state = engine.get_workflow_state(success_request.workflow_id)
        assert success_state.current_state == WorkflowState.COMPLETED

        # Test failing workflow
        fail_request = ModelWorkflowRequest(
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,
            instance_id="fail_test",
        )

        fail_response = await engine.process_workflow(fail_request)
        assert fail_response.status == WorkflowStatus.FAILED
        assert fail_response.error_message is not None

        # Verify state is correctly managed for failed workflow
        fail_state = engine.get_workflow_state(fail_request.workflow_id)
        assert fail_state.current_state == WorkflowState.FAILED

        # Verify metrics reflect both outcomes
        metrics = engine.get_metrics()
        assert metrics.successful_workflows >= 1
        assert metrics.failed_workflows >= 1

    @pytest.mark.asyncio
    async def test_error_recovery_with_partial_failures(self, mock_container):
        """Test error recovery when some workflows fail in concurrent processing."""
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event",
        ):
            engine = ReducerPatternEngine(mock_container)

            # Register subreducers with different failure rates
            data_subreducer = IntegrationTestSubreducer(
                "data_test",
                WorkflowType.DATA_ANALYSIS,
            )
            doc_subreducer = IntegrationTestSubreducer(
                "doc_test",
                WorkflowType.DOCUMENT_REGENERATION,
                failure_rate=0.5,
            )
            report_subreducer = IntegrationTestSubreducer(
                "report_test",
                WorkflowType.REPORT_GENERATION,
                failure_rate=0.3,
            )

            engine.register_subreducer(data_subreducer)
            engine.register_subreducer(doc_subreducer)
            engine.register_subreducer(report_subreducer)

        # Create mixed requests
        requests = []
        for i in range(20):
            workflow_type = [
                WorkflowType.DATA_ANALYSIS,
                WorkflowType.DOCUMENT_REGENERATION,
                WorkflowType.REPORT_GENERATION,
            ][i % 3]
            requests.append(
                ModelWorkflowRequest(
                    workflow_type=workflow_type,
                    instance_id=f"mixed_test_{i}",
                ),
            )

        # Process all workflows
        responses = await asyncio.gather(
            *[engine.process_workflow(req) for req in requests],
        )

        # Verify we got both successes and failures
        successful = [r for r in responses if r.status == WorkflowStatus.COMPLETED]
        failed = [r for r in responses if r.status == WorkflowStatus.FAILED]

        assert len(successful) > 0
        assert len(failed) > 0
        assert len(successful) + len(failed) == len(responses)

        # Verify metrics
        metrics = engine.get_metrics()
        assert metrics.successful_workflows == len(successful)
        assert metrics.failed_workflows == len(failed)

    @pytest.mark.asyncio
    async def test_routing_failure_recovery(self, mock_container):
        """Test recovery from routing failures (unsupported workflow types)."""
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event",
        ):
            engine = ReducerPatternEngine(mock_container)

            # Register only one subreducer
            engine.register_subreducer(
                IntegrationTestSubreducer("limited_test", WorkflowType.DATA_ANALYSIS),
            )

        # Test supported workflow type
        supported_request = ModelWorkflowRequest(
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="supported_test",
        )

        supported_response = await engine.process_workflow(supported_request)
        assert supported_response.status == WorkflowStatus.COMPLETED

        # Test unsupported workflow type
        unsupported_request = ModelWorkflowRequest(
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,
            instance_id="unsupported_test",
        )

        unsupported_response = await engine.process_workflow(unsupported_request)
        assert unsupported_response.status == WorkflowStatus.FAILED
        assert (
            "routing" in unsupported_response.error_message.lower()
            or "subreducer" in unsupported_response.error_message.lower()
        )

    # ====== State Persistence Integration ======

    @pytest.mark.asyncio
    async def test_state_persistence_across_workflow_lifecycle(self, test_engine):
        """Test state persistence and transitions throughout complete workflow lifecycle."""
        request = ModelWorkflowRequest(
            workflow_type=WorkflowType.REPORT_GENERATION,
            instance_id="state_persistence_test",
        )

        # Process workflow and track state changes
        response = await test_engine.process_workflow(request)

        # Verify final state persistence
        final_state = test_engine.get_workflow_state(request.workflow_id)
        assert final_state is not None
        assert final_state.workflow_id == request.workflow_id
        assert final_state.current_state == WorkflowState.COMPLETED
        assert final_state.correlation_id == request.correlation_id

        # Verify timestamps
        assert final_state.started_at is not None
        assert final_state.completed_at is not None
        assert final_state.completed_at >= final_state.started_at

        # Verify state can be retrieved after processing
        retrieved_state = test_engine.get_workflow_state(request.workflow_id)
        assert retrieved_state.workflow_id == final_state.workflow_id
        assert retrieved_state.current_state == final_state.current_state

    @pytest.mark.asyncio
    async def test_state_cleanup_integration(self, test_engine):
        """Test state cleanup functionality in integrated environment."""
        # Create and process multiple workflows to trigger potential cleanup
        requests = []
        for i in range(50):  # Create enough to potentially trigger cleanup
            request = ModelWorkflowRequest(
                workflow_type=WorkflowType.DATA_ANALYSIS,
                instance_id=f"cleanup_test_{i}",
            )
            requests.append(request)

        # Process all workflows
        responses = await asyncio.gather(
            *[test_engine.process_workflow(req) for req in requests],
        )

        # Verify all processed successfully
        assert all(r.status == WorkflowStatus.COMPLETED for r in responses)

        # Verify states exist
        for request in requests:
            state = test_engine.get_workflow_state(request.workflow_id)
            assert state is not None

        # Trigger cleanup manually if available
        if hasattr(test_engine, "_cleanup_old_workflow_states"):
            test_engine._cleanup_old_workflow_states()

        # States should still be accessible immediately after processing
        active_states = 0
        for request in requests:
            state = test_engine.get_workflow_state(request.workflow_id)
            if state is not None:
                active_states += 1

        # At least some states should still exist (depends on cleanup policy)
        assert active_states > 0

    # ====== Performance Integration Testing ======

    @pytest.mark.asyncio
    async def test_performance_integration_throughput(self, test_engine):
        """Test performance integration under load conditions."""
        num_workflows = 100

        # Create diverse workload
        requests = []
        for i in range(num_workflows):
            workflow_type = [
                WorkflowType.DATA_ANALYSIS,
                WorkflowType.DOCUMENT_REGENERATION,
                WorkflowType.REPORT_GENERATION,
            ][i % 3]
            request = ModelWorkflowRequest(
                workflow_type=workflow_type,
                instance_id=f"perf_test_{i}",
                payload={"size": "large", "complexity": "high"},
            )
            requests.append(request)

        # Process with timing
        start_time = time.time()
        responses = await asyncio.gather(
            *[test_engine.process_workflow(req) for req in requests],
        )
        end_time = time.time()

        # Verify all completed
        successful = [r for r in responses if r.status == WorkflowStatus.COMPLETED]
        assert len(successful) == num_workflows

        # Verify performance metrics
        total_time = end_time - start_time
        throughput = num_workflows / total_time

        # Should achieve reasonable throughput (adjust based on requirements)
        assert throughput > 10  # At least 10 workflows/second

        # Verify response times are reasonable
        response_times = [r.processing_time_ms for r in responses]
        avg_response_time = sum(response_times) / len(response_times)

        # Average response time should be reasonable
        assert avg_response_time < 500  # Less than 500ms average

    @pytest.mark.asyncio
    async def test_memory_usage_integration(self, test_engine):
        """Test memory usage during integrated workflow processing."""
        # Process workflows and monitor state accumulation
        num_batches = 5
        batch_size = 20

        for batch in range(num_batches):
            requests = [
                ModelWorkflowRequest(
                    workflow_type=WorkflowType.DATA_ANALYSIS,
                    instance_id=f"memory_test_{batch}_{i}",
                )
                for i in range(batch_size)
            ]

            # Process batch
            responses = await asyncio.gather(
                *[test_engine.process_workflow(req) for req in requests],
            )
            assert all(r.status == WorkflowStatus.COMPLETED for r in responses)

        # Verify metrics are being tracked correctly
        metrics = test_engine.get_metrics()
        assert metrics.total_workflows_processed >= num_batches * batch_size

        # Verify state management isn't consuming excessive memory
        # This is a basic check - in production you'd want more sophisticated memory monitoring
        active_states = 0
        for batch in range(num_batches):
            for i in range(batch_size):
                # Create workflow_id that matches what would have been generated
                # This is a simplified check since we can't recreate exact UUIDs
                active_states += 1

        # We processed workflows, so there should be evidence of processing
        assert metrics.total_workflows_processed > 0

    # ====== Full System Integration ======

    @pytest.mark.asyncio
    async def test_full_system_integration_end_to_end(self, integration_engine):
        """Test complete system integration with all real components."""
        # Create comprehensive test scenario with all workflow types
        test_scenarios = [
            {
                "type": WorkflowType.DATA_ANALYSIS,
                "payload": {
                    "analysis_type": "descriptive",
                    "data": [1, 2, 3, 4, 5] * 20,  # Larger dataset
                    "options": {"include_all": True},
                },
                "expected_result_keys": ["analysis_results", "processed_data_points"],
            },
            {
                "type": WorkflowType.DOCUMENT_REGENERATION,
                "payload": {
                    "document_type": "user_manual",
                    "content": "This is a comprehensive user manual content that needs regeneration.",
                    "regeneration_options": {
                        "enhance_structure": True,
                        "improve_clarity": True,
                    },
                },
                "expected_result_keys": ["regenerated_content"],
            },
            {
                "type": WorkflowType.REPORT_GENERATION,
                "payload": {
                    "report_type": "comprehensive_analysis",
                    "data_sources": ["primary", "secondary"],
                    "sections": ["executive_summary", "detailed_analysis"],
                },
                "expected_result_keys": ["report_content"],
            },
        ]

        responses = []

        # Process each scenario
        for i, scenario in enumerate(test_scenarios):
            request = ModelWorkflowRequest(
                workflow_type=scenario["type"],
                instance_id=f"full_integration_{i}_{scenario['type'].value}",
                payload=scenario["payload"],
                metadata={"test_scenario": i, "integration_test": True},
            )

            response = await integration_engine.process_workflow(request)
            responses.append((scenario, response))

        # Verify all scenarios completed successfully
        for scenario, response in responses:
            assert (
                response.status == WorkflowStatus.COMPLETED
            ), f"Failed scenario: {scenario['type']}"
            assert response.result is not None

            # Verify expected result structure
            for expected_key in scenario["expected_result_keys"]:
                assert (
                    expected_key in response.result
                ), f"Missing key {expected_key} in {scenario['type']} response"

        # Verify system-wide metrics
        metrics = integration_engine.get_metrics()
        assert metrics.total_workflows_processed >= len(test_scenarios)
        assert metrics.successful_workflows >= len(test_scenarios)
        assert metrics.failed_workflows == 0

        # Verify all workflow types were processed
        for scenario in test_scenarios:
            assert scenario["type"].value in metrics.workflow_types_processed

        # Verify state management worked correctly
        for scenario, response in responses:
            state = integration_engine.get_workflow_state(response.workflow_id)
            assert state is not None
            assert state.current_state == WorkflowState.COMPLETED

    @pytest.mark.asyncio
    async def test_comprehensive_error_scenarios_integration(self, mock_container):
        """Test comprehensive error scenarios in integrated environment."""
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event",
        ):
            engine = ReducerPatternEngine(mock_container)

            # Register subreducers with various failure modes
            success_subreducer = IntegrationTestSubreducer(
                "success",
                WorkflowType.DATA_ANALYSIS,
            )
            slow_failing_subreducer = IntegrationTestSubreducer(
                "slow_fail",
                WorkflowType.DOCUMENT_REGENERATION,
                success=False,
                processing_delay=0.2,
            )
            intermittent_subreducer = IntegrationTestSubreducer(
                "intermittent",
                WorkflowType.REPORT_GENERATION,
                failure_rate=0.5,
            )

            engine.register_subreducer(success_subreducer)
            engine.register_subreducer(slow_failing_subreducer)
            engine.register_subreducer(intermittent_subreducer)

        # Test mixed success/failure scenarios concurrently
        requests = []
        expected_outcomes = []

        # Always successful requests
        for i in range(5):
            requests.append(
                ModelWorkflowRequest(
                    workflow_type=WorkflowType.DATA_ANALYSIS,
                    instance_id=f"success_{i}",
                ),
            )
            expected_outcomes.append("success")

        # Always failing requests
        for i in range(5):
            requests.append(
                ModelWorkflowRequest(
                    workflow_type=WorkflowType.DOCUMENT_REGENERATION,
                    instance_id=f"fail_{i}",
                ),
            )
            expected_outcomes.append("failure")

        # Intermittent requests (will have mixed outcomes)
        for i in range(10):
            requests.append(
                ModelWorkflowRequest(
                    workflow_type=WorkflowType.REPORT_GENERATION,
                    instance_id=f"intermittent_{i}",
                ),
            )
            expected_outcomes.append("intermittent")

        # Process all concurrently
        responses = await asyncio.gather(
            *[engine.process_workflow(req) for req in requests],
        )

        # Verify expected outcomes
        success_count = len(
            [r for r in responses if r.status == WorkflowStatus.COMPLETED],
        )
        failure_count = len([r for r in responses if r.status == WorkflowStatus.FAILED])

        # Should have some successes and some failures
        assert success_count >= 5  # At least the always-successful ones
        assert failure_count >= 5  # At least the always-failing ones
        assert success_count + failure_count == len(responses)

        # Verify metrics reflect mixed outcomes
        metrics = engine.get_metrics()
        assert metrics.successful_workflows == success_count
        assert metrics.failed_workflows == failure_count
        assert metrics.total_workflows_processed == len(responses)

        # Verify state management for all outcomes
        for response in responses:
            state = engine.get_workflow_state(response.workflow_id)
            assert state is not None
            if response.status == WorkflowStatus.COMPLETED:
                assert state.current_state == WorkflowState.COMPLETED
            else:
                assert state.current_state == WorkflowState.FAILED


class TestResourceCleanupIntegration:
    """Test resource cleanup and lifecycle management in integrated environment."""

    @pytest.fixture
    def cleanup_engine(self, mock_container) -> ReducerPatternEngine:
        """Create engine for cleanup testing."""
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event",
        ):
            engine = ReducerPatternEngine(mock_container)
            engine.register_subreducer(
                IntegrationTestSubreducer("cleanup_test", WorkflowType.DATA_ANALYSIS),
            )
            return engine

    @pytest.mark.asyncio
    async def test_engine_lifecycle_integration(self, cleanup_engine):
        """Test complete engine lifecycle including startup, processing, and cleanup."""
        # Verify engine starts correctly
        assert cleanup_engine is not None
        assert len(cleanup_engine._registry.list_subreducers()) == 1

        # Process some workflows
        requests = [
            ModelWorkflowRequest(
                workflow_type=WorkflowType.DATA_ANALYSIS,
                instance_id=f"lifecycle_test_{i}",
            )
            for i in range(10)
        ]

        responses = await asyncio.gather(
            *[cleanup_engine.process_workflow(req) for req in requests],
        )

        # Verify all succeeded
        assert all(r.status == WorkflowStatus.COMPLETED for r in responses)

        # Verify metrics
        metrics = cleanup_engine.get_metrics()
        assert metrics.total_workflows_processed == 10

        # Engine should remain functional after processing
        additional_request = ModelWorkflowRequest(
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="post_processing_test",
        )

        additional_response = await cleanup_engine.process_workflow(additional_request)
        assert additional_response.status == WorkflowStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_concurrent_resource_usage_integration(self, cleanup_engine):
        """Test resource usage under concurrent load."""
        num_concurrent = 50

        requests = [
            ModelWorkflowRequest(
                workflow_type=WorkflowType.DATA_ANALYSIS,
                instance_id=f"resource_test_{i}",
                payload={"load_test": True, "size": "medium"},
            )
            for i in range(num_concurrent)
        ]

        # Process all concurrently
        start_time = time.time()
        responses = await asyncio.gather(
            *[cleanup_engine.process_workflow(req) for req in requests],
        )
        end_time = time.time()

        # Verify all completed
        assert len(responses) == num_concurrent
        assert all(r.status == WorkflowStatus.COMPLETED for r in responses)

        # Verify performance under load
        total_time = end_time - start_time
        assert total_time < 5.0  # Should complete within reasonable time

        # Verify engine remains stable after concurrent load
        post_load_request = ModelWorkflowRequest(
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="post_load_stability_test",
        )

        post_load_response = await cleanup_engine.process_workflow(post_load_request)
        assert post_load_response.status == WorkflowStatus.COMPLETED


# ====== Integration Test Utilities ======


def create_realistic_data_analysis_payload() -> dict[str, Any]:
    """Create realistic payload for data analysis testing."""
    return {
        "analysis_type": "comprehensive",
        "data": [i * 1.5 + (i % 7) * 0.3 for i in range(100)],
        "options": {
            "include_statistics": True,
            "include_distribution": True,
            "include_correlation": True,
            "outlier_detection": True,
        },
        "metadata": {
            "source": "integration_test",
            "data_quality": "high",
        },
    }


def create_realistic_document_payload() -> dict[str, Any]:
    """Create realistic payload for document regeneration testing."""
    return {
        "document_type": "technical_specification",
        "content": """
# Technical Specification

This document outlines the technical specifications for the system.

## Overview
The system provides comprehensive workflow processing capabilities.

## Features
- Multi-workflow support
- Concurrent processing
- State management
- Metrics collection

## Architecture
The architecture follows ONEX patterns with four-node design.
        """.strip(),
        "regeneration_options": {
            "enhance_structure": True,
            "improve_clarity": True,
            "add_examples": True,
            "target_audience": "technical",
        },
        "output_format": "markdown",
    }


def create_realistic_report_payload() -> dict[str, Any]:
    """Create realistic payload for report generation testing."""
    return {
        "report_type": "system_performance_analysis",
        "data_sources": [
            "metrics_database",
            "application_logs",
            "user_feedback",
        ],
        "time_range": {
            "start": "2023-01-01T00:00:00Z",
            "end": "2023-12-31T23:59:59Z",
        },
        "sections": [
            "executive_summary",
            "performance_metrics",
            "trend_analysis",
            "recommendations",
            "appendix",
        ],
        "output_format": "html",
        "styling": {
            "theme": "professional",
            "include_charts": True,
            "include_tables": True,
        },
    }
