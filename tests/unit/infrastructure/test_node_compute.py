"""
Comprehensive unit tests for NodeCompute infrastructure class.

Tests cover:
- Initialization with ModelONEXContainer dependency injection
- Contract loading and validation
- Computation execution (sequential and parallel)
- RSD priority calculation algorithm
- Computation registry management
- Caching layer operations
- Performance metrics tracking
- Resource lifecycle management
- Input/output validation
- Introspection and health monitoring
"""

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.infrastructure.node_compute import NodeCompute
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.operations.model_compute_input import ModelComputeInput
from omnibase_core.models.operations.model_compute_output import ModelComputeOutput


class TestNodeComputeInitialization:
    """Test NodeCompute initialization and contract loading."""

    def test_node_compute_initialization_success(self):
        """Test successful NodeCompute initialization with valid container."""
        container = ModelONEXContainer()

        with (
            patch.object(NodeCompute, "_load_contract_model") as mock_load_contract,
            patch.object(
                NodeCompute, "_register_rsd_computations"
            ) as mock_register_rsd,
        ):
            mock_contract = Mock()
            mock_contract.node_type = "compute"
            mock_contract.version = "1.0.0"
            mock_load_contract.return_value = mock_contract

            node = NodeCompute(container)

            assert node.container == container
            assert isinstance(node.node_id, UUID)
            assert isinstance(node.created_at, datetime)
            assert node.max_parallel_workers == 4
            assert node.cache_ttl_minutes == 30
            assert node.performance_threshold_ms == 100.0
            assert node.computation_cache is not None
            assert (
                node.thread_pool is None
            )  # Not initialized until _initialize_node_resources
            assert isinstance(node.computation_registry, dict)
            assert isinstance(node.computation_metrics, dict)

            mock_load_contract.assert_called_once()
            mock_register_rsd.assert_called_once()

    def test_node_compute_contract_model_loading(self):
        """Test contract model loading with valid contract file."""
        container = ModelONEXContainer()

        # Note: This is a complex test that would require mocking the entire contract
        # loading pipeline. For now, we're testing that _load_contract_model is called
        # during initialization, which is covered by test_node_compute_initialization_success
        with patch.object(NodeCompute, "_load_contract_model") as mock_load_contract:
            mock_contract = Mock()
            mock_contract.node_type = "compute"
            mock_contract.version = "1.0.0"
            mock_contract.validate_node_specific_config = Mock()
            mock_load_contract.return_value = mock_contract

            node = NodeCompute(container)

            assert node.contract_model is not None
            mock_load_contract.assert_called_once()

    def test_node_compute_contract_loading_failure(self):
        """Test error handling when contract loading fails."""
        container = ModelONEXContainer()

        with (
            patch.object(NodeCompute, "_find_contract_path") as mock_find_path,
            patch.object(NodeCompute, "_register_rsd_computations"),
        ):
            mock_find_path.side_effect = FileNotFoundError("Contract not found")

            with pytest.raises(ModelOnexError) as exc_info:
                NodeCompute(container)

            assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
            assert "Contract model loading failed" in exc_info.value.message

    def test_node_compute_rsd_computations_registered(self):
        """Test that RSD computations are registered during initialization."""
        container = ModelONEXContainer()

        with patch.object(NodeCompute, "_load_contract_model") as mock_load_contract:
            mock_contract = Mock()
            mock_contract.node_type = "compute"
            mock_contract.version = "1.0.0"
            mock_load_contract.return_value = mock_contract

            node = NodeCompute(container)

            assert "rsd_priority_calculation" in node.computation_registry
            assert callable(node.computation_registry["rsd_priority_calculation"])


class TestNodeComputeProcessing:
    """Test NodeCompute core processing functionality."""

    @pytest.fixture
    def node_compute(self):
        """Create NodeCompute instance for testing."""
        container = ModelONEXContainer()

        with patch.object(NodeCompute, "_load_contract_model") as mock_load_contract:
            mock_contract = Mock()
            mock_contract.node_type = "compute"
            mock_contract.version = "1.0.0"
            mock_load_contract.return_value = mock_contract

            node = NodeCompute(container)
            return node

    @pytest.mark.asyncio
    async def test_process_with_cache_miss_sequential(self, node_compute):
        """Test process method with cache miss and sequential execution."""

        # Register a simple computation
        def simple_computation(data: dict[str, Any]) -> int:
            return data["value"] * 2

        node_compute.register_computation("simple_test", simple_computation)

        # Create input
        input_data = ModelComputeInput(
            data={"value": 5},
            computation_type="simple_test",
            cache_enabled=True,
            parallel_enabled=False,
        )

        # Execute
        output = await node_compute.process(input_data)

        assert isinstance(output, ModelComputeOutput)
        assert output.result == 10
        assert output.operation_id == input_data.operation_id
        assert output.computation_type == "simple_test"
        assert output.processing_time_ms > 0
        assert output.cache_hit is False
        assert output.parallel_execution_used is False

    @pytest.mark.asyncio
    async def test_process_with_cache_hit(self, node_compute):
        """Test process method with cache hit."""

        # Register computation
        def simple_computation(data: dict[str, Any]) -> int:
            return data["value"] * 2

        node_compute.register_computation("cache_test", simple_computation)

        # First call - cache miss
        input_data = ModelComputeInput(
            data={"value": 7},
            computation_type="cache_test",
            cache_enabled=True,
        )

        output1 = await node_compute.process(input_data)
        assert output1.cache_hit is False

        # Second call - cache hit
        output2 = await node_compute.process(input_data)
        assert output2.cache_hit is True
        assert output2.processing_time_ms == 0.0
        assert output2.result == output1.result

    @pytest.mark.asyncio
    async def test_process_without_caching(self, node_compute):
        """Test process method with caching disabled."""
        # Register computation
        computation_calls = []

        def tracked_computation(data: dict[str, Any]) -> int:
            computation_calls.append(data)
            return data["value"] * 3

        node_compute.register_computation("no_cache_test", tracked_computation)

        # Execute twice with cache disabled
        input_data = ModelComputeInput(
            data={"value": 4},
            computation_type="no_cache_test",
            cache_enabled=False,
        )

        output1 = await node_compute.process(input_data)
        output2 = await node_compute.process(input_data)

        assert len(computation_calls) == 2  # Both calls executed
        assert output1.cache_hit is False
        assert output2.cache_hit is False

    @pytest.mark.asyncio
    async def test_process_parallel_execution(self, node_compute):
        """Test process method with parallel execution enabled."""

        # Register batch computation
        def batch_computation(data: list[int]) -> list[int]:
            return [x * 2 for x in data]

        node_compute.register_computation("batch_test", batch_computation)

        # Initialize thread pool
        await node_compute._initialize_node_resources()

        # Execute with batch data
        input_data = ModelComputeInput(
            data=[1, 2, 3, 4, 5],
            computation_type="batch_test",
            cache_enabled=False,
            parallel_enabled=True,
        )

        output = await node_compute.process(input_data)

        assert output.result == [2, 4, 6, 8, 10]
        assert output.parallel_execution_used is True

        # Cleanup
        await node_compute._cleanup_node_resources()

    @pytest.mark.asyncio
    async def test_process_performance_threshold_warning(self, node_compute):
        """Test that slow computations trigger performance warnings."""

        # Register slow computation
        def slow_computation(data: dict[str, Any]) -> int:
            time.sleep(0.15)  # Exceed 100ms threshold
            return data["value"]

        node_compute.register_computation("slow_test", slow_computation)

        input_data = ModelComputeInput(
            data={"value": 42},
            computation_type="slow_test",
            cache_enabled=False,
        )

        with patch(
            "omnibase_core.infrastructure.node_compute.emit_log_event"
        ) as mock_log:
            output = await node_compute.process(input_data)

            assert output.processing_time_ms > node_compute.performance_threshold_ms

            # Check that warning was logged
            warning_logged = any(
                call[0][1].startswith("Computation exceeded performance threshold")
                for call in mock_log.call_args_list
            )
            assert warning_logged

    @pytest.mark.asyncio
    async def test_process_unknown_computation_type(self, node_compute):
        """Test process with unknown computation type raises error."""
        input_data = ModelComputeInput(
            data={"value": 1},
            computation_type="unknown_computation",
            cache_enabled=False,
        )

        with pytest.raises(ModelOnexError) as exc_info:
            await node_compute.process(input_data)

        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
        assert "Unknown computation type" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_process_computation_failure(self, node_compute):
        """Test process handles computation failures gracefully."""

        def failing_computation(data: dict[str, Any]) -> int:
            raise ValueError("Computation failed intentionally")

        node_compute.register_computation("failing_test", failing_computation)

        input_data = ModelComputeInput(
            data={"value": 1},
            computation_type="failing_test",
            cache_enabled=False,
        )

        with pytest.raises(ModelOnexError) as exc_info:
            await node_compute.process(input_data)

        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
        assert "Computation failed" in exc_info.value.message

        # Check error metrics updated
        assert "failing_test" in node_compute.computation_metrics
        assert node_compute.computation_metrics["failing_test"]["error_count"] == 1.0


class TestNodeComputeRSDAlgorithm:
    """Test RSD priority calculation algorithm."""

    @pytest.fixture
    def node_compute(self):
        """Create NodeCompute instance for testing."""
        container = ModelONEXContainer()

        with patch.object(NodeCompute, "_load_contract_model") as mock_load_contract:
            mock_contract = Mock()
            mock_contract.node_type = "compute"
            mock_load_contract.return_value = mock_contract

            return NodeCompute(container)

    @pytest.mark.asyncio
    async def test_calculate_rsd_priority_default_values(self, node_compute):
        """Test RSD calculation with default parameter values."""
        ticket_id = uuid4()

        priority = await node_compute.calculate_rsd_priority(ticket_id)

        assert isinstance(priority, float)
        assert 0.0 <= priority <= 100.0
        # Defaults: dependency=0, failure=0, days=0, agent=0, user_override=0.5
        # time_score (days=0) = 0.1, user_score = 0.5
        # Total = 0.15*0.1*100 + 0.10*0.5*100 = 1.5 + 5.0 = 6.5
        assert priority == 6.5

    @pytest.mark.asyncio
    async def test_calculate_rsd_priority_max_values(self, node_compute):
        """Test RSD calculation with maximum parameter values."""
        ticket_id = uuid4()

        priority = await node_compute.calculate_rsd_priority(
            ticket_id,
            dependency_count=10,
            failure_indicators=5,
            days_old=30.0,
            agent_requests=5,
            user_override_score=1.0,
        )

        assert isinstance(priority, float)
        assert priority > 80.0  # High values should give high priority

    @pytest.mark.asyncio
    async def test_calculate_rsd_priority_time_decay(self, node_compute):
        """Test RSD calculation time decay factor."""
        ticket_id = uuid4()

        # Recent ticket (< 7 days)
        priority_recent = await node_compute.calculate_rsd_priority(
            ticket_id, days_old=3.0
        )

        # Old ticket (> 7 days)
        priority_old = await node_compute.calculate_rsd_priority(
            ticket_id, days_old=21.0
        )

        assert priority_old > priority_recent  # Older tickets get higher priority

    @pytest.mark.asyncio
    async def test_calculate_rsd_priority_dependency_distance(self, node_compute):
        """Test RSD calculation dependency distance factor."""
        ticket_id = uuid4()

        priority_no_deps = await node_compute.calculate_rsd_priority(
            ticket_id, dependency_count=0
        )

        priority_many_deps = await node_compute.calculate_rsd_priority(
            ticket_id, dependency_count=8
        )

        assert (
            priority_many_deps > priority_no_deps
        )  # More dependencies = higher priority

    @pytest.mark.asyncio
    async def test_calculate_rsd_priority_failure_surface(self, node_compute):
        """Test RSD calculation failure surface factor."""
        ticket_id = uuid4()

        priority_no_failures = await node_compute.calculate_rsd_priority(
            ticket_id, failure_indicators=0
        )

        priority_many_failures = await node_compute.calculate_rsd_priority(
            ticket_id, failure_indicators=4
        )

        assert (
            priority_many_failures > priority_no_failures
        )  # More failures = higher priority

    @pytest.mark.asyncio
    async def test_calculate_rsd_priority_caching(self, node_compute):
        """Test that RSD calculations are cached."""
        ticket_id = uuid4()

        # First call
        priority1 = await node_compute.calculate_rsd_priority(
            ticket_id,
            dependency_count=5,
            failure_indicators=2,
            days_old=10.0,
        )

        # Check cache was populated
        cache_stats = node_compute.computation_cache.get_stats()
        assert cache_stats["total_entries"] > 0

        # Second call with same parameters should hit cache
        priority2 = await node_compute.calculate_rsd_priority(
            ticket_id,
            dependency_count=5,
            failure_indicators=2,
            days_old=10.0,
        )

        assert priority1 == priority2


class TestNodeComputeRegistry:
    """Test computation registry management."""

    @pytest.fixture
    def node_compute(self):
        """Create NodeCompute instance for testing."""
        container = ModelONEXContainer()

        with patch.object(NodeCompute, "_load_contract_model") as mock_load_contract:
            mock_contract = Mock()
            mock_contract.node_type = "compute"
            mock_load_contract.return_value = mock_contract

            return NodeCompute(container)

    def test_register_computation_success(self, node_compute):
        """Test successful computation registration."""

        def custom_computation(data: dict[str, Any]) -> str:
            return f"processed: {data['value']}"

        node_compute.register_computation("custom_test", custom_computation)

        assert "custom_test" in node_compute.computation_registry
        assert node_compute.computation_registry["custom_test"] == custom_computation

    def test_register_computation_duplicate_fails(self, node_compute):
        """Test that duplicate computation registration fails."""

        def computation1(data: dict[str, Any]) -> int:
            return 1

        def computation2(data: dict[str, Any]) -> int:
            return 2

        node_compute.register_computation("duplicate_test", computation1)

        with pytest.raises(ModelOnexError) as exc_info:
            node_compute.register_computation("duplicate_test", computation2)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "already registered" in exc_info.value.message

    def test_register_computation_non_callable_fails(self, node_compute):
        """Test that registering non-callable fails."""
        with pytest.raises(ModelOnexError) as exc_info:
            node_compute.register_computation("invalid_test", "not_a_function")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "must be callable" in exc_info.value.message

    def test_register_multiple_computations(self, node_compute):
        """Test registering multiple different computations."""
        computations = {
            "comp1": lambda data: data["x"] + 1,
            "comp2": lambda data: data["x"] * 2,
            "comp3": lambda data: data["x"] ** 2,
        }

        for name, func in computations.items():
            node_compute.register_computation(name, func)

        for name in computations:
            assert name in node_compute.computation_registry


class TestNodeComputeValidation:
    """Test NodeCompute input validation."""

    @pytest.fixture
    def node_compute(self):
        """Create NodeCompute instance for testing."""
        container = ModelONEXContainer()

        with patch.object(NodeCompute, "_load_contract_model") as mock_load_contract:
            mock_contract = Mock()
            mock_contract.node_type = "compute"
            mock_load_contract.return_value = mock_contract

            return NodeCompute(container)

    def test_validate_compute_input_success(self, node_compute):
        """Test successful input validation."""
        input_data = ModelComputeInput(
            data={"value": 42}, computation_type="test_computation"
        )

        # Should not raise
        node_compute._validate_compute_input(input_data)

    def test_validate_compute_input_missing_data(self, node_compute):
        """Test validation fails when data attribute is missing."""
        # Create mock input without 'data' attribute
        invalid_input = Mock(spec=[])
        invalid_input.operation_id = uuid4()

        with pytest.raises(ModelOnexError) as exc_info:
            node_compute._validate_compute_input(invalid_input)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "must have 'data' attribute" in exc_info.value.message

    def test_validate_compute_input_missing_computation_type(self, node_compute):
        """Test validation fails when computation_type is missing."""
        # Create mock input without 'computation_type' attribute
        invalid_input = Mock(spec=["data"])
        invalid_input.data = {"value": 1}
        invalid_input.operation_id = uuid4()

        with pytest.raises(ModelOnexError) as exc_info:
            node_compute._validate_compute_input(invalid_input)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "must have 'computation_type' attribute" in exc_info.value.message


class TestNodeComputeCaching:
    """Test NodeCompute caching operations."""

    @pytest.fixture
    def node_compute(self):
        """Create NodeCompute instance for testing."""
        container = ModelONEXContainer()

        with patch.object(NodeCompute, "_load_contract_model") as mock_load_contract:
            mock_contract = Mock()
            mock_contract.node_type = "compute"
            mock_load_contract.return_value = mock_contract

            return NodeCompute(container)

    def test_generate_cache_key_deterministic(self, node_compute):
        """Test cache key generation is deterministic."""
        input_data1 = ModelComputeInput(
            data={"value": 42}, computation_type="test_comp"
        )
        input_data2 = ModelComputeInput(
            data={"value": 42}, computation_type="test_comp"
        )

        key1 = node_compute._generate_cache_key(input_data1)
        key2 = node_compute._generate_cache_key(input_data2)

        assert key1 == key2

    def test_generate_cache_key_different_data(self, node_compute):
        """Test cache keys differ for different data."""
        input_data1 = ModelComputeInput(data={"value": 42}, computation_type="test")
        input_data2 = ModelComputeInput(data={"value": 43}, computation_type="test")

        key1 = node_compute._generate_cache_key(input_data1)
        key2 = node_compute._generate_cache_key(input_data2)

        assert key1 != key2

    def test_generate_cache_key_different_type(self, node_compute):
        """Test cache keys differ for different computation types."""
        input_data1 = ModelComputeInput(data={"value": 42}, computation_type="type1")
        input_data2 = ModelComputeInput(data={"value": 42}, computation_type="type2")

        key1 = node_compute._generate_cache_key(input_data1)
        key2 = node_compute._generate_cache_key(input_data2)

        assert key1 != key2

    def test_cache_integration(self, node_compute):
        """Test cache integration with computation cache."""
        input_data = ModelComputeInput(
            data={"value": 100}, computation_type="cache_integration_test"
        )

        cache_key = node_compute._generate_cache_key(input_data)

        # Cache should be empty initially
        cached_value = node_compute.computation_cache.get(cache_key)
        assert cached_value is None

        # Put value in cache
        result_value = 200
        node_compute.computation_cache.put(cache_key, result_value, 30)

        # Retrieve from cache
        cached_value = node_compute.computation_cache.get(cache_key)
        assert cached_value == result_value


class TestNodeComputeParallelExecution:
    """Test NodeCompute parallel execution capabilities."""

    @pytest.fixture
    def node_compute(self):
        """Create NodeCompute instance for testing."""
        container = ModelONEXContainer()

        with patch.object(NodeCompute, "_load_contract_model") as mock_load_contract:
            mock_contract = Mock()
            mock_contract.node_type = "compute"
            mock_load_contract.return_value = mock_contract

            return NodeCompute(container)

    def test_supports_parallel_execution_with_list(self, node_compute):
        """Test parallel execution support detection with list data."""
        input_data = ModelComputeInput(data=[1, 2, 3, 4], computation_type="batch")

        assert node_compute._supports_parallel_execution(input_data) is True

    def test_supports_parallel_execution_with_tuple(self, node_compute):
        """Test parallel execution support detection with tuple data."""
        input_data = ModelComputeInput(data=(1, 2, 3), computation_type="batch")

        assert node_compute._supports_parallel_execution(input_data) is True

    def test_supports_parallel_execution_with_single_item(self, node_compute):
        """Test parallel execution not supported for single item."""
        input_data = ModelComputeInput(data=[1], computation_type="single")

        assert node_compute._supports_parallel_execution(input_data) is False

    def test_supports_parallel_execution_with_dict(self, node_compute):
        """Test parallel execution not supported for dict data."""
        input_data = ModelComputeInput(data={"value": 42}, computation_type="dict")

        assert node_compute._supports_parallel_execution(input_data) is False

    @pytest.mark.asyncio
    async def test_execute_parallel_computation_fallback(self, node_compute):
        """Test parallel execution falls back to sequential when no thread pool."""

        def batch_computation(data: list[int]) -> list[int]:
            return [x * 2 for x in data]

        node_compute.register_computation("batch_fallback", batch_computation)

        input_data = ModelComputeInput(
            data=[1, 2, 3], computation_type="batch_fallback"
        )

        # Thread pool is None by default
        assert node_compute.thread_pool is None

        result = await node_compute._execute_parallel_computation(input_data)

        assert result == [2, 4, 6]


class TestNodeComputeMetrics:
    """Test NodeCompute metrics tracking."""

    @pytest.fixture
    def node_compute(self):
        """Create NodeCompute instance for testing."""
        container = ModelONEXContainer()

        with patch.object(NodeCompute, "_load_contract_model") as mock_load_contract:
            mock_contract = Mock()
            mock_contract.node_type = "compute"
            mock_load_contract.return_value = mock_contract

            return NodeCompute(container)

    @pytest.mark.asyncio
    async def test_update_computation_metrics_success(self, node_compute):
        """Test computation metrics tracking for successful operations."""
        await node_compute._update_computation_metrics("test_comp", 50.0, True)

        assert "test_comp" in node_compute.computation_metrics
        metrics = node_compute.computation_metrics["test_comp"]

        assert metrics["total_operations"] == 1.0
        assert metrics["success_count"] == 1.0
        assert metrics["error_count"] == 0.0
        assert metrics["avg_processing_time_ms"] == 50.0
        assert metrics["min_processing_time_ms"] == 50.0
        assert metrics["max_processing_time_ms"] == 50.0

    @pytest.mark.asyncio
    async def test_update_computation_metrics_error(self, node_compute):
        """Test computation metrics tracking for failed operations."""
        await node_compute._update_computation_metrics("test_comp", 75.0, False)

        metrics = node_compute.computation_metrics["test_comp"]

        assert metrics["total_operations"] == 1.0
        assert metrics["success_count"] == 0.0
        assert metrics["error_count"] == 1.0

    @pytest.mark.asyncio
    async def test_update_computation_metrics_rolling_average(self, node_compute):
        """Test rolling average calculation for processing time."""
        # First operation: 100ms
        await node_compute._update_computation_metrics("avg_test", 100.0, True)
        metrics = node_compute.computation_metrics["avg_test"]
        assert metrics["avg_processing_time_ms"] == 100.0

        # Second operation: 200ms
        await node_compute._update_computation_metrics("avg_test", 200.0, True)
        metrics = node_compute.computation_metrics["avg_test"]
        assert metrics["avg_processing_time_ms"] == 150.0  # (100 + 200) / 2

        # Third operation: 150ms
        await node_compute._update_computation_metrics("avg_test", 150.0, True)
        metrics = node_compute.computation_metrics["avg_test"]
        assert metrics["avg_processing_time_ms"] == 150.0  # (100 + 200 + 150) / 3

    @pytest.mark.asyncio
    async def test_update_computation_metrics_min_max(self, node_compute):
        """Test min/max processing time tracking."""
        await node_compute._update_computation_metrics("minmax_test", 100.0, True)
        await node_compute._update_computation_metrics("minmax_test", 50.0, True)
        await node_compute._update_computation_metrics("minmax_test", 200.0, True)

        metrics = node_compute.computation_metrics["minmax_test"]
        assert metrics["min_processing_time_ms"] == 50.0
        assert metrics["max_processing_time_ms"] == 200.0

    @pytest.mark.asyncio
    async def test_get_computation_metrics(self, node_compute):
        """Test retrieving comprehensive computation metrics."""
        # Add some metrics
        await node_compute._update_computation_metrics("comp1", 50.0, True)
        await node_compute._update_computation_metrics("comp2", 75.0, True)

        metrics = await node_compute.get_computation_metrics()

        assert "comp1" in metrics
        assert "comp2" in metrics
        assert "cache_performance" in metrics
        assert "parallel_processing" in metrics

        cache_perf = metrics["cache_performance"]
        assert "total_entries" in cache_perf
        assert "cache_utilization" in cache_perf

        parallel_info = metrics["parallel_processing"]
        assert parallel_info["max_workers"] == 4.0


class TestNodeComputeLifecycle:
    """Test NodeCompute resource lifecycle management."""

    @pytest.fixture
    def node_compute(self):
        """Create NodeCompute instance for testing."""
        container = ModelONEXContainer()

        with patch.object(NodeCompute, "_load_contract_model") as mock_load_contract:
            mock_contract = Mock()
            mock_contract.node_type = "compute"
            mock_load_contract.return_value = mock_contract

            return NodeCompute(container)

    @pytest.mark.asyncio
    async def test_initialize_node_resources(self, node_compute):
        """Test node resource initialization."""
        assert node_compute.thread_pool is None

        await node_compute._initialize_node_resources()

        assert node_compute.thread_pool is not None
        assert (
            node_compute.thread_pool._max_workers == node_compute.max_parallel_workers
        )

        # Cleanup
        await node_compute._cleanup_node_resources()

    @pytest.mark.asyncio
    async def test_cleanup_node_resources(self, node_compute):
        """Test node resource cleanup."""
        # Initialize resources first
        await node_compute._initialize_node_resources()
        assert node_compute.thread_pool is not None

        # Add some cache entries
        node_compute.computation_cache.put("test_key", "test_value", 30)
        assert node_compute.computation_cache.get_stats()["total_entries"] > 0

        # Cleanup
        await node_compute._cleanup_node_resources()

        assert node_compute.thread_pool is None
        assert node_compute.computation_cache.get_stats()["total_entries"] == 0

    @pytest.mark.asyncio
    async def test_cleanup_idempotent(self, node_compute):
        """Test that cleanup can be called multiple times safely."""
        await node_compute._initialize_node_resources()
        await node_compute._cleanup_node_resources()

        # Second cleanup should not raise
        await node_compute._cleanup_node_resources()

        assert node_compute.thread_pool is None


class TestNodeComputeIntrospection:
    """Test NodeCompute introspection capabilities."""

    @pytest.fixture
    def node_compute(self):
        """Create NodeCompute instance for testing."""
        container = ModelONEXContainer()

        with patch.object(NodeCompute, "_load_contract_model") as mock_load_contract:
            mock_contract = Mock()
            mock_contract.node_type = "compute"
            mock_contract.version = "1.0.0"
            mock_contract.algorithm = Mock()
            mock_contract.algorithm.algorithm_type = "rsd_priority"
            mock_contract.algorithm.factors = [
                "dependency_distance",
                "failure_surface",
            ]
            mock_contract.input_model = "ModelComputeInput"
            mock_contract.output_model = "ModelComputeOutput"
            mock_load_contract.return_value = mock_contract

            return NodeCompute(container)

    @pytest.mark.asyncio
    async def test_get_introspection_data_success(self, node_compute):
        """Test successful introspection data retrieval."""
        introspection = await node_compute.get_introspection_data()

        assert "node_capabilities" in introspection
        assert "contract_details" in introspection
        assert "runtime_information" in introspection
        assert "algorithm_information" in introspection
        assert "performance_configuration" in introspection
        assert "introspection_metadata" in introspection

        # Verify node capabilities
        capabilities = introspection["node_capabilities"]
        assert capabilities["node_type"] == "NodeCompute"
        assert capabilities["node_classification"] == "compute"
        assert isinstance(capabilities["node_id"], UUID)

        # Verify algorithm information
        algo_info = introspection["algorithm_information"]
        assert algo_info["rsd_algorithm_support"] is True
        assert algo_info["algorithm_count"] >= 1  # At least RSD computation

    @pytest.mark.asyncio
    async def test_get_introspection_data_with_custom_algorithms(self, node_compute):
        """Test introspection includes custom registered algorithms."""

        def custom_algo(data: dict[str, Any]) -> int:
            return 42

        node_compute.register_computation("custom_algorithm", custom_algo)

        introspection = await node_compute.get_introspection_data()
        algo_info = introspection["algorithm_information"]

        assert "custom_algorithm" in algo_info["registered_algorithms"]
        assert algo_info["algorithm_count"] >= 2  # RSD + custom

    @pytest.mark.asyncio
    async def test_extract_compute_operations(self, node_compute):
        """Test extraction of available compute operations."""
        operations = node_compute._extract_compute_operations()

        assert "process" in operations
        assert "calculate_rsd_priority" in operations
        assert "register_computation" in operations
        assert "get_computation_metrics" in operations

    def test_extract_compute_io_specifications(self, node_compute):
        """Test extraction of I/O specifications."""
        io_specs = node_compute._extract_compute_io_specifications()

        assert io_specs["supports_batch_processing"] is True
        assert io_specs["supports_parallel_processing"] is True
        assert io_specs["supports_streaming"] is False
        assert "data" in io_specs["input_requirements"]
        assert "computation_type" in io_specs["input_requirements"]

    def test_extract_compute_performance_characteristics(self, node_compute):
        """Test extraction of performance characteristics."""
        perf_chars = node_compute._extract_compute_performance_characteristics()

        assert perf_chars["supports_parallel_processing"] is True
        assert perf_chars["caching_enabled"] is True
        assert perf_chars["deterministic_operations"] is True
        assert perf_chars["side_effects"] is False

    def test_get_compute_health_status_healthy(self, node_compute):
        """Test health status reporting when node is healthy."""
        health = node_compute._get_compute_health_status()

        assert health == "healthy"

    def test_get_compute_resource_usage(self, node_compute):
        """Test resource usage reporting."""
        usage = node_compute._get_compute_resource_usage()

        assert "cache_utilization" in usage
        assert "thread_pool_status" in usage
        assert "parallel_worker_count" in usage
        assert "registered_algorithms" in usage

    def test_get_caching_status(self, node_compute):
        """Test caching status reporting."""
        caching = node_compute._get_caching_status()

        assert caching["enabled"] is True
        assert "cache_stats" in caching
        assert caching["ttl_minutes"] == 30
        assert caching["eviction_policy"] == "lru"

    def test_get_parallel_processing_status(self, node_compute):
        """Test parallel processing status reporting."""
        parallel = node_compute._get_parallel_processing_status()

        assert parallel["enabled"] is True
        assert parallel["max_workers"] == 4
        assert parallel["supports_async_processing"] is True


class TestNodeComputeEdgeCases:
    """Test NodeCompute edge cases and error scenarios."""

    @pytest.fixture
    def node_compute(self):
        """Create NodeCompute instance for testing."""
        container = ModelONEXContainer()

        with patch.object(NodeCompute, "_load_contract_model") as mock_load_contract:
            mock_contract = Mock()
            mock_contract.node_type = "compute"
            mock_contract.version = "1.0.0"
            mock_load_contract.return_value = mock_contract

            return NodeCompute(container)

    @pytest.mark.asyncio
    async def test_process_with_none_result(self, node_compute):
        """Test process handles None results correctly."""

        def none_computation(data: dict[str, Any]) -> None:
            return None

        node_compute.register_computation("none_test", none_computation)

        input_data = ModelComputeInput(
            data={"value": 1}, computation_type="none_test", cache_enabled=False
        )

        output = await node_compute.process(input_data)

        assert output.result is None
        assert output.processing_time_ms >= 0

    @pytest.mark.asyncio
    async def test_process_with_empty_data(self, node_compute):
        """Test process with empty data dict."""

        def empty_computation(data: dict[str, Any]) -> str:
            return "empty_result"

        node_compute.register_computation("empty_test", empty_computation)

        input_data = ModelComputeInput(
            data={}, computation_type="empty_test", cache_enabled=False
        )

        output = await node_compute.process(input_data)

        assert output.result == "empty_result"

    @pytest.mark.asyncio
    async def test_rsd_priority_with_zero_values(self, node_compute):
        """Test RSD calculation with all zero values including user_override."""
        ticket_id = uuid4()

        priority = await node_compute.calculate_rsd_priority(
            ticket_id,
            dependency_count=0,
            failure_indicators=0,
            days_old=0.0,
            agent_requests=0,
            user_override_score=0.0,
        )

        # Even with all zeros, time_score = 0.1 for days_old=0
        # Total = 0.15*0.1*100 = 1.5
        assert priority == 1.5

    @pytest.mark.asyncio
    async def test_rsd_priority_with_negative_values(self, node_compute):
        """Test RSD calculation with negative values (current behavior allows negatives)."""
        ticket_id = uuid4()

        # Note: Current implementation does NOT clamp negative values
        # Only user_override_score is clamped via max(0, min(1, value))
        priority = await node_compute.calculate_rsd_priority(
            ticket_id,
            dependency_count=-5,
            failure_indicators=-2,
            days_old=-10.0,
            agent_requests=-3,
            user_override_score=-0.5,  # Only this gets clamped to 0
        )

        # Current behavior produces negative priority
        # This documents actual behavior, not ideal behavior
        assert priority < 0.0  # Negative inputs produce negative output
        assert -50.0 <= priority <= 0.0  # Reasonable bounds for negative case

    @pytest.mark.asyncio
    async def test_introspection_data_fallback_on_error(self, node_compute):
        """Test introspection provides fallback data on errors."""
        # Force an error by breaking a method called during introspection
        with patch.object(
            node_compute,
            "_extract_algorithm_configuration",
            side_effect=Exception("Introspection error"),
        ):
            introspection = await node_compute.get_introspection_data()

            # Should still return minimal fallback data
            assert "node_capabilities" in introspection
            assert "runtime_information" in introspection
            assert "introspection_metadata" in introspection

            # Check that it used fallback
            capabilities = introspection["node_capabilities"]
            assert capabilities["node_type"] == "NodeCompute"
            assert capabilities["node_classification"] == "compute"

            metadata = introspection["introspection_metadata"]
            assert metadata["supports_full_introspection"] is False
            assert "fallback_reason" in metadata

    def test_resolve_contract_references_error_fallback(self, node_compute):
        """Test contract reference resolution returns None on error."""
        # Create mock reference resolver
        reference_resolver = Mock()
        reference_resolver.resolve_reference = Mock(
            side_effect=Exception("Reference resolution failed")
        )

        base_path = Path("/tmp")

        # Create data that will cause an error during resolution
        data = {"$ref": "/nonexistent/file.yaml"}

        result = node_compute._resolve_contract_references(
            data, base_path, reference_resolver
        )

        # Should return None on error (fallback behavior)
        assert result is None

    def test_get_compute_health_status_unhealthy(self, node_compute):
        """Test health status returns unhealthy when validation fails."""
        # Break validation to make health check fail
        with patch.object(
            node_compute,
            "_validate_compute_input",
            side_effect=Exception("Validation failed"),
        ):
            health = node_compute._get_compute_health_status()

            assert health == "unhealthy"

    def test_get_compute_resource_usage_error_fallback(self, node_compute):
        """Test resource usage returns unknown status on error."""
        # Break cache stats to trigger error
        with patch.object(
            node_compute.computation_cache,
            "get_stats",
            side_effect=Exception("Cache error"),
        ):
            usage = node_compute._get_compute_resource_usage()

            assert usage == {"status": "unknown"}

    def test_get_caching_status_error_fallback(self, node_compute):
        """Test caching status returns disabled with error on failure."""
        # Break cache stats to trigger error
        with patch.object(
            node_compute.computation_cache,
            "get_stats",
            side_effect=Exception("Cache stats error"),
        ):
            caching = node_compute._get_caching_status()

            assert caching["enabled"] is False
            assert "error" in caching
            assert "Cache stats error" in caching["error"]

    def test_get_computation_metrics_sync_error_fallback(self, node_compute):
        """Test computation metrics returns unknown status on error."""
        # Break cache stats to trigger error in metrics collection
        with patch.object(
            node_compute.computation_cache,
            "get_stats",
            side_effect=Exception("Metrics error"),
        ):
            metrics = node_compute._get_computation_metrics_sync()

            assert metrics["status"] == "unknown"
            assert "error" in metrics
            assert "Metrics error" in metrics["error"]

    def test_extract_algorithm_configuration_error_fallback(self, node_compute):
        """Test algorithm configuration extraction returns default on error."""
        # Remove algorithm attribute to trigger error
        delattr(node_compute.contract_model, "algorithm")

        config = node_compute._extract_algorithm_configuration()

        assert config == {"algorithm_type": "default_compute"}

    def test_extract_compute_operations_error_handling(self, node_compute):
        """Test compute operations extraction handles registry errors."""
        # Break computation_registry to trigger exception handling
        with patch.object(
            node_compute,
            "computation_registry",
            side_effect=Exception("Registry error"),
        ):
            operations = node_compute._extract_compute_operations()

            # Should still return base operations
            assert "process" in operations
            assert "calculate_rsd_priority" in operations
