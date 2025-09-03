"""
Enhanced tests for WorkflowRouter with multi-workflow support.

Tests comprehensive routing functionality including hash-based routing,
multi-workflow type support, error handling, metrics collection,
and routing decision consistency for Phase 2 implementation.
"""

import asyncio
import hashlib
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

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


class MockRouterSubreducer(BaseSubreducer):
    """Mock subreducer for router testing with enhanced functionality."""

    def __init__(self, name: str, supported_types: List[WorkflowType]):
        super().__init__(name)
        self._supported_types = supported_types
        self._process_call_count = 0
        self._routing_calls = []

    def supports_workflow_type(self, workflow_type: WorkflowType) -> bool:
        return workflow_type in self._supported_types

    async def process(self, request: WorkflowRequest) -> SubreducerResult:
        """Mock processing that records routing information."""
        self._process_call_count += 1
        self._routing_calls.append(
            {
                "workflow_id": request.workflow_id,
                "workflow_type": request.workflow_type,
                "instance_id": request.instance_id,
                "correlation_id": request.correlation_id,
            }
        )

        return SubreducerResult(
            workflow_id=request.workflow_id,
            subreducer_name=self.name,
            success=True,
            result={
                "routed_successfully": True,
                "call_number": self._process_call_count,
            },
        )

    @property
    def routing_calls(self) -> List[Dict[str, Any]]:
        return self._routing_calls.copy()

    @property
    def process_call_count(self) -> int:
        return self._process_call_count


class TestWorkflowRouterEnhanced:
    """Enhanced test suite for WorkflowRouter with multi-workflow support."""

    @pytest.fixture
    def router(self) -> WorkflowRouter:
        """Create a WorkflowRouter instance for testing."""
        return WorkflowRouter()

    @pytest.fixture
    def mock_subreducers(self) -> Dict[str, MockRouterSubreducer]:
        """Create mock subreducers for different workflow types."""
        return {
            "data_analysis": MockRouterSubreducer(
                "data_analysis_subreducer", [WorkflowType.DATA_ANALYSIS]
            ),
            "report_generation": MockRouterSubreducer(
                "report_generation_subreducer", [WorkflowType.REPORT_GENERATION]
            ),
            "document_regeneration": MockRouterSubreducer(
                "document_regeneration_subreducer", [WorkflowType.DOCUMENT_REGENERATION]
            ),
            "multi_type": MockRouterSubreducer(
                "multi_type_subreducer",
                [WorkflowType.DATA_ANALYSIS, WorkflowType.REPORT_GENERATION],
            ),
        }

    @pytest.fixture
    def sample_requests(self) -> Dict[str, WorkflowRequest]:
        """Create sample workflow requests for different types."""
        base_correlation_id = uuid4()

        return {
            "data_analysis": WorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.DATA_ANALYSIS,
                instance_id="router-test-data-001",
                correlation_id=base_correlation_id,
                payload={"data": [1, 2, 3, 4, 5]},
            ),
            "report_generation": WorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.REPORT_GENERATION,
                instance_id="router-test-report-001",
                correlation_id=base_correlation_id,
                payload={"template_type": "summary", "output_format": "json"},
            ),
            "document_regeneration": WorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.DOCUMENT_REGENERATION,
                instance_id="router-test-doc-001",
                correlation_id=base_correlation_id,
                payload={"document_id": "test-doc-123"},
            ),
        }

    def test_router_initialization(self, router):
        """Test proper router initialization."""
        assert len(router._subreducers) == 0
        assert len(router._workflow_type_mappings) == 0

        # Initial metrics should be zero
        metrics = router.get_routing_metrics()
        assert metrics["total_routed"] == 0
        assert metrics["routing_errors"] == 0
        assert metrics["average_routing_time_ms"] == 0.0

    def test_register_single_workflow_type_subreducer(self, router, mock_subreducers):
        """Test registering subreducer for single workflow type."""
        subreducer = mock_subreducers["data_analysis"]
        router.register_subreducer(subreducer, [WorkflowType.DATA_ANALYSIS])

        # Verify registration
        assert len(router._subreducers) == 1
        assert subreducer.name in router._subreducers
        assert router._subreducers[subreducer.name] == subreducer

        # Verify workflow type mapping
        assert len(router._workflow_type_mappings) == 1
        assert WorkflowType.DATA_ANALYSIS in router._workflow_type_mappings
        assert (
            router._workflow_type_mappings[WorkflowType.DATA_ANALYSIS]
            == subreducer.name
        )

        # Test retrieval
        retrieved = router.get_subreducer(subreducer.name)
        assert retrieved == subreducer

    def test_register_multiple_workflow_type_subreducers(
        self, router, mock_subreducers
    ):
        """Test registering multiple subreducers for different workflow types."""
        subreducers_to_register = [
            (mock_subreducers["data_analysis"], [WorkflowType.DATA_ANALYSIS]),
            (mock_subreducers["report_generation"], [WorkflowType.REPORT_GENERATION]),
            (
                mock_subreducers["document_regeneration"],
                [WorkflowType.DOCUMENT_REGENERATION],
            ),
        ]

        for subreducer, workflow_types in subreducers_to_register:
            router.register_subreducer(subreducer, workflow_types)

        # Verify all registered
        assert len(router._subreducers) == 3
        assert len(router._workflow_type_mappings) == 3

        # Verify each workflow type maps correctly
        assert (
            router._workflow_type_mappings[WorkflowType.DATA_ANALYSIS]
            == "data_analysis_subreducer"
        )
        assert (
            router._workflow_type_mappings[WorkflowType.REPORT_GENERATION]
            == "report_generation_subreducer"
        )
        assert (
            router._workflow_type_mappings[WorkflowType.DOCUMENT_REGENERATION]
            == "document_regeneration_subreducer"
        )

    def test_register_multi_type_subreducer(self, router, mock_subreducers):
        """Test registering subreducer that supports multiple workflow types."""
        multi_subreducer = mock_subreducers["multi_type"]
        supported_types = [WorkflowType.DATA_ANALYSIS, WorkflowType.REPORT_GENERATION]

        router.register_subreducer(multi_subreducer, supported_types)

        # Verify registration
        assert len(router._subreducers) == 1
        assert len(router._workflow_type_mappings) == 2

        # Both workflow types should map to the same subreducer
        assert (
            router._workflow_type_mappings[WorkflowType.DATA_ANALYSIS]
            == multi_subreducer.name
        )
        assert (
            router._workflow_type_mappings[WorkflowType.REPORT_GENERATION]
            == multi_subreducer.name
        )

    def test_register_invalid_subreducer_type(self, router):
        """Test registering invalid subreducer type raises error."""
        invalid_subreducer = "not_a_subreducer"

        with pytest.raises(OnexError) as exc_info:
            router.register_subreducer(invalid_subreducer, [WorkflowType.DATA_ANALYSIS])

        assert exc_info.value.error_code == CoreErrorCode.VALIDATION_ERROR
        assert "Invalid subreducer type" in str(exc_info.value)

        # Verify nothing was registered
        assert len(router._subreducers) == 0
        assert len(router._workflow_type_mappings) == 0

    def test_register_duplicate_workflow_type(self, router, mock_subreducers):
        """Test registering duplicate workflow type raises error."""
        # Register first subreducer
        first_subreducer = mock_subreducers["data_analysis"]
        router.register_subreducer(first_subreducer, [WorkflowType.DATA_ANALYSIS])

        # Try to register second subreducer for same workflow type
        second_subreducer = mock_subreducers["multi_type"]

        with pytest.raises(OnexError) as exc_info:
            router.register_subreducer(second_subreducer, [WorkflowType.DATA_ANALYSIS])

        assert exc_info.value.error_code == CoreErrorCode.VALIDATION_ERROR
        assert "already registered" in str(exc_info.value)

        # Verify only first subreducer remains registered
        assert len(router._subreducers) == 1
        assert (
            router._workflow_type_mappings[WorkflowType.DATA_ANALYSIS]
            == first_subreducer.name
        )

    @pytest.mark.asyncio
    async def test_route_single_workflow_type(
        self, router, mock_subreducers, sample_requests
    ):
        """Test routing single workflow type."""
        subreducer = mock_subreducers["data_analysis"]
        router.register_subreducer(subreducer, [WorkflowType.DATA_ANALYSIS])

        request = sample_requests["data_analysis"]
        decision = await router.route(request)

        # Verify routing decision
        assert isinstance(decision, RoutingDecision)
        assert decision.workflow_id == request.workflow_id
        assert decision.workflow_type == request.workflow_type
        assert decision.instance_id == request.instance_id
        assert decision.subreducer_name == subreducer.name
        assert decision.routing_hash is not None
        assert len(decision.routing_hash) == 16  # Truncated SHA-256

        # Verify routing metadata
        assert "correlation_id" in decision.routing_metadata
        assert decision.routing_metadata["routing_algorithm"] == "hash_based"
        assert decision.routing_metadata["total_subreducers"] == 1

        # Verify metrics updated
        metrics = router.get_routing_metrics()
        assert metrics["total_routed"] == 1
        assert metrics["routing_errors"] == 0
        assert metrics["average_routing_time_ms"] > 0

    @pytest.mark.asyncio
    async def test_route_multiple_workflow_types(
        self, router, mock_subreducers, sample_requests
    ):
        """Test routing across multiple workflow types."""
        # Register subreducers for all workflow types
        registrations = [
            (mock_subreducers["data_analysis"], [WorkflowType.DATA_ANALYSIS]),
            (mock_subreducers["report_generation"], [WorkflowType.REPORT_GENERATION]),
            (
                mock_subreducers["document_regeneration"],
                [WorkflowType.DOCUMENT_REGENERATION],
            ),
        ]

        for subreducer, workflow_types in registrations:
            router.register_subreducer(subreducer, workflow_types)

        # Route each workflow type
        routing_results = {}
        for workflow_name, request in sample_requests.items():
            decision = await router.route(request)
            routing_results[workflow_name] = decision

        # Verify each routed correctly
        assert (
            routing_results["data_analysis"].subreducer_name
            == "data_analysis_subreducer"
        )
        assert (
            routing_results["report_generation"].subreducer_name
            == "report_generation_subreducer"
        )
        assert (
            routing_results["document_regeneration"].subreducer_name
            == "document_regeneration_subreducer"
        )

        # Verify all have different routing hashes (different instance IDs)
        hashes = [decision.routing_hash for decision in routing_results.values()]
        assert len(set(hashes)) == len(hashes)  # All unique

        # Verify metrics
        metrics = router.get_routing_metrics()
        assert metrics["total_routed"] == 3
        assert metrics["routing_errors"] == 0

    @pytest.mark.asyncio
    async def test_route_unsupported_workflow_type(self, router, mock_subreducers):
        """Test routing unsupported workflow type raises error."""
        # Register only one subreducer
        router.register_subreducer(
            mock_subreducers["data_analysis"], [WorkflowType.DATA_ANALYSIS]
        )

        # Try to route unsupported workflow type
        unsupported_request = WorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.REPORT_GENERATION,  # Not registered
            instance_id="unsupported-001",
            correlation_id=uuid4(),
            payload={"test": "data"},
        )

        with pytest.raises(OnexError) as exc_info:
            await router.route(unsupported_request)

        assert exc_info.value.error_code == CoreErrorCode.VALIDATION_ERROR
        assert "Unsupported workflow type" in str(exc_info.value)

        # Verify metrics reflect error
        metrics = router.get_routing_metrics()
        assert metrics["routing_errors"] == 1
        assert metrics["total_routed"] == 0  # No successful routing

    @pytest.mark.asyncio
    async def test_routing_hash_consistency(self, router, mock_subreducers):
        """Test that routing hash is consistent for same workflow type and instance ID."""
        router.register_subreducer(
            mock_subreducers["data_analysis"], [WorkflowType.DATA_ANALYSIS]
        )

        # Create multiple requests with same workflow type and instance ID
        base_request = WorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="consistency-test-001",
            correlation_id=uuid4(),
            payload={"data": [1, 2, 3]},
        )

        # Route multiple times
        decisions = []
        for i in range(5):
            # New workflow ID but same type and instance ID
            request = WorkflowRequest(
                workflow_id=uuid4(),  # Different workflow ID
                workflow_type=base_request.workflow_type,
                instance_id=base_request.instance_id,  # Same instance ID
                correlation_id=uuid4(),
                payload=base_request.payload,
            )

            decision = await router.route(request)
            decisions.append(decision)

        # All should have same routing hash (same workflow type + instance ID)
        routing_hashes = [d.routing_hash for d in decisions]
        assert all(h == routing_hashes[0] for h in routing_hashes)

        # All should route to same subreducer
        subreducer_names = [d.subreducer_name for d in decisions]
        assert all(name == subreducer_names[0] for name in subreducer_names)

    @pytest.mark.asyncio
    async def test_routing_hash_variation(self, router, mock_subreducers):
        """Test that routing hash varies with different instance IDs."""
        router.register_subreducer(
            mock_subreducers["data_analysis"], [WorkflowType.DATA_ANALYSIS]
        )

        # Create requests with different instance IDs
        requests = []
        for i in range(10):
            request = WorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.DATA_ANALYSIS,
                instance_id=f"hash-variation-{i:03d}",  # Different instance IDs
                correlation_id=uuid4(),
                payload={"data": [i]},
            )
            requests.append(request)

        # Route all requests
        decisions = []
        for request in requests:
            decision = await router.route(request)
            decisions.append(decision)

        # All routing hashes should be different
        routing_hashes = [d.routing_hash for d in decisions]
        assert len(set(routing_hashes)) == len(routing_hashes)  # All unique

    def test_generate_routing_hash_correctness(self, router):
        """Test routing hash generation correctness."""
        workflow_type = "data_analysis"
        instance_id = "test-instance-001"

        # Generate hash using router method
        router_hash = router._generate_routing_hash(workflow_type, instance_id)

        # Generate expected hash manually
        routing_key = f"{workflow_type}:{instance_id}"
        expected_hash = hashlib.sha256(routing_key.encode()).hexdigest()[:16]

        assert router_hash == expected_hash
        assert len(router_hash) == 16

    def test_get_subreducer_retrieval(self, router, mock_subreducers):
        """Test subreducer retrieval by name."""
        # Test retrieval from empty router
        assert router.get_subreducer("nonexistent") is None

        # Register subreducers
        for name, subreducer in mock_subreducers.items():
            if name != "multi_type":  # Skip multi-type for simpler test
                router.register_subreducer(subreducer, subreducer._supported_types)

        # Test retrieval of registered subreducers
        for name, subreducer in mock_subreducers.items():
            if name != "multi_type":
                retrieved = router.get_subreducer(subreducer.name)
                assert retrieved == subreducer

        # Test retrieval of non-existent subreducer
        assert router.get_subreducer("non_existent_subreducer") is None

    @pytest.mark.asyncio
    async def test_routing_metrics_tracking(
        self, router, mock_subreducers, sample_requests
    ):
        """Test comprehensive routing metrics tracking."""
        # Register subreducers
        for name, subreducer in mock_subreducers.items():
            if name != "multi_type":
                router.register_subreducer(subreducer, subreducer._supported_types)

        # Route multiple requests successfully
        successful_requests = 0
        for workflow_name, request in sample_requests.items():
            await router.route(request)
            successful_requests += 1

        # Try to route unsupported workflow (will increment error count)
        unsupported_request = WorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DATA_ANALYSIS,  # Registered type
            instance_id="unsupported-instance",
            correlation_id=uuid4(),
            payload={"test": "data"},
        )

        # First, unregister data analysis to make it unsupported
        router._workflow_type_mappings.clear()
        router.register_subreducer(
            mock_subreducers["report_generation"], [WorkflowType.REPORT_GENERATION]
        )

        try:
            await router.route(unsupported_request)
        except OnexError:
            pass  # Expected error

        # Verify metrics
        metrics = router.get_routing_metrics()
        assert metrics["total_routed"] == successful_requests
        assert metrics["routing_errors"] == 1
        assert metrics["average_routing_time_ms"] > 0

        # Route one more successful request to test average calculation
        report_request = sample_requests["report_generation"]
        await router.route(report_request)

        updated_metrics = router.get_routing_metrics()
        assert updated_metrics["total_routed"] == successful_requests + 1
        assert updated_metrics["routing_errors"] == 1  # Same as before
        assert updated_metrics["average_routing_time_ms"] > 0

    @pytest.mark.asyncio
    async def test_concurrent_routing_performance(self, router, mock_subreducers):
        """Test router performance under concurrent load."""
        # Register all subreducers
        for name, subreducer in mock_subreducers.items():
            if name != "multi_type":
                router.register_subreducer(subreducer, subreducer._supported_types)

        # Create many concurrent routing requests
        concurrent_requests = []
        for i in range(100):
            workflow_type = [
                WorkflowType.DATA_ANALYSIS,
                WorkflowType.REPORT_GENERATION,
                WorkflowType.DOCUMENT_REGENERATION,
            ][i % 3]
            request = WorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=workflow_type,
                instance_id=f"concurrent-{i:03d}",
                correlation_id=uuid4(),
                payload={"batch_id": i // 10, "request_id": i},
            )
            concurrent_requests.append(request)

        # Route all requests concurrently
        import time

        start_time = time.time()
        routing_tasks = [router.route(request) for request in concurrent_requests]
        decisions = await asyncio.gather(*routing_tasks)
        total_time = time.time() - start_time

        # Verify all routed successfully
        assert len(decisions) == len(concurrent_requests)

        # Verify routing distribution
        subreducer_counts = {}
        for decision in decisions:
            subreducer_counts[decision.subreducer_name] = (
                subreducer_counts.get(decision.subreducer_name, 0) + 1
            )

        # Should have roughly even distribution across workflow types
        assert len(subreducer_counts) == 3
        for count in subreducer_counts.values():
            assert count > 0

        # Verify performance metrics
        metrics = router.get_routing_metrics()
        assert metrics["total_routed"] == 100
        assert metrics["routing_errors"] == 0
        assert metrics["average_routing_time_ms"] > 0

        print(
            f"Routed {len(concurrent_requests)} requests concurrently in {total_time:.3f}s"
        )
        print(f"Average routing time: {metrics['average_routing_time_ms']:.3f}ms")

    @pytest.mark.asyncio
    async def test_routing_decision_structure(
        self, router, mock_subreducers, sample_requests
    ):
        """Test comprehensive routing decision structure and metadata."""
        subreducer = mock_subreducers["data_analysis"]
        router.register_subreducer(subreducer, [WorkflowType.DATA_ANALYSIS])

        request = sample_requests["data_analysis"]
        decision = await router.route(request)

        # Verify decision structure
        assert hasattr(decision, "workflow_id")
        assert hasattr(decision, "workflow_type")
        assert hasattr(decision, "instance_id")
        assert hasattr(decision, "subreducer_name")
        assert hasattr(decision, "routing_hash")
        assert hasattr(decision, "routing_metadata")

        # Verify decision values
        assert decision.workflow_id == request.workflow_id
        assert decision.workflow_type == request.workflow_type
        assert decision.instance_id == request.instance_id
        assert decision.subreducer_name == subreducer.name

        # Verify routing hash format
        assert isinstance(decision.routing_hash, str)
        assert len(decision.routing_hash) == 16
        assert all(c in "0123456789abcdef" for c in decision.routing_hash)  # Valid hex

        # Verify routing metadata
        metadata = decision.routing_metadata
        assert "correlation_id" in metadata
        assert metadata["correlation_id"] == str(request.correlation_id)
        assert metadata["routing_algorithm"] == "hash_based"
        assert metadata["total_subreducers"] == 1

    @pytest.mark.asyncio
    async def test_error_handling_and_logging(self, router, mock_subreducers):
        """Test error handling and structured logging."""
        router.register_subreducer(
            mock_subreducers["data_analysis"], [WorkflowType.DATA_ANALYSIS]
        )

        # Test with structured logging capture
        with patch(
            "omnibase_core.patterns.reducer_pattern_engine.v1_0_0.router.emit_log_event"
        ) as mock_log:
            # Successful routing
            request = WorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.DATA_ANALYSIS,
                instance_id="logging-test-001",
                correlation_id=uuid4(),
                payload={"test": "data"},
            )

            await router.route(request)

            # Verify success logging
            success_calls = [
                call
                for call in mock_log.call_args_list
                if "workflow_routed" in str(call)
            ]
            assert len(success_calls) > 0

            # Test error routing
            error_request = WorkflowRequest(
                workflow_id=uuid4(),
                workflow_type=WorkflowType.REPORT_GENERATION,  # Not registered
                instance_id="error-test-001",
                correlation_id=uuid4(),
                payload={"test": "error"},
            )

            try:
                await router.route(error_request)
            except OnexError:
                pass  # Expected

            # Verify error logging
            error_calls = [
                call
                for call in mock_log.call_args_list
                if "routing_failed" in str(call)
            ]
            assert len(error_calls) > 0

    @pytest.mark.asyncio
    async def test_routing_with_complex_payloads(self, router, mock_subreducers):
        """Test routing with complex payload structures."""
        router.register_subreducer(
            mock_subreducers["data_analysis"], [WorkflowType.DATA_ANALYSIS]
        )

        # Create request with complex payload
        complex_payload = {
            "data": list(range(1000)),  # Large list
            "metadata": {
                "nested": {"deeply": {"nested": {"value": "test"}}},
                "analysis_config": {
                    "algorithms": ["linear", "polynomial", "exponential"],
                    "parameters": {"threshold": 0.95, "iterations": 100},
                },
            },
            "binary_data": bytes(range(256)),
            "unicode_text": "测试数据 🚀 émojis and unicode",
        }

        complex_request = WorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="complex-payload-001",
            correlation_id=uuid4(),
            payload=complex_payload,
        )

        # Should route successfully regardless of payload complexity
        decision = await router.route(complex_request)

        assert decision.subreducer_name == "data_analysis_subreducer"
        assert decision.workflow_id == complex_request.workflow_id
        assert decision.routing_hash is not None

        # Routing hash should be consistent for same instance ID regardless of payload
        simple_request = WorkflowRequest(
            workflow_id=uuid4(),
            workflow_type=WorkflowType.DATA_ANALYSIS,
            instance_id="complex-payload-001",  # Same instance ID
            correlation_id=uuid4(),
            payload={"simple": "payload"},
        )

        simple_decision = await router.route(simple_request)

        # Should have same routing hash (based on workflow type and instance ID only)
        assert simple_decision.routing_hash == decision.routing_hash
