"""
Unit tests for WorkflowRouter.

Tests the router functionality including subreducer registration,
workflow routing decisions, hash-based routing, and error handling.
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.contracts import (
    BaseSubreducer,
    RoutingDecision,
    SubreducerResult,
    WorkflowRequest,
    WorkflowType,
)
from omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router import WorkflowRouter


class MockSubreducer(BaseSubreducer):
    """Mock subreducer for testing."""

    def __init__(self, name: str = "test_subreducer"):
        super().__init__(name)

    def supports_workflow_type(self, workflow_type: WorkflowType) -> bool:
        return workflow_type == WorkflowType.DOCUMENT_REGENERATION

    async def process(self, request: WorkflowRequest) -> SubreducerResult:
        return SubreducerResult(
            workflow_id=request.workflow_id,
            subreducer_name=self.name,
            success=True,
            result={"test": "success"},
            processing_time_ms=10.0,
        )


class InvalidSubreducer:
    """Invalid subreducer class for testing validation."""

    def __init__(self, name: str = "invalid_subreducer"):
        self.name = name


@pytest.fixture
def router():
    """Create a WorkflowRouter instance for testing."""
    with patch(
        "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
    ):
        return WorkflowRouter()


@pytest.fixture
def sample_workflow_request():
    """Create a sample workflow request for testing."""
    return WorkflowRequest(
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


class TestWorkflowRouterInitialization:
    """Test router initialization."""

    def test_router_initialization(self):
        """Test that router initializes correctly."""
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
        ):
            router = WorkflowRouter()

            assert router is not None
            assert router._subreducers == {}
            assert router._workflow_type_mappings == {}
            assert "total_routed" in router._routing_metrics
            assert "routing_errors" in router._routing_metrics
            assert "average_routing_time_ms" in router._routing_metrics
            assert router._routing_metrics["total_routed"] == 0
            assert router._routing_metrics["routing_errors"] == 0
            assert router._routing_metrics["average_routing_time_ms"] == 0.0


class TestSubreducerRegistration:
    """Test subreducer registration functionality."""

    def test_register_subreducer_success(self, router):
        """Test successful subreducer registration."""
        subreducer = MockSubreducer("doc_regeneration_subreducer")
        workflow_types = [WorkflowType.DOCUMENT_REGENERATION]

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
        ):
            router.register_subreducer(subreducer, workflow_types)

        # Verify subreducer is registered
        assert "doc_regeneration_subreducer" in router._subreducers
        assert router._subreducers["doc_regeneration_subreducer"] is subreducer

        # Verify workflow type mapping
        assert WorkflowType.DOCUMENT_REGENERATION in router._workflow_type_mappings
        assert (
            router._workflow_type_mappings[WorkflowType.DOCUMENT_REGENERATION]
            == "doc_regeneration_subreducer"
        )

        # Verify we can get the subreducer
        retrieved_subreducer = router.get_subreducer("doc_regeneration_subreducer")
        assert retrieved_subreducer is subreducer

    def test_register_subreducer_invalid_type(self, router):
        """Test registration with invalid subreducer type."""
        invalid_subreducer = InvalidSubreducer("invalid_subreducer")
        workflow_types = [WorkflowType.DOCUMENT_REGENERATION]

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
        ):
            with pytest.raises(OnexError) as exc_info:
                router.register_subreducer(invalid_subreducer, workflow_types)

            assert exc_info.value.error_code == CoreErrorCode.VALIDATION_ERROR
            assert "Invalid subreducer type" in str(exc_info.value)

    def test_register_duplicate_workflow_type(self, router):
        """Test registration of duplicate workflow type."""
        subreducer1 = MockSubreducer("subreducer1")
        subreducer2 = MockSubreducer("subreducer2")
        workflow_types = [WorkflowType.DOCUMENT_REGENERATION]

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
        ):
            # Register first subreducer
            router.register_subreducer(subreducer1, workflow_types)

            # Try to register second subreducer for same workflow type
            with pytest.raises(OnexError) as exc_info:
                router.register_subreducer(subreducer2, workflow_types)

            assert exc_info.value.error_code == CoreErrorCode.VALIDATION_ERROR
            assert "already registered" in str(exc_info.value)

    def test_register_subreducer_multiple_workflow_types(self, router):
        """Test registration with multiple workflow types (future-proofing)."""
        subreducer = MockSubreducer("multi_subreducer")
        # Currently only one type supported, but test the pattern
        workflow_types = [WorkflowType.DOCUMENT_REGENERATION]

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
        ):
            router.register_subreducer(subreducer, workflow_types)

        # Verify all workflow types are mapped
        for workflow_type in workflow_types:
            assert workflow_type in router._workflow_type_mappings
            assert router._workflow_type_mappings[workflow_type] == "multi_subreducer"

    def test_get_subreducer_not_found(self, router):
        """Test getting a subreducer that doesn't exist."""
        result = router.get_subreducer("nonexistent_subreducer")
        assert result is None


class TestWorkflowRouting:
    """Test workflow routing functionality."""

    @pytest.mark.asyncio
    async def test_successful_routing(self, router, sample_workflow_request):
        """Test successful workflow routing."""
        # Register a subreducer
        subreducer = MockSubreducer("doc_regeneration_subreducer")
        workflow_types = [WorkflowType.DOCUMENT_REGENERATION]

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
        ):
            router.register_subreducer(subreducer, workflow_types)

            # Route the workflow
            decision = await router.route(sample_workflow_request)

        # Verify routing decision
        assert isinstance(decision, RoutingDecision)
        assert decision.workflow_id == sample_workflow_request.workflow_id
        assert decision.workflow_type == sample_workflow_request.workflow_type
        assert decision.instance_id == sample_workflow_request.instance_id
        assert decision.subreducer_name == "doc_regeneration_subreducer"
        assert isinstance(decision.routing_hash, str)
        assert len(decision.routing_hash) == 16  # SHA-256 truncated to 16 chars

        # Verify routing metadata
        assert "correlation_id" in decision.routing_metadata
        assert "routing_algorithm" in decision.routing_metadata
        assert "total_subreducers" in decision.routing_metadata
        assert decision.routing_metadata["correlation_id"] == str(
            sample_workflow_request.correlation_id
        )
        assert decision.routing_metadata["routing_algorithm"] == "hash_based"
        assert decision.routing_metadata["total_subreducers"] == 1

    @pytest.mark.asyncio
    async def test_routing_unsupported_workflow_type(
        self, router, sample_workflow_request
    ):
        """Test routing with unsupported workflow type."""
        # Don't register any subreducers

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
        ):
            with pytest.raises(OnexError) as exc_info:
                await router.route(sample_workflow_request)

            assert exc_info.value.error_code == CoreErrorCode.VALIDATION_ERROR
            assert "Unsupported workflow type" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_routing_hash_consistency(self, router, sample_workflow_request):
        """Test that routing hash is consistent for same inputs."""
        # Register a subreducer
        subreducer = MockSubreducer("doc_regeneration_subreducer")
        workflow_types = [WorkflowType.DOCUMENT_REGENERATION]

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
        ):
            router.register_subreducer(subreducer, workflow_types)

            # Route the same workflow multiple times
            decision1 = await router.route(sample_workflow_request)
            decision2 = await router.route(sample_workflow_request)

        # Hash should be consistent
        assert decision1.routing_hash == decision2.routing_hash

    @pytest.mark.asyncio
    async def test_routing_hash_different_instances(self, router):
        """Test that different instances get different hashes."""
        # Register a subreducer
        subreducer = MockSubreducer("doc_regeneration_subreducer")
        workflow_types = [WorkflowType.DOCUMENT_REGENERATION]

        # Create requests with different instance IDs
        request1 = WorkflowRequest(
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,
            instance_id="instance_1",
            payload={"document_id": "doc_123"},
        )

        request2 = WorkflowRequest(
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,
            instance_id="instance_2",
            payload={"document_id": "doc_123"},
        )

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
        ):
            router.register_subreducer(subreducer, workflow_types)

            # Route both workflows
            decision1 = await router.route(request1)
            decision2 = await router.route(request2)

        # Hashes should be different
        assert decision1.routing_hash != decision2.routing_hash

    @pytest.mark.asyncio
    async def test_routing_updates_metrics(self, router, sample_workflow_request):
        """Test that routing updates performance metrics."""
        # Register a subreducer
        subreducer = MockSubreducer("doc_regeneration_subreducer")
        workflow_types = [WorkflowType.DOCUMENT_REGENERATION]

        # Get initial metrics
        initial_metrics = router.get_routing_metrics()
        assert initial_metrics["total_routed"] == 0
        assert initial_metrics["routing_errors"] == 0
        assert initial_metrics["average_routing_time_ms"] == 0.0

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
        ):
            router.register_subreducer(subreducer, workflow_types)

            # Route a workflow
            await router.route(sample_workflow_request)

        # Check updated metrics
        updated_metrics = router.get_routing_metrics()
        assert updated_metrics["total_routed"] == 1
        assert updated_metrics["routing_errors"] == 0
        assert updated_metrics["average_routing_time_ms"] > 0.0

    @pytest.mark.asyncio
    async def test_routing_error_updates_metrics(self, router, sample_workflow_request):
        """Test that routing errors update metrics."""
        # Don't register any subreducers to cause error
        initial_metrics = router.get_routing_metrics()

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
        ):
            with pytest.raises(OnexError):
                await router.route(sample_workflow_request)

        # Check error metrics
        updated_metrics = router.get_routing_metrics()
        assert (
            updated_metrics["routing_errors"] == initial_metrics["routing_errors"] + 1
        )


class TestRoutingMetrics:
    """Test routing metrics functionality."""

    def test_get_routing_metrics_returns_copy(self, router):
        """Test that get_routing_metrics returns a copy to prevent external modification."""
        metrics = router.get_routing_metrics()
        original_total = metrics["total_routed"]

        # Modify the returned metrics
        metrics["total_routed"] = 999

        # Get metrics again
        fresh_metrics = router.get_routing_metrics()
        assert fresh_metrics["total_routed"] == original_total

    @pytest.mark.asyncio
    async def test_routing_metrics_average_calculation(self, router):
        """Test that average routing time is calculated correctly."""
        subreducer = MockSubreducer("doc_regeneration_subreducer")
        workflow_types = [WorkflowType.DOCUMENT_REGENERATION]

        requests = [
            WorkflowRequest(
                workflow_type=WorkflowType.DOCUMENT_REGENERATION,
                instance_id=f"instance_{i}",
                payload={"document_id": f"doc_{i}"},
            )
            for i in range(3)
        ]

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
        ):
            router.register_subreducer(subreducer, workflow_types)

            # Route multiple workflows
            for request in requests:
                await router.route(request)

        # Check that average is reasonable
        metrics = router.get_routing_metrics()
        assert metrics["total_routed"] == 3
        assert metrics["average_routing_time_ms"] > 0.0
        # Average should be less than individual routing times (which are very small)
        assert (
            metrics["average_routing_time_ms"] < 100.0
        )  # Should be much less than 100ms


class TestRoutingHashGeneration:
    """Test routing hash generation functionality."""

    def test_generate_routing_hash(self, router):
        """Test routing hash generation."""
        # Use the private method for direct testing
        hash1 = router._generate_routing_hash("document_regeneration", "instance_1")
        hash2 = router._generate_routing_hash("document_regeneration", "instance_1")
        hash3 = router._generate_routing_hash("document_regeneration", "instance_2")

        # Same inputs should produce same hash
        assert hash1 == hash2
        assert isinstance(hash1, str)
        assert len(hash1) == 16

        # Different inputs should produce different hash
        assert hash1 != hash3

    def test_routing_hash_format(self, router):
        """Test routing hash format and characteristics."""
        hash_value = router._generate_routing_hash("test_type", "test_instance")

        # Should be hex string
        assert isinstance(hash_value, str)
        assert len(hash_value) == 16
        assert all(c in "0123456789abcdef" for c in hash_value)


class TestErrorHandling:
    """Test error handling in router."""

    @pytest.mark.asyncio
    async def test_routing_with_exception_during_processing(
        self, router, sample_workflow_request
    ):
        """Test handling of exceptions during routing process."""
        subreducer = MockSubreducer("doc_regeneration_subreducer")
        workflow_types = [WorkflowType.DOCUMENT_REGENERATION]

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
        ):
            router.register_subreducer(subreducer, workflow_types)

            # Mock _generate_routing_hash to raise an exception
            with patch.object(
                router,
                "_generate_routing_hash",
                side_effect=Exception("Hash generation failed"),
            ):
                with pytest.raises(Exception) as exc_info:
                    await router.route(sample_workflow_request)

                assert "Hash generation failed" in str(exc_info.value)

                # Check that error metrics were updated
                metrics = router.get_routing_metrics()
                assert metrics["routing_errors"] == 1

    def test_registration_error_logging(self, router):
        """Test that registration errors are properly logged."""
        invalid_subreducer = InvalidSubreducer("invalid")
        workflow_types = [WorkflowType.DOCUMENT_REGENERATION]

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
        ) as mock_log:
            with pytest.raises(OnexError):
                router.register_subreducer(invalid_subreducer, workflow_types)

            # Check that error logging was called
            error_calls = [
                call
                for call in mock_log.call_args_list
                if "registration_failed" in str(call)
            ]
            assert len(error_calls) > 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_subreducer_name(self, router):
        """Test handling of empty subreducer name."""
        subreducer = MockSubreducer("")
        workflow_types = [WorkflowType.DOCUMENT_REGENERATION]

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
        ):
            # Should still work with empty name
            router.register_subreducer(subreducer, workflow_types)

            # Should be able to retrieve by empty name
            retrieved = router.get_subreducer("")
            assert retrieved is subreducer

    def test_register_subreducer_empty_workflow_types(self, router):
        """Test registering subreducer with empty workflow types list."""
        subreducer = MockSubreducer("test_subreducer")
        workflow_types = []

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
        ):
            # Should succeed but not map any workflow types
            router.register_subreducer(subreducer, workflow_types)

            # Subreducer should be registered but no workflow type mappings
            assert "test_subreducer" in router._subreducers
            assert len(router._workflow_type_mappings) == 0

    @pytest.mark.asyncio
    async def test_routing_with_empty_instance_id(self, router):
        """Test routing with empty instance ID."""
        subreducer = MockSubreducer("doc_regeneration_subreducer")
        workflow_types = [WorkflowType.DOCUMENT_REGENERATION]

        request = WorkflowRequest(
            workflow_type=WorkflowType.DOCUMENT_REGENERATION,
            instance_id="",  # Empty instance ID
            payload={"document_id": "doc_123"},
        )

        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
        ):
            router.register_subreducer(subreducer, workflow_types)

            # Should still work with empty instance ID
            decision = await router.route(request)

            assert decision.instance_id == ""
            assert isinstance(decision.routing_hash, str)
            assert len(decision.routing_hash) == 16
