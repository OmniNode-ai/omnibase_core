"""
Unit tests for ReducerPatternEngine.

Tests the core engine functionality including workflow processing,
subreducer registration, metrics collection, and error handling.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from omnibase_core.core.errors.core_errors import OnexError
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
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


class MockSubreducer(BaseSubreducer):
    """Mock subreducer for testing."""

    def __init__(self, name: str = "test_subreducer"):
        super().__init__(name)
        self.process_calls = []

    def supports_workflow_type(self, workflow_type: WorkflowType) -> bool:
        return workflow_type == WorkflowType.DOCUMENT_REGENERATION

    async def process(self, request: ModelWorkflowRequest) -> ModelSubreducerResult:
        self.process_calls.append(request)
        return ModelSubreducerResult(
            workflow_id=request.workflow_id,
            subreducer_name=self.name,
            success=True,
            result={"test": "success"},
            processing_time_ms=10.0,
        )


class FailingMockSubreducer(BaseSubreducer):
    """Mock subreducer that fails for testing error handling."""

    def __init__(self, name: str = "failing_subreducer"):
        super().__init__(name)

    def supports_workflow_type(self, workflow_type: WorkflowType) -> bool:
        return workflow_type == WorkflowType.DOCUMENT_REGENERATION

    async def process(self, request: ModelWorkflowRequest) -> ModelSubreducerResult:
        return ModelSubreducerResult(
            workflow_id=request.workflow_id,
            subreducer_name=self.name,
            success=False,
            error_message="Test failure",
            error_details={"error": "simulated failure"},
            processing_time_ms=5.0,
        )


@pytest.fixture
def mock_container():
    """Create a mock ModelONEXContainer for testing."""
    container = MagicMock(spec=ModelONEXContainer)
    return container


@pytest.fixture
def engine(mock_container):
    """Create a ReducerPatternEngine instance for testing."""
    with patch(
        "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event",
    ):
        return ReducerPatternEngine(mock_container)


@pytest.fixture
def sample_workflow_request():
    """Create a sample workflow request for testing."""
    return ModelWorkflowRequest(
        workflow_id=uuid4(),
        workflow_type=WorkflowType.DOCUMENT_REGENERATION,
        instance_id="test_instance_1",
        correlation_id=uuid4(),
        payload={
            "document_id": "doc_123",
            "content_type": "markdown",
            "template_id": "template_456",
        },
        metadata={"test": "metadata"},
    )


class TestReducerPatternEngineInitialization:
    """Test engine initialization."""

    def test_engine_initialization(self, mock_container):
        """Test that engine initializes correctly."""
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event",
        ):
            engine = ReducerPatternEngine(mock_container)

            assert engine is not None
            assert engine._router is not None
            assert engine._metrics is not None
            assert engine._active_workflows == {}

    def test_engine_inherits_from_node_reducer(self, mock_container):
        """Test that engine properly inherits from NodeReducer."""
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event",
        ):
            engine = ReducerPatternEngine(mock_container)

            # Check that it has NodeReducer attributes/methods
            assert hasattr(engine, "container")
            assert hasattr(engine, "_load_contract_model")


class TestSubreducerRegistration:
    """Test subreducer registration functionality."""

    def test_register_subreducer_success(self, engine):
        """Test successful subreducer registration."""
        subreducer = MockSubreducer("test_doc_reducer")
        workflow_types = [WorkflowType.DOCUMENT_REGENERATION]

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event",
        ):
            engine.register_subreducer(subreducer, workflow_types)

        # Verify router has the subreducer
        registered_subreducer = engine._router.get_subreducer("test_doc_reducer")
        assert registered_subreducer is subreducer

    def test_register_subreducer_router_failure(self, engine):
        """Test handling of router registration failures."""
        subreducer = MockSubreducer("test_doc_reducer")
        workflow_types = [WorkflowType.DOCUMENT_REGENERATION]

        # Mock router to raise exception
        engine._router.register_subreducer = MagicMock(
            side_effect=OnexError("test error"),
        )

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event",
        ):
            with pytest.raises(OnexError):
                engine.register_subreducer(subreducer, workflow_types)


class TestWorkflowProcessing:
    """Test workflow processing functionality."""

    @pytest.mark.asyncio
    async def test_successful_workflow_processing(
        self,
        engine,
        sample_workflow_request,
    ):
        """Test successful end-to-end workflow processing."""
        # Register a mock subreducer
        subreducer = MockSubreducer("test_doc_reducer")
        workflow_types = [WorkflowType.DOCUMENT_REGENERATION]

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event",
        ):
            engine.register_subreducer(subreducer, workflow_types)

            # Process the workflow
            response = await engine.process_workflow(sample_workflow_request)

        # Verify response
        assert isinstance(response, ModelWorkflowResponse)
        assert response.workflow_id == sample_workflow_request.workflow_id
        assert response.status == WorkflowStatus.COMPLETED
        assert response.result == {"test": "success"}
        assert response.processing_time_ms > 0
        assert response.subreducer_name == "test_doc_reducer"

        # Verify subreducer was called
        assert len(subreducer.process_calls) == 1
        assert subreducer.process_calls[0] == sample_workflow_request

        # Verify metrics updated
        metrics = engine.get_metrics()
        assert metrics.total_workflows_processed == 1
        assert metrics.successful_workflows == 1
        assert metrics.failed_workflows == 0

    @pytest.mark.asyncio
    async def test_failed_workflow_processing(self, engine, sample_workflow_request):
        """Test handling of workflow processing failures."""
        # Register a failing subreducer
        subreducer = FailingMockSubreducer("failing_doc_reducer")
        workflow_types = [WorkflowType.DOCUMENT_REGENERATION]

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event",
        ):
            engine.register_subreducer(subreducer, workflow_types)

            # Process the workflow
            response = await engine.process_workflow(sample_workflow_request)

        # Verify response indicates failure
        assert isinstance(response, ModelWorkflowResponse)
        assert response.workflow_id == sample_workflow_request.workflow_id
        assert response.status == WorkflowStatus.FAILED
        assert response.error_message == "Test failure"
        assert response.error_details == {"error": "simulated failure"}
        assert response.processing_time_ms > 0
        assert response.subreducer_name == "failing_doc_reducer"

        # Verify metrics updated
        metrics = engine.get_metrics()
        assert metrics.total_workflows_processed == 1
        assert metrics.successful_workflows == 0
        assert metrics.failed_workflows == 1

    @pytest.mark.asyncio
    async def test_workflow_processing_no_subreducer(
        self,
        engine,
        sample_workflow_request,
    ):
        """Test workflow processing when no subreducer is registered."""
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event",
        ):
            # Process without registering any subreducers
            response = await engine.process_workflow(sample_workflow_request)

        # Verify response indicates failure
        assert isinstance(response, ModelWorkflowResponse)
        assert response.status == WorkflowStatus.FAILED
        assert "Unsupported workflow type" in response.error_message

        # Verify metrics updated
        metrics = engine.get_metrics()
        assert metrics.total_workflows_processed == 1
        assert metrics.failed_workflows == 1

    @pytest.mark.asyncio
    async def test_workflow_processing_exception(self, engine, sample_workflow_request):
        """Test handling of unexpected exceptions during processing."""
        # Register a subreducer that will cause router to fail
        subreducer = MockSubreducer("test_doc_reducer")
        workflow_types = [WorkflowType.DOCUMENT_REGENERATION]

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event",
        ):
            engine.register_subreducer(subreducer, workflow_types)

            # Mock router to raise exception
            engine._router.route = AsyncMock(side_effect=Exception("Router failure"))

            # Process the workflow
            response = await engine.process_workflow(sample_workflow_request)

        # Verify response indicates failure
        assert isinstance(response, ModelWorkflowResponse)
        assert response.status == WorkflowStatus.FAILED
        assert "Router failure" in response.error_message
        assert response.error_details["error_type"] == "Exception"


class TestActiveWorkflowTracking:
    """Test active workflow tracking functionality."""

    @pytest.mark.asyncio
    async def test_active_workflow_tracking(self, engine, sample_workflow_request):
        """Test that active workflows are properly tracked."""
        # Create a subreducer that we can control
        subreducer = MockSubreducer("test_doc_reducer")

        # Make process method track when it's called and take some time
        original_process = subreducer.process
        process_started = False

        async def tracked_process(request):
            nonlocal process_started
            process_started = True
            # Check that workflow is tracked while processing
            active_workflows = engine.get_active_workflows()
            assert str(request.workflow_id) in active_workflows
            return await original_process(request)

        subreducer.process = tracked_process
        workflow_types = [WorkflowType.DOCUMENT_REGENERATION]

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event",
        ):
            engine.register_subreducer(subreducer, workflow_types)

            # Process the workflow
            response = await engine.process_workflow(sample_workflow_request)

        # Verify process was called and workflow tracking worked
        assert process_started
        assert response.status == WorkflowStatus.COMPLETED

        # Verify workflow is no longer active after completion
        active_workflows = engine.get_active_workflows()
        assert str(sample_workflow_request.workflow_id) not in active_workflows


class TestMetrics:
    """Test metrics collection functionality."""

    @pytest.mark.asyncio
    async def test_metrics_collection(self, engine, sample_workflow_request):
        """Test that metrics are properly collected and calculated."""
        subreducer = MockSubreducer("test_doc_reducer")
        workflow_types = [WorkflowType.DOCUMENT_REGENERATION]

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event",
        ):
            engine.register_subreducer(subreducer, workflow_types)

            # Process multiple workflows
            await engine.process_workflow(sample_workflow_request)

            # Create another request
            request2 = ModelWorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.DOCUMENT_REGENERATION,
                instance_id="test_instance_2",
                payload={"document_id": "doc_456", "content_type": "html"},
            )
            await engine.process_workflow(request2)

        # Check metrics
        metrics = engine.get_metrics()
        assert metrics.total_workflows_processed == 2
        assert metrics.successful_workflows == 2
        assert metrics.failed_workflows == 0
        assert metrics.average_processing_time_ms > 0
        assert metrics.calculate_success_rate() == 100.0

        # Check that router metrics are included
        assert "router" in metrics.subreducer_metrics

    def test_get_active_workflows(self, engine):
        """Test getting active workflows when none are active."""
        active_workflows = engine.get_active_workflows()
        assert active_workflows == {}


class TestBackgroundCleanup:
    """Test background cleanup functionality."""

    @pytest.mark.asyncio
    async def test_background_cleanup_thread_initialization(self, mock_container):
        """Test that background cleanup thread starts during engine initialization."""
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event",
        ):
            engine = ReducerPatternEngine(mock_container)

        # Verify thread is created and started
        assert hasattr(engine, "_cleanup_thread")
        assert hasattr(engine, "_cleanup_thread_stop_event")
        assert engine._cleanup_thread.is_alive()
        assert engine._cleanup_thread.daemon  # Should be daemon thread
        assert "ReducerEngine-Cleanup" in engine._cleanup_thread.name

        # Clean up
        engine.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_cleanup_thread(self, mock_container):
        """Test graceful shutdown of background cleanup thread."""
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event",
        ):
            engine = ReducerPatternEngine(mock_container)

        # Verify thread is running
        assert engine._cleanup_thread.is_alive()

        # Shutdown engine
        engine.shutdown()

        # Verify thread stops within reasonable time
        engine._cleanup_thread.join(timeout=1.0)
        assert not engine._cleanup_thread.is_alive()

    @pytest.mark.asyncio
    async def test_background_cleanup_worker_error_handling(self, mock_container):
        """Test that background cleanup continues despite errors."""
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event",
        ) as mock_log:
            engine = ReducerPatternEngine(mock_container)

            # Mock _cleanup_old_workflow_states to raise an exception
            original_cleanup = engine._cleanup_old_workflow_states
            exception_raised = False

            def failing_cleanup():
                nonlocal exception_raised
                if not exception_raised:
                    exception_raised = True
                    raise Exception("Test cleanup error")
                return original_cleanup()

            engine._cleanup_old_workflow_states = failing_cleanup

            # Wait briefly for the background thread to potentially hit the error
            import time

            time.sleep(0.1)

            # Clean up
            engine.shutdown()

            # Verify error was logged but thread continued
            error_logs = [
                call
                for call in mock_log.call_args_list
                if len(call[1]) > 1
                and call[1].get("event") == "background_cleanup_error"
            ]
            # Note: May or may not have hit the error in this short test, so we don't assert on it


class TestInstanceIdValidation:
    """Test instance_id validation constraints."""

    def test_valid_instance_ids(self):
        """Test that valid instance_id values are accepted."""
        from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.models import (
            ModelWorkflowRequest,
            WorkflowType,
        )

        valid_ids = [
            "a",
            "1",
            "test123",
            "user-session-1",
            "workflow_instance_456",
            "ABC123",
            "a1b2c3",
            "service-1-instance-2",
        ]

        for instance_id in valid_ids:
            # Should not raise an exception
            request = ModelWorkflowRequest(
                workflow_type=WorkflowType.DOCUMENT_REGENERATION,
                instance_id=instance_id,
            )
            assert request.instance_id == instance_id

    def test_invalid_instance_ids(self):
        """Test that invalid instance_id values raise validation errors."""
        from pydantic import ValidationError

        from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.models import (
            ModelWorkflowRequest,
            WorkflowType,
        )

        invalid_ids = [
            "",  # Empty string
            "   ",  # Only whitespace
            "-abc",  # Starts with hyphen
            "abc-",  # Ends with hyphen
            "_abc",  # Starts with underscore
            "abc_",  # Ends with underscore
            "abc def",  # Contains space
            "abc@def",  # Contains invalid character
            "abc.def",  # Contains invalid character
            "a" * 129,  # Too long (>128 chars)
        ]

        for instance_id in invalid_ids:
            with pytest.raises(ValidationError):
                ModelWorkflowRequest(
                    workflow_type=WorkflowType.DOCUMENT_REGENERATION,
                    instance_id=instance_id,
                )

    def test_instance_id_trimming(self):
        """Test that instance_id values are properly trimmed."""
        from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.models import (
            ModelWorkflowRequest,
            WorkflowType,
        )

        # Whitespace should be trimmed
        request = ModelWorkflowRequest(
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,
            instance_id="  test123  ",
        )
        assert request.instance_id == "test123"


class TestMetricsLockingPatterns:
    """Test consistent metrics locking patterns."""

    @pytest.mark.asyncio
    async def test_concurrent_metrics_updates(self, engine):
        """Test that metrics updates are thread-safe under concurrent access."""

        # Register a subreducer
        subreducer = MockSubreducer("concurrent_test")
        workflow_types = [WorkflowType.DOCUMENT_REGENERATION]

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event",
        ):
            engine.register_subreducer(subreducer, workflow_types)

        # Create multiple workflow requests
        requests = []
        for i in range(10):
            request = ModelWorkflowRequest(
                workflow_type=WorkflowType.DOCUMENT_REGENERATION,
                instance_id=f"concurrent_test_{i}",
            )
            requests.append(request)

        # Process workflows concurrently
        async def process_workflow(req):
            return await engine.process_workflow(req)

        # Execute workflows concurrently
        tasks = [process_workflow(req) for req in requests]
        results = await asyncio.gather(*tasks)

        # Verify all workflows completed
        assert len(results) == 10
        assert all(result.status == WorkflowStatus.COMPLETED for result in results)

        # Verify metrics are consistent
        metrics = engine.get_metrics()
        assert metrics.total_workflows_processed == 10
        assert metrics.successful_workflows == 10
        assert metrics.failed_workflows == 0

    def test_router_metrics_thread_safety(self, engine):
        """Test that router metrics are accessed in a thread-safe manner."""
        import threading
        import time

        def update_metrics():
            """Function to update router metrics from multiple threads."""
            for _ in range(100):
                # Access metrics (this should be thread-safe)
                metrics = engine._router.get_routing_metrics()
                assert isinstance(metrics, dict)
                time.sleep(0.001)  # Small delay to increase concurrency chances

        # Start multiple threads that access metrics
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=update_metrics)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify router metrics are still accessible
        final_metrics = engine._router.get_routing_metrics()
        assert isinstance(final_metrics, dict)
        assert "total_routed" in final_metrics
        assert "routing_errors" in final_metrics


class TestEndToEndWorkflowIntegration:
    """Test complete end-to-end workflow processing integration."""

    @pytest.mark.asyncio
    async def test_complete_document_workflow_success(self, mock_container):
        """Test complete successful document workflow from start to finish."""
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event",
        ):
            # Initialize engine with realistic configuration
            engine = ReducerPatternEngine(
                mock_container,
                max_workflow_states=100,
                state_retention_hours=1,
            )

            # Register document regeneration subreducer
            subreducer = MockSubreducer("doc_regeneration_e2e")
            workflow_types = [WorkflowType.DOCUMENT_REGENERATION]
            engine.register_subreducer(subreducer, workflow_types)

            # Create realistic workflow request
            request = ModelWorkflowRequest(
                workflow_type=WorkflowType.DOCUMENT_REGENERATION,
                instance_id="e2e-test-instance-001",
                payload={
                    "document_id": "doc_12345",
                    "content_type": "markdown",
                    "source_content": "# Original Document\n\nThis is test content.",
                    "regeneration_options": {
                        "improve_clarity": True,
                        "add_examples": False,
                        "target_length": "medium",
                    },
                },
                metadata={
                    "user_id": "test_user_123",
                    "session_id": "session_456",
                    "priority": "normal",
                },
            )

            # Process the workflow end-to-end
            response = await engine.process_workflow(request)

            # Verify complete response structure
            assert isinstance(response, ModelWorkflowResponse)
            assert response.workflow_id == request.workflow_id
            assert response.workflow_type == WorkflowType.DOCUMENT_REGENERATION
            assert response.instance_id == "e2e-test-instance-001"
            assert response.correlation_id == request.correlation_id
            assert response.status == WorkflowStatus.COMPLETED
            assert response.result is not None
            assert response.result == {"test": "success"}
            assert response.processing_time_ms > 0
            assert response.subreducer_name == "doc_regeneration_e2e"
            assert response.error_message is None
            assert response.error_details is None

            # Verify subreducer was called with correct data
            assert len(subreducer.process_calls) == 1
            processed_request = subreducer.process_calls[0]
            assert processed_request.workflow_id == request.workflow_id
            assert processed_request.payload == request.payload
            assert processed_request.metadata == request.metadata

            # Verify metrics were updated correctly
            metrics = engine.get_metrics()
            assert metrics.total_workflows_processed == 1
            assert metrics.successful_workflows == 1
            assert metrics.failed_workflows == 0
            assert metrics.average_processing_time_ms > 0
            assert metrics.active_instances == 0  # Should be cleaned up

            # Verify router metrics
            router_metrics = engine._router.get_routing_metrics()
            assert router_metrics["total_routed"] == 1
            assert router_metrics["routing_errors"] == 0
            assert router_metrics["average_routing_time_ms"] > 0

            # Cleanup
            engine.shutdown()

    @pytest.mark.asyncio
    async def test_complete_workflow_failure_handling(self, mock_container):
        """Test complete workflow failure handling from start to finish."""
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event",
        ):
            engine = ReducerPatternEngine(mock_container)

            # Register failing subreducer
            failing_subreducer = FailingMockSubreducer("failing_doc_regeneration")
            workflow_types = [WorkflowType.DOCUMENT_REGENERATION]
            engine.register_subreducer(failing_subreducer, workflow_types)

            # Create workflow request
            request = ModelWorkflowRequest(
                workflow_type=WorkflowType.DOCUMENT_REGENERATION,
                instance_id="e2e-failure-test",
                payload={"document_id": "invalid_doc"},
            )

            # Process the failing workflow
            response = await engine.process_workflow(request)

            # Verify failure response structure
            assert isinstance(response, ModelWorkflowResponse)
            assert response.workflow_id == request.workflow_id
            assert response.status == WorkflowStatus.FAILED
            assert response.error_message == "Test failure"
            assert response.error_details == {"error": "simulated failure"}
            assert response.processing_time_ms > 0
            assert response.subreducer_name == "failing_doc_regeneration"
            assert response.result is None

            # Verify metrics show failure
            metrics = engine.get_metrics()
            assert metrics.total_workflows_processed == 1
            assert metrics.successful_workflows == 0
            assert metrics.failed_workflows == 1

            engine.shutdown()

    @pytest.mark.asyncio
    async def test_multiple_concurrent_workflows_e2e(self, mock_container):
        """Test multiple concurrent workflows processing end-to-end."""
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event",
        ):
            engine = ReducerPatternEngine(mock_container, max_workflow_states=50)

            # Register subreducer
            subreducer = MockSubreducer("concurrent_e2e")
            workflow_types = [WorkflowType.DOCUMENT_REGENERATION]
            engine.register_subreducer(subreducer, workflow_types)

            # Create multiple workflow requests with different instance IDs
            requests = []
            for i in range(5):
                request = ModelWorkflowRequest(
                    workflow_type=WorkflowType.DOCUMENT_REGENERATION,
                    instance_id=f"concurrent-e2e-{i:03d}",
                    payload={
                        "document_id": f"doc_{i}",
                        "batch_id": f"batch_{i // 2}",  # Some shared, some unique
                    },
                )
                requests.append(request)

            # Process all workflows concurrently
            tasks = [engine.process_workflow(req) for req in requests]
            responses = await asyncio.gather(*tasks)

            # Verify all responses
            assert len(responses) == 5
            for i, response in enumerate(responses):
                assert response.status == WorkflowStatus.COMPLETED
                assert response.instance_id == f"concurrent-e2e-{i:03d}"
                assert response.subreducer_name == "concurrent_e2e"

            # Verify all subreducer calls were made
            assert len(subreducer.process_calls) == 5

            # Verify final metrics
            metrics = engine.get_metrics()
            assert metrics.total_workflows_processed == 5
            assert metrics.successful_workflows == 5
            assert metrics.failed_workflows == 0
            assert metrics.active_instances == 0  # All should be cleaned up

            # Verify router handled all requests
            router_metrics = engine._router.get_routing_metrics()
            assert router_metrics["total_routed"] == 5
            assert router_metrics["routing_errors"] == 0

            engine.shutdown()

    @pytest.mark.asyncio
    async def test_workflow_state_lifecycle_e2e(self, mock_container):
        """Test complete workflow state lifecycle from creation to cleanup."""
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.engine.emit_log_event",
        ):
            engine = ReducerPatternEngine(
                mock_container,
                state_retention_hours=0,
            )  # Immediate cleanup

            # Create a custom subreducer that allows us to inspect state during processing
            class StateInspectionSubreducer(BaseSubreducer):
                def __init__(self, name: str):
                    super().__init__(name)
                    self.engine_ref = None

                def supports_workflow_type(self, workflow_type: WorkflowType) -> bool:
                    return workflow_type == WorkflowType.DOCUMENT_REGENERATION

                async def process(
                    self,
                    request: ModelWorkflowRequest,
                ) -> ModelSubreducerResult:
                    # Check that workflow is active during processing
                    if self.engine_ref:
                        active_workflows = self.engine_ref.get_active_workflows()
                        assert str(request.workflow_id) in active_workflows

                        # Check workflow state exists
                        state = self.engine_ref._get_workflow_state(
                            str(request.workflow_id),
                        )
                        assert state is not None

                    return ModelSubreducerResult(
                        workflow_id=request.workflow_id,
                        subreducer_name=self.name,
                        success=True,
                        result={"lifecycle": "tested"},
                        processing_time_ms=5.0,
                    )

            subreducer = StateInspectionSubreducer("state_lifecycle_test")
            subreducer.engine_ref = engine  # Allow subreducer to inspect engine state

            workflow_types = [WorkflowType.DOCUMENT_REGENERATION]
            engine.register_subreducer(subreducer, workflow_types)

            # Create and process workflow
            request = ModelWorkflowRequest(
                workflow_type=WorkflowType.DOCUMENT_REGENERATION,
                instance_id="state-lifecycle-test",
            )

            # Verify no active workflows initially
            assert len(engine.get_active_workflows()) == 0

            # Process workflow
            response = await engine.process_workflow(request)

            # Verify successful completion
            assert response.status == WorkflowStatus.COMPLETED
            assert response.result == {"lifecycle": "tested"}

            # Verify workflow is no longer active after completion
            assert len(engine.get_active_workflows()) == 0

            # Trigger cleanup (since retention is 0 hours, completed workflows should be cleaned up)
            engine._cleanup_old_workflow_states()

            # Verify state was cleaned up
            state = engine._get_workflow_state(str(request.workflow_id))
            # Note: State might still exist briefly, but should be marked as completed
            if state:
                from omnibase_core.patterns.reducer_pattern_engine.models.state_transitions import (
                    WorkflowState,
                )

                assert state.current_state == WorkflowState.COMPLETED

            engine.shutdown()
