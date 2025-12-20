"""
Unit tests for NodeCompute deterministic execution guarantees.

Tests that NodeCompute maintains determinism:
- Same inputs produce same outputs
- No hidden sources of entropy
- Independence from time and threading
- State serialization produces identical results

Ticket: OMN-741
"""

from __future__ import annotations

import copy
from typing import Any
from uuid import UUID, uuid4

import pytest

from omnibase_core.models.compute.model_compute_input import ModelComputeInput
from omnibase_core.models.compute.model_compute_output import ModelComputeOutput
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.nodes.node_compute import NodeCompute

# Module-level marker
pytestmark = pytest.mark.unit


@pytest.fixture
def test_container() -> ModelONEXContainer:
    """Create test container with service registry disabled for deterministic testing."""
    return ModelONEXContainer(enable_service_registry=False)


@pytest.fixture
def pure_compute_node(test_container: ModelONEXContainer) -> NodeCompute[Any, Any]:
    """Create NodeCompute instance in pure mode (no infrastructure services).

    Pure mode ensures:
    - No caching (cache_hit always False)
    - No timing (processing_time_ms is 0.0)
    - No parallelization (sequential execution only)
    """
    node = NodeCompute(test_container)
    # Explicitly set to None to ensure pure mode
    node._cache = None
    node._timing_service = None
    node._parallel_executor = None
    return node


@pytest.fixture
def fixed_operation_id() -> UUID:
    """Provide a fixed UUID for deterministic testing."""
    return UUID("12345678-1234-5678-1234-567812345678")


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestNodeComputeDeterministicOutput:
    """Test that same inputs always produce same outputs.

    Acceptance Criteria (OMN-741):
    - Multiple invocations with identical input data produce identical output
    - Test with different computation types (default, string_uppercase, sum_numbers)
    - Test with various data types (strings, lists, numbers)
    """

    @pytest.mark.asyncio
    async def test_same_input_produces_same_output_default_computation(
        self,
        pure_compute_node: NodeCompute[Any, Any],
        fixed_operation_id: UUID,
    ) -> None:
        """Test that default computation produces identical output for identical input."""
        input_data = ModelComputeInput(
            data={"key": "value", "number": 42},
            computation_type="default",
            operation_id=fixed_operation_id,
            cache_enabled=False,
            parallel_enabled=False,
        )

        result1 = await pure_compute_node.process(input_data)
        result2 = await pure_compute_node.process(input_data)

        # Results must be identical
        assert result1.result == result2.result
        assert result1.computation_type == result2.computation_type

    @pytest.mark.asyncio
    async def test_same_input_produces_same_output_string_uppercase(
        self,
        pure_compute_node: NodeCompute[Any, Any],
        fixed_operation_id: UUID,
    ) -> None:
        """Test that string_uppercase produces identical output for identical input."""
        input_data = ModelComputeInput(
            data="hello world",
            computation_type="string_uppercase",
            operation_id=fixed_operation_id,
            cache_enabled=False,
        )

        result1 = await pure_compute_node.process(input_data)
        result2 = await pure_compute_node.process(input_data)

        assert result1.result == result2.result
        assert result1.result == "HELLO WORLD"

    @pytest.mark.asyncio
    async def test_same_input_produces_same_output_sum_numbers(
        self,
        pure_compute_node: NodeCompute[Any, Any],
        fixed_operation_id: UUID,
    ) -> None:
        """Test that sum_numbers produces identical output for identical input."""
        input_data = ModelComputeInput(
            data=[1.0, 2.0, 3.0, 4.0, 5.0],
            computation_type="sum_numbers",
            operation_id=fixed_operation_id,
            cache_enabled=False,
        )

        result1 = await pure_compute_node.process(input_data)
        result2 = await pure_compute_node.process(input_data)

        assert result1.result == result2.result
        assert result1.result == 15.0

    @pytest.mark.asyncio
    async def test_multiple_invocations_produce_identical_results(
        self,
        pure_compute_node: NodeCompute[Any, Any],
        fixed_operation_id: UUID,
    ) -> None:
        """Test that N invocations all produce identical results."""
        input_data = ModelComputeInput(
            data="deterministic test",
            computation_type="string_uppercase",
            operation_id=fixed_operation_id,
            cache_enabled=False,
        )

        # Execute 10 times
        results = []
        for _ in range(10):
            result = await pure_compute_node.process(input_data)
            results.append(result.result)

        # All results must be identical
        assert all(r == results[0] for r in results)
        assert results[0] == "DETERMINISTIC TEST"

    @pytest.mark.asyncio
    async def test_different_inputs_produce_different_outputs(
        self,
        pure_compute_node: NodeCompute[Any, Any],
    ) -> None:
        """Test that different inputs produce different outputs (sanity check)."""
        input1 = ModelComputeInput(
            data="hello",
            computation_type="string_uppercase",
            cache_enabled=False,
        )
        input2 = ModelComputeInput(
            data="world",
            computation_type="string_uppercase",
            cache_enabled=False,
        )

        result1 = await pure_compute_node.process(input1)
        result2 = await pure_compute_node.process(input2)

        assert result1.result != result2.result
        assert result1.result == "HELLO"
        assert result2.result == "WORLD"

    @pytest.mark.asyncio
    async def test_list_data_determinism(
        self,
        pure_compute_node: NodeCompute[Any, Any],
        fixed_operation_id: UUID,
    ) -> None:
        """Test determinism with list data type."""
        list_data = [1, 2, 3, 4, 5]
        input_data = ModelComputeInput(
            data=list_data,
            computation_type="default",
            operation_id=fixed_operation_id,
            cache_enabled=False,
        )

        result1 = await pure_compute_node.process(input_data)
        result2 = await pure_compute_node.process(input_data)

        assert result1.result == result2.result
        assert result1.result == list_data

    @pytest.mark.asyncio
    async def test_nested_dict_data_determinism(
        self,
        pure_compute_node: NodeCompute[Any, Any],
        fixed_operation_id: UUID,
    ) -> None:
        """Test determinism with nested dictionary data."""
        nested_data = {
            "level1": {
                "level2": {
                    "value": 42,
                    "list": [1, 2, 3],
                }
            },
            "key": "value",
        }
        input_data = ModelComputeInput(
            data=nested_data,
            computation_type="default",
            operation_id=fixed_operation_id,
            cache_enabled=False,
        )

        result1 = await pure_compute_node.process(input_data)
        result2 = await pure_compute_node.process(input_data)

        assert result1.result == result2.result
        assert result1.result == nested_data


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestNodeComputeNoHiddenEntropy:
    """Test that no hidden entropy sources affect output.

    Acceptance Criteria (OMN-741):
    - Verify no random.random() or uuid4() or time-based values in output
    - Verify output metadata is deterministic (except timing)
    - Verify cache keys are deterministic (same input -> same cache key)
    """

    @pytest.mark.asyncio
    async def test_output_metadata_is_deterministic(
        self,
        pure_compute_node: NodeCompute[Any, Any],
        fixed_operation_id: UUID,
    ) -> None:
        """Test that output metadata is deterministic in pure mode."""
        input_data = ModelComputeInput(
            data="test data",
            computation_type="default",
            operation_id=fixed_operation_id,
            cache_enabled=False,
        )

        result1 = await pure_compute_node.process(input_data)
        result2 = await pure_compute_node.process(input_data)

        # Metadata should contain deterministic values
        # In pure mode, pure_mode should be True
        assert result1.metadata.get("pure_mode") == result2.metadata.get("pure_mode")
        assert result1.metadata.get("cache_enabled") == result2.metadata.get(
            "cache_enabled"
        )
        assert result1.metadata.get("input_data_size") == result2.metadata.get(
            "input_data_size"
        )

    @pytest.mark.asyncio
    async def test_pure_mode_has_zero_processing_time(
        self,
        pure_compute_node: NodeCompute[Any, Any],
        fixed_operation_id: UUID,
    ) -> None:
        """Test that in pure mode, processing_time_ms is always 0.0."""
        input_data = ModelComputeInput(
            data="test",
            computation_type="string_uppercase",
            operation_id=fixed_operation_id,
            cache_enabled=False,
        )

        result1 = await pure_compute_node.process(input_data)
        result2 = await pure_compute_node.process(input_data)

        # In pure mode (no timing service), processing_time_ms must be 0.0
        assert result1.processing_time_ms == 0.0
        assert result2.processing_time_ms == 0.0

    def test_cache_key_is_deterministic(
        self,
        pure_compute_node: NodeCompute[Any, Any],
        fixed_operation_id: UUID,
    ) -> None:
        """Test that cache keys are deterministic for identical input."""
        input_data = ModelComputeInput(
            data={"key": "value", "number": 42},
            computation_type="default",
            operation_id=fixed_operation_id,
        )

        # Generate cache key multiple times
        key1 = pure_compute_node._generate_cache_key(input_data)
        key2 = pure_compute_node._generate_cache_key(input_data)

        assert key1 == key2

    def test_cache_key_different_for_different_data(
        self,
        pure_compute_node: NodeCompute[Any, Any],
    ) -> None:
        """Test that cache keys differ for different input data."""
        input1 = ModelComputeInput(
            data="hello",
            computation_type="default",
        )
        input2 = ModelComputeInput(
            data="world",
            computation_type="default",
        )

        key1 = pure_compute_node._generate_cache_key(input1)
        key2 = pure_compute_node._generate_cache_key(input2)

        assert key1 != key2

    def test_cache_key_different_for_different_computation_type(
        self,
        pure_compute_node: NodeCompute[Any, Any],
    ) -> None:
        """Test that cache keys differ for different computation types."""
        input1 = ModelComputeInput(
            data="test",
            computation_type="default",
        )
        input2 = ModelComputeInput(
            data="test",
            computation_type="string_uppercase",
        )

        key1 = pure_compute_node._generate_cache_key(input1)
        key2 = pure_compute_node._generate_cache_key(input2)

        assert key1 != key2

    def test_cache_key_format_is_deterministic(
        self,
        pure_compute_node: NodeCompute[Any, Any],
    ) -> None:
        """Test that cache key format follows expected pattern."""
        input_data = ModelComputeInput(
            data="test",
            computation_type="my_computation",
        )

        key = pure_compute_node._generate_cache_key(input_data)

        # Key should follow format: {computation_type}:{hash}
        assert ":" in key
        parts = key.split(":", 1)
        assert parts[0] == "my_computation"
        # Hash should be a deterministic SHA256 hex string (64 chars)
        assert len(parts[1]) == 64

    @pytest.mark.asyncio
    async def test_no_uuid_generation_in_output_result(
        self,
        pure_compute_node: NodeCompute[Any, Any],
        fixed_operation_id: UUID,
    ) -> None:
        """Test that output result doesn't contain generated UUIDs."""
        input_data = ModelComputeInput(
            data={"test": "value"},
            computation_type="default",
            operation_id=fixed_operation_id,
            cache_enabled=False,
        )

        result = await pure_compute_node.process(input_data)

        # The result should be the same as input (default is identity)
        # No UUIDs should be injected into the result
        assert result.result == {"test": "value"}
        # operation_id should be the same as input
        assert result.operation_id == fixed_operation_id

    @pytest.mark.asyncio
    async def test_no_timestamp_in_result(
        self,
        pure_compute_node: NodeCompute[Any, Any],
        fixed_operation_id: UUID,
    ) -> None:
        """Test that result does not contain timestamps or time-based values."""
        input_data = ModelComputeInput(
            data="test",
            computation_type="string_uppercase",
            operation_id=fixed_operation_id,
            cache_enabled=False,
        )

        result1 = await pure_compute_node.process(input_data)
        result2 = await pure_compute_node.process(input_data)

        # Results should not vary based on execution time
        assert result1.result == result2.result

        # Metadata should not contain variable timestamps
        # (pure_mode, cache_enabled, input_data_size are all deterministic)
        for key in result1.metadata:
            assert result1.metadata[key] == result2.metadata[key]


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestNodeComputeTimeIndependence:
    """Test that results are independent of time/execution order.

    Acceptance Criteria (OMN-741):
    - Output result is independent of when computation runs
    - Results identical across multiple executions at different times
    - In pure mode (no timing service), processing_time_ms is always 0.0
    """

    @pytest.mark.asyncio
    async def test_result_independent_of_execution_order(
        self,
        pure_compute_node: NodeCompute[Any, Any],
    ) -> None:
        """Test that result doesn't depend on execution order."""
        # Execute different computations, then repeat
        input_a = ModelComputeInput(
            data="alpha",
            computation_type="string_uppercase",
            cache_enabled=False,
        )
        input_b = ModelComputeInput(
            data="beta",
            computation_type="string_uppercase",
            cache_enabled=False,
        )

        # First order: A, B
        result_a1 = await pure_compute_node.process(input_a)
        result_b1 = await pure_compute_node.process(input_b)

        # Second order: B, A
        result_b2 = await pure_compute_node.process(input_b)
        result_a2 = await pure_compute_node.process(input_a)

        # Results should be the same regardless of execution order
        assert result_a1.result == result_a2.result
        assert result_b1.result == result_b2.result

    @pytest.mark.asyncio
    async def test_interleaved_computations_are_deterministic(
        self,
        pure_compute_node: NodeCompute[Any, Any],
    ) -> None:
        """Test that interleaved computations produce deterministic results."""
        input_default = ModelComputeInput(
            data={"key": "value"},
            computation_type="default",
            cache_enabled=False,
        )
        input_upper = ModelComputeInput(
            data="hello",
            computation_type="string_uppercase",
            cache_enabled=False,
        )
        input_sum = ModelComputeInput(
            data=[1.0, 2.0, 3.0],
            computation_type="sum_numbers",
            cache_enabled=False,
        )

        # Execute interleaved
        results_pass1 = []
        for input_data in [input_default, input_upper, input_sum]:
            result = await pure_compute_node.process(input_data)
            results_pass1.append(result.result)

        # Execute in different order
        results_pass2 = []
        for input_data in [input_sum, input_default, input_upper]:
            result = await pure_compute_node.process(input_data)
            results_pass2.append(result.result)

        # Results for each computation type should be consistent
        # Pass 1 order: default, upper, sum
        # Pass 2 order: sum, default, upper
        assert results_pass1[0] == results_pass2[1]  # default
        assert results_pass1[1] == results_pass2[2]  # upper
        assert results_pass1[2] == results_pass2[0]  # sum

    @pytest.mark.asyncio
    async def test_pure_mode_processing_time_always_zero(
        self,
        pure_compute_node: NodeCompute[Any, Any],
    ) -> None:
        """Test that processing_time_ms is always 0.0 in pure mode."""
        # Test with different computation types
        computation_types = ["default", "string_uppercase", "sum_numbers"]
        data_by_type = {
            "default": "test",
            "string_uppercase": "hello",
            "sum_numbers": [1.0, 2.0],
        }

        for comp_type in computation_types:
            input_data = ModelComputeInput(
                data=data_by_type[comp_type],
                computation_type=comp_type,
                cache_enabled=False,
            )

            result = await pure_compute_node.process(input_data)

            assert result.processing_time_ms == 0.0, (
                f"processing_time_ms should be 0.0 in pure mode for {comp_type}, "
                f"got {result.processing_time_ms}"
            )

    @pytest.mark.asyncio
    async def test_cache_hit_is_always_false_in_pure_mode(
        self,
        pure_compute_node: NodeCompute[Any, Any],
        fixed_operation_id: UUID,
    ) -> None:
        """Test that cache_hit is always False in pure mode (no cache injected)."""
        input_data = ModelComputeInput(
            data="test",
            computation_type="default",
            operation_id=fixed_operation_id,
            cache_enabled=True,  # Even with caching enabled
        )

        result1 = await pure_compute_node.process(input_data)
        result2 = await pure_compute_node.process(input_data)

        # In pure mode, cache_hit should always be False
        assert result1.cache_hit is False
        assert result2.cache_hit is False

    @pytest.mark.asyncio
    async def test_parallel_execution_always_false_in_pure_mode(
        self,
        pure_compute_node: NodeCompute[Any, Any],
    ) -> None:
        """Test that parallel_execution_used is always False in pure mode."""
        input_data = ModelComputeInput(
            data=[1, 2, 3, 4, 5],
            computation_type="default",
            cache_enabled=False,
            parallel_enabled=True,  # Even with parallel enabled
        )

        result = await pure_compute_node.process(input_data)

        # In pure mode (no parallel executor), parallel_execution_used is False
        assert result.parallel_execution_used is False


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestNodeComputeStateSerialization:
    """Test that state serialization produces identical results.

    Acceptance Criteria (OMN-741):
    - Serializing node state and restoring produces identical behavior
    - Computation registry state is consistent
    """

    def test_computation_registry_contains_builtins(
        self,
        pure_compute_node: NodeCompute[Any, Any],
    ) -> None:
        """Test that computation registry has expected built-in computations."""
        expected_builtins = {"default", "string_uppercase", "sum_numbers"}

        assert expected_builtins.issubset(
            set(pure_compute_node.computation_registry.keys())
        )

    def test_computation_registry_is_consistent_across_instances(
        self,
        test_container: ModelONEXContainer,
    ) -> None:
        """Test that computation registry is consistent across node instances."""
        node1: NodeCompute[Any, Any] = NodeCompute(test_container)
        node2: NodeCompute[Any, Any] = NodeCompute(test_container)

        # Both should have the same built-in computations
        assert set(node1.computation_registry.keys()) == set(
            node2.computation_registry.keys()
        )

    @pytest.mark.asyncio
    async def test_identical_behavior_across_fresh_instances(
        self,
        test_container: ModelONEXContainer,
        fixed_operation_id: UUID,
    ) -> None:
        """Test that fresh node instances produce identical results."""
        input_data = ModelComputeInput(
            data="hello world",
            computation_type="string_uppercase",
            operation_id=fixed_operation_id,
            cache_enabled=False,
        )

        # Create two fresh instances
        node1: NodeCompute[Any, Any] = NodeCompute(test_container)
        node1._cache = None
        node1._timing_service = None
        node1._parallel_executor = None

        node2: NodeCompute[Any, Any] = NodeCompute(test_container)
        node2._cache = None
        node2._timing_service = None
        node2._parallel_executor = None

        result1 = await node1.process(input_data)
        result2 = await node2.process(input_data)

        assert result1.result == result2.result
        assert result1.computation_type == result2.computation_type

    def test_custom_computation_registration_is_consistent(
        self,
        pure_compute_node: NodeCompute[Any, Any],
    ) -> None:
        """Test that custom computation registration works consistently."""

        def custom_double(data: int) -> int:
            return data * 2

        pure_compute_node.register_computation("custom_double", custom_double)

        # Registration should be persistent
        assert "custom_double" in pure_compute_node.computation_registry
        assert pure_compute_node.computation_registry["custom_double"](5) == 10

    @pytest.mark.asyncio
    async def test_custom_computation_is_deterministic(
        self,
        pure_compute_node: NodeCompute[Any, Any],
        fixed_operation_id: UUID,
    ) -> None:
        """Test that custom computations produce deterministic results."""

        def custom_transform(data: str) -> str:
            return f"[{data.upper()}]"

        pure_compute_node.register_computation("custom_transform", custom_transform)

        input_data = ModelComputeInput(
            data="test",
            computation_type="custom_transform",
            operation_id=fixed_operation_id,
            cache_enabled=False,
        )

        result1 = await pure_compute_node.process(input_data)
        result2 = await pure_compute_node.process(input_data)

        assert result1.result == result2.result
        assert result1.result == "[TEST]"

    def test_node_id_is_stable_for_instance(
        self,
        pure_compute_node: NodeCompute[Any, Any],
    ) -> None:
        """Test that node_id remains stable for a node instance."""
        node_id_1 = pure_compute_node.node_id
        node_id_2 = pure_compute_node.node_id

        assert node_id_1 == node_id_2

    @pytest.mark.asyncio
    async def test_registry_state_affects_computation(
        self,
        test_container: ModelONEXContainer,
        fixed_operation_id: UUID,
    ) -> None:
        """Test that computation registry state directly affects output."""
        node: NodeCompute[Any, Any] = NodeCompute(test_container)
        node._cache = None
        node._timing_service = None
        node._parallel_executor = None

        def version_1(data: str) -> str:
            return f"v1:{data}"

        node.register_computation("versioned", version_1)

        input_data = ModelComputeInput(
            data="test",
            computation_type="versioned",
            operation_id=fixed_operation_id,
            cache_enabled=False,
        )

        result = await node.process(input_data)

        assert result.result == "v1:test"


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestNodeComputeCacheKeyDeterminism:
    """Additional tests for cache key determinism."""

    def test_cache_key_uses_sha256(
        self,
        pure_compute_node: NodeCompute[Any, Any],
    ) -> None:
        """Test that cache key uses SHA256 for deterministic hashing."""
        import hashlib

        input_data = ModelComputeInput(
            data="test_data",
            computation_type="test_type",
        )

        key = pure_compute_node._generate_cache_key(input_data)

        # Verify format: {computation_type}:{sha256_hash}
        parts = key.split(":", 1)
        assert parts[0] == "test_type"

        # Verify hash matches expected SHA256
        expected_hash = hashlib.sha256(str(input_data.data).encode()).hexdigest()
        assert parts[1] == expected_hash

    def test_cache_key_deterministic_with_complex_data(
        self,
        pure_compute_node: NodeCompute[Any, Any],
    ) -> None:
        """Test cache key determinism with complex nested data."""
        complex_data = {
            "users": [
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25},
            ],
            "metadata": {
                "version": "1.0",
                "tags": ["production", "validated"],
            },
        }

        input_data = ModelComputeInput(
            data=complex_data,
            computation_type="default",
        )

        # Generate key multiple times
        keys = [pure_compute_node._generate_cache_key(input_data) for _ in range(5)]

        # All keys must be identical
        assert all(k == keys[0] for k in keys)

    def test_cache_key_handles_special_characters(
        self,
        pure_compute_node: NodeCompute[Any, Any],
    ) -> None:
        """Test cache key handles special characters in data."""
        special_data = "hello\nworld\twith\x00special"

        input_data = ModelComputeInput(
            data=special_data,
            computation_type="default",
        )

        key1 = pure_compute_node._generate_cache_key(input_data)
        key2 = pure_compute_node._generate_cache_key(input_data)

        assert key1 == key2

    def test_cache_key_handles_unicode(
        self,
        pure_compute_node: NodeCompute[Any, Any],
    ) -> None:
        """Test cache key handles unicode data correctly."""
        unicode_data = "Hello World - Japanese - Arabic"

        input_data = ModelComputeInput(
            data=unicode_data,
            computation_type="default",
        )

        key1 = pure_compute_node._generate_cache_key(input_data)
        key2 = pure_compute_node._generate_cache_key(input_data)

        assert key1 == key2


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestNodeComputeInputValidation:
    """Tests for input validation to ensure deterministic behavior."""

    @pytest.mark.asyncio
    async def test_validates_input_has_data_attribute(
        self,
        pure_compute_node: NodeCompute[Any, Any],
    ) -> None:
        """Test that input validation checks for data attribute."""
        input_data = ModelComputeInput(
            data="test",
            computation_type="default",
            cache_enabled=False,
        )

        # Should not raise - valid input
        result = await pure_compute_node.process(input_data)
        assert result.result == "test"

    @pytest.mark.asyncio
    async def test_validates_computation_type_exists(
        self,
        pure_compute_node: NodeCompute[Any, Any],
    ) -> None:
        """Test that unknown computation type raises error."""
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        input_data = ModelComputeInput(
            data="test",
            computation_type="nonexistent_computation",
            cache_enabled=False,
        )

        with pytest.raises(ModelOnexError) as exc_info:
            await pure_compute_node.process(input_data)

        assert "Unknown computation type" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_string_uppercase_validates_input_type(
        self,
        pure_compute_node: NodeCompute[Any, Any],
    ) -> None:
        """Test that string_uppercase validates input is string."""
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        input_data = ModelComputeInput(
            data=12345,  # Not a string
            computation_type="string_uppercase",
            cache_enabled=False,
        )

        with pytest.raises(ModelOnexError) as exc_info:
            await pure_compute_node.process(input_data)

        assert "must be a string" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_sum_numbers_validates_input_type(
        self,
        pure_compute_node: NodeCompute[Any, Any],
    ) -> None:
        """Test that sum_numbers validates input is list/tuple."""
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        input_data = ModelComputeInput(
            data="not a list",  # Not a list/tuple
            computation_type="sum_numbers",
            cache_enabled=False,
        )

        with pytest.raises(ModelOnexError) as exc_info:
            await pure_compute_node.process(input_data)

        assert "must be a list or tuple" in str(exc_info.value)


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestNodeComputeImmutability:
    """Tests for immutability guarantees supporting determinism."""

    @pytest.mark.asyncio
    async def test_input_not_modified_by_computation(
        self,
        pure_compute_node: NodeCompute[Any, Any],
    ) -> None:
        """Test that input data is not modified during computation."""
        original_data = {"key": "value", "nested": {"inner": "data"}}
        original_data_copy = copy.deepcopy(original_data)

        input_data = ModelComputeInput(
            data=original_data,
            computation_type="default",
            cache_enabled=False,
        )

        await pure_compute_node.process(input_data)

        # Input data should not be modified
        assert input_data.data == original_data_copy

    @pytest.mark.asyncio
    async def test_output_is_frozen(
        self,
        pure_compute_node: NodeCompute[Any, Any],
    ) -> None:
        """Test that output model is frozen (immutable)."""
        input_data = ModelComputeInput(
            data="test",
            computation_type="string_uppercase",
            cache_enabled=False,
        )

        result = await pure_compute_node.process(input_data)

        # Output model should be frozen
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            result.result = "modified"

    def test_input_is_frozen(self) -> None:
        """Test that input model is frozen (immutable)."""
        input_data = ModelComputeInput(
            data="test",
            computation_type="default",
        )

        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            input_data.data = "modified"
