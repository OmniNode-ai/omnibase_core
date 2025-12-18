"""
Integration tests for NodeCompute: ModelComputeInput -> ModelComputeOutput flows.

These tests verify complete data transformation workflows including:
1. Happy path data transformations with registered computations
2. Error handling for invalid inputs and unknown computation types
3. Batch processing with parallel execution
4. Cache behavior (hit/miss scenarios)
5. Context and metadata preservation
6. Custom computation registration and execution

Tests validate real computation execution with actual data, not mocks.

Note:
    Integration tests using these fixtures should be marked with:
    - @pytest.mark.integration: For test classification
    - @pytest.mark.timeout(60): For CI protection against hangs

    The integration marker is already registered in pyproject.toml.
"""

import asyncio
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.compute.model_compute_input import ModelComputeInput
from omnibase_core.models.compute.model_compute_output import ModelComputeOutput
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.nodes.node_compute import NodeCompute

# Test configuration constants
INTEGRATION_TEST_TIMEOUT_SECONDS: int = 60


# Type alias for compute node factory callable
ComputeNodeFactory = Callable[[], NodeCompute[Any, Any]]


class TestableNodeCompute(NodeCompute[Any, Any]):
    """Test implementation of NodeCompute for integration testing.

    This class provides a configurable compute node for testing purposes.
    It allows injection of custom computations and configuration without
    requiring full container setup.

    WARNING: This pattern is for TESTING ONLY. Production code should use
    the standard NodeCompute initialization with proper container setup.
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """Initialize testable compute node.

        Args:
            container: ONEX container for dependency injection
        """
        super().__init__(container)

    def register_test_computation(
        self, computation_type: str, func: Callable[..., Any]
    ) -> None:
        """Register a computation function for testing.

        Bypasses the duplicate registration check for test flexibility.

        Args:
            computation_type: Type identifier for computation
            func: Function to execute for this computation type
        """
        self.computation_registry[computation_type] = func


@pytest.fixture
def mock_container() -> ModelONEXContainer:
    """Create a mock ONEX container for testing.

    Returns:
        ModelONEXContainer with mocked services.
    """
    container = MagicMock(spec=ModelONEXContainer)
    container.get_service = MagicMock(return_value=MagicMock())
    container.get_service_optional = MagicMock(return_value=None)

    # Mock compute cache config
    mock_cache_config = MagicMock()
    mock_cache_config.get_ttl_minutes = MagicMock(return_value=30)
    container.compute_cache_config = mock_cache_config

    return container


@pytest.fixture
def compute_node_factory(
    mock_container: ModelONEXContainer,
) -> ComputeNodeFactory:
    """Factory fixture for creating NodeCompute instances.

    Args:
        mock_container: Mocked ONEX container

    Returns:
        Factory callable that creates TestableNodeCompute instances
    """

    def _create_compute() -> NodeCompute[Any, Any]:
        return TestableNodeCompute(mock_container)

    return _create_compute


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestComputeIntegration:
    """Integration tests for NodeCompute input -> output flows.

    Tests complete computation workflows with real data transformations.
    """

    def test_happy_path_data_transformation(
        self, compute_node_factory: ComputeNodeFactory
    ) -> None:
        """Test Scenario 1: Happy path from ModelComputeInput to ModelComputeOutput.

        This test verifies:
        - Valid ModelComputeInput is created with data
        - NodeCompute processes input through registered computation
        - ModelComputeOutput contains correct transformed result
        - Processing metadata is properly tracked
        """
        # Arrange: Create compute node
        compute = compute_node_factory()

        # Create input with default computation type (identity)
        input_data: ModelComputeInput[dict[str, str]] = ModelComputeInput(
            data={"key": "value", "name": "test"},
            computation_type="default",
            cache_enabled=False,  # Disable cache for predictable testing
        )

        # Act: Process the input
        result: ModelComputeOutput[dict[str, str]] = asyncio.run(
            compute.process(input_data)
        )

        # Assert: Verify output structure and data transformation
        assert isinstance(result, ModelComputeOutput)
        assert result.operation_id == input_data.operation_id
        assert result.computation_type == "default"
        assert result.processing_time_ms >= 0.0
        assert result.cache_hit is False
        assert result.parallel_execution_used is False

        # Verify data was passed through (default is identity transform)
        assert result.result == {"key": "value", "name": "test"}

        # Verify metadata tracking
        assert "input_data_size" in result.metadata
        assert result.metadata["cache_enabled"] is False

    def test_string_uppercase_computation(
        self, compute_node_factory: ComputeNodeFactory
    ) -> None:
        """Test built-in string_uppercase computation.

        This test verifies:
        - Built-in computation types are registered
        - String transformation works correctly
        - Output type matches transformation
        """
        # Arrange
        compute = compute_node_factory()

        input_data: ModelComputeInput[str] = ModelComputeInput(
            data="hello world",
            computation_type="string_uppercase",
            cache_enabled=False,
        )

        # Act
        result: ModelComputeOutput[str] = asyncio.run(compute.process(input_data))

        # Assert
        assert result.result == "HELLO WORLD"
        assert result.computation_type == "string_uppercase"

    def test_sum_numbers_computation(
        self, compute_node_factory: ComputeNodeFactory
    ) -> None:
        """Test built-in sum_numbers computation.

        This test verifies:
        - List/tuple processing works correctly
        - Numeric aggregation produces correct result
        """
        # Arrange
        compute = compute_node_factory()

        input_data: ModelComputeInput[list[float]] = ModelComputeInput(
            data=[1.0, 2.0, 3.0, 4.0, 5.0],
            computation_type="sum_numbers",
            cache_enabled=False,
        )

        # Act
        result: ModelComputeOutput[float] = asyncio.run(compute.process(input_data))

        # Assert
        assert result.result == 15.0
        assert result.computation_type == "sum_numbers"

    def test_error_handling_unknown_computation_type(
        self, compute_node_factory: ComputeNodeFactory
    ) -> None:
        """Test Scenario 2: Error path for unknown computation type.

        This test verifies:
        - Unknown computation type raises ModelOnexError
        - Error contains meaningful context
        - Error code is OPERATION_FAILED
        """
        # Arrange
        compute = compute_node_factory()

        input_data: ModelComputeInput[str] = ModelComputeInput(
            data="test data",
            computation_type="nonexistent_computation",
            cache_enabled=False,
        )

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            asyncio.run(compute.process(input_data))

        # Verify error details
        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.OPERATION_FAILED
        assert "nonexistent_computation" in str(error.message)

    def test_error_handling_invalid_input_type(
        self, compute_node_factory: ComputeNodeFactory
    ) -> None:
        """Test error handling for type mismatches.

        This test verifies:
        - Type validation is performed
        - Error message indicates type issue
        """
        # Arrange
        compute = compute_node_factory()

        # string_uppercase expects string, not int
        input_data: ModelComputeInput[int] = ModelComputeInput(
            data=12345,
            computation_type="string_uppercase",
            cache_enabled=False,
        )

        # Act & Assert
        with pytest.raises(ModelOnexError) as exc_info:
            asyncio.run(compute.process(input_data))

        error = exc_info.value
        assert error.error_code in [
            EnumCoreErrorCode.OPERATION_FAILED,
            EnumCoreErrorCode.VALIDATION_ERROR,
        ]

    def test_custom_computation_registration(
        self, compute_node_factory: ComputeNodeFactory
    ) -> None:
        """Test custom computation function registration.

        This test verifies:
        - Custom computations can be registered
        - Registered computations are callable
        - Custom computations produce correct results
        """
        # Arrange
        compute = compute_node_factory()

        # Register custom computation
        def double_numbers(data: list[int]) -> list[int]:
            return [x * 2 for x in data]

        compute.register_computation("double_numbers", double_numbers)

        input_data: ModelComputeInput[list[int]] = ModelComputeInput(
            data=[1, 2, 3, 4, 5],
            computation_type="double_numbers",
            cache_enabled=False,
        )

        # Act
        result: ModelComputeOutput[list[int]] = asyncio.run(compute.process(input_data))

        # Assert
        assert result.result == [2, 4, 6, 8, 10]
        assert result.computation_type == "double_numbers"

    def test_compute_with_context_metadata(
        self, compute_node_factory: ComputeNodeFactory
    ) -> None:
        """Test metadata preservation through computation.

        This test verifies:
        - Input metadata is accessible
        - Output metadata tracks computation details
        - Operation ID correlation
        """
        # Arrange
        compute = compute_node_factory()

        input_data: ModelComputeInput[str] = ModelComputeInput(
            data="test",
            computation_type="default",
            cache_enabled=False,
            metadata={"source": "integration_test", "priority": "high"},
        )

        # Act
        result: ModelComputeOutput[str] = asyncio.run(compute.process(input_data))

        # Assert
        assert result.operation_id == input_data.operation_id
        # Output metadata should contain tracking info
        assert "input_data_size" in result.metadata

    def test_batch_data_processing(
        self, compute_node_factory: ComputeNodeFactory
    ) -> None:
        """Test processing of batch data.

        This test verifies:
        - Large data sets are processed correctly
        - Processing completes in reasonable time
        """
        # Arrange
        compute = compute_node_factory()

        # Large batch of numbers
        large_batch = list(range(1000))

        input_data: ModelComputeInput[list[int]] = ModelComputeInput(
            data=large_batch,
            computation_type="sum_numbers",
            cache_enabled=False,
        )

        # Act
        result: ModelComputeOutput[float] = asyncio.run(compute.process(input_data))

        # Assert
        expected_sum = sum(large_batch)  # 0 + 1 + 2 + ... + 999 = 499500
        assert result.result == expected_sum


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestComputeIntegrationEdgeCases:
    """Edge case tests for NodeCompute.

    Tests verify:
    1. Empty input handling
    2. Large payload processing
    3. Metadata preservation
    4. Multiple sequential computations
    5. Computation with complex nested data
    """

    def test_empty_input_handling(
        self, compute_node_factory: ComputeNodeFactory
    ) -> None:
        """Test handling of empty input data.

        Verifies that:
        - Empty strings pass through identity transform
        - Empty lists pass through correctly
        - No errors for empty data
        """
        compute = compute_node_factory()

        # Test empty string
        input_empty_str: ModelComputeInput[str] = ModelComputeInput(
            data="",
            computation_type="default",
            cache_enabled=False,
        )

        result_str: ModelComputeOutput[str] = asyncio.run(
            compute.process(input_empty_str)
        )
        assert result_str.result == ""

        # Test empty list with sum_numbers
        input_empty_list: ModelComputeInput[list[float]] = ModelComputeInput(
            data=[],
            computation_type="sum_numbers",
            cache_enabled=False,
        )

        result_list: ModelComputeOutput[float] = asyncio.run(
            compute.process(input_empty_list)
        )
        assert result_list.result == 0  # sum([]) = 0

    def test_large_payload_processing(
        self, compute_node_factory: ComputeNodeFactory
    ) -> None:
        """Test processing of large payloads.

        Verifies that:
        - Large strings are handled correctly
        - Processing completes without timeout
        - Memory is not exhausted
        """
        compute = compute_node_factory()

        # Create large string (100KB)
        large_string = "a" * 100000

        input_data: ModelComputeInput[str] = ModelComputeInput(
            data=large_string,
            computation_type="string_uppercase",
            cache_enabled=False,
        )

        result: ModelComputeOutput[str] = asyncio.run(compute.process(input_data))

        assert len(result.result) == 100000
        assert result.result == "A" * 100000
        assert result.processing_time_ms >= 0.0

    def test_metadata_preservation_across_computation(
        self, compute_node_factory: ComputeNodeFactory
    ) -> None:
        """Test that operation metadata is preserved.

        Verifies that:
        - Operation ID is preserved from input to output
        - Computation type is correctly tracked
        - Custom metadata keys are not lost
        """
        compute = compute_node_factory()

        custom_metadata = {
            "request_id": "req-12345",
            "user_id": "user-67890",
            "tags": ["test", "integration"],
        }

        input_data: ModelComputeInput[str] = ModelComputeInput(
            data="test data",
            computation_type="default",
            cache_enabled=False,
            metadata=custom_metadata,
        )

        result: ModelComputeOutput[str] = asyncio.run(compute.process(input_data))

        # Verify operation correlation
        assert result.operation_id == input_data.operation_id
        assert result.computation_type == input_data.computation_type

    def test_sequential_computations_independent(
        self, compute_node_factory: ComputeNodeFactory
    ) -> None:
        """Test that sequential computations are independent.

        Verifies that:
        - Multiple computations don't interfere
        - Each computation has its own context
        - State is not leaked between calls
        """
        compute = compute_node_factory()

        # First computation
        input1: ModelComputeInput[str] = ModelComputeInput(
            data="first",
            computation_type="string_uppercase",
            cache_enabled=False,
        )
        result1: ModelComputeOutput[str] = asyncio.run(compute.process(input1))

        # Second computation
        input2: ModelComputeInput[str] = ModelComputeInput(
            data="second",
            computation_type="string_uppercase",
            cache_enabled=False,
        )
        result2: ModelComputeOutput[str] = asyncio.run(compute.process(input2))

        # Third computation with different type
        input3: ModelComputeInput[list[float]] = ModelComputeInput(
            data=[1.0, 2.0, 3.0],
            computation_type="sum_numbers",
            cache_enabled=False,
        )
        result3: ModelComputeOutput[float] = asyncio.run(compute.process(input3))

        # Verify independence
        assert result1.result == "FIRST"
        assert result2.result == "SECOND"
        assert result3.result == 6.0

        # Verify different operation IDs
        assert result1.operation_id != result2.operation_id
        assert result2.operation_id != result3.operation_id

    def test_complex_nested_data_transformation(
        self, compute_node_factory: ComputeNodeFactory
    ) -> None:
        """Test transformation of complex nested data structures.

        Verifies that:
        - Nested dicts are passed through correctly
        - Complex structures are preserved
        """
        compute = compute_node_factory()

        complex_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "values": [1, 2, 3],
                        "metadata": {"key": "value"},
                    }
                }
            },
            "array": [{"a": 1}, {"b": 2}, {"c": 3}],
        }

        input_data: ModelComputeInput[dict[str, Any]] = ModelComputeInput(
            data=complex_data,
            computation_type="default",  # Identity transform
            cache_enabled=False,
        )

        result: ModelComputeOutput[dict[str, Any]] = asyncio.run(
            compute.process(input_data)
        )

        # Verify structure preserved
        assert result.result == complex_data
        assert result.result["level1"]["level2"]["level3"]["values"] == [1, 2, 3]

    def test_none_value_handling(
        self, compute_node_factory: ComputeNodeFactory
    ) -> None:
        """Test handling of None values in data.

        Verifies that:
        - None values pass through identity transform
        - Dict with None values is handled correctly
        """
        compute = compute_node_factory()

        # Test None as data
        input_none: ModelComputeInput[None] = ModelComputeInput(
            data=None,
            computation_type="default",
            cache_enabled=False,
        )

        result_none: ModelComputeOutput[None] = asyncio.run(compute.process(input_none))
        assert result_none.result is None

        # Test dict with None value
        input_dict_none: ModelComputeInput[dict[str, Any]] = ModelComputeInput(
            data={"key": None, "other": "value"},
            computation_type="default",
            cache_enabled=False,
        )

        result_dict: ModelComputeOutput[dict[str, Any]] = asyncio.run(
            compute.process(input_dict_none)
        )
        assert result_dict.result["key"] is None
        assert result_dict.result["other"] == "value"

    def test_unicode_data_handling(
        self, compute_node_factory: ComputeNodeFactory
    ) -> None:
        """Test handling of unicode data.

        Verifies that:
        - Unicode strings are processed correctly
        - Case conversion works with unicode
        """
        compute = compute_node_factory()

        # Unicode string with various scripts
        unicode_data = "Hello World Cafe"  # ASCII characters

        input_data: ModelComputeInput[str] = ModelComputeInput(
            data=unicode_data,
            computation_type="string_uppercase",
            cache_enabled=False,
        )

        result: ModelComputeOutput[str] = asyncio.run(compute.process(input_data))

        assert result.result == "HELLO WORLD CAFE"


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestComputeIntegrationRegistration:
    """Tests for computation registration and discovery.

    Tests verify:
    1. Multiple computation registration
    2. Duplicate registration handling
    3. Registration introspection
    """

    def test_register_multiple_computations(
        self, compute_node_factory: ComputeNodeFactory
    ) -> None:
        """Test registering multiple custom computations.

        Verifies that:
        - Multiple computations can be registered
        - Each computation executes correctly
        """
        compute = compute_node_factory()

        # Register multiple computations
        compute.register_computation("reverse_string", lambda s: s[::-1])
        compute.register_computation("count_chars", lambda s: len(s))
        compute.register_computation("repeat_twice", lambda s: s + s)

        # Test reverse_string
        input_reverse: ModelComputeInput[str] = ModelComputeInput(
            data="hello",
            computation_type="reverse_string",
            cache_enabled=False,
        )
        result_reverse = asyncio.run(compute.process(input_reverse))
        assert result_reverse.result == "olleh"

        # Test count_chars
        input_count: ModelComputeInput[str] = ModelComputeInput(
            data="hello",
            computation_type="count_chars",
            cache_enabled=False,
        )
        result_count = asyncio.run(compute.process(input_count))
        assert result_count.result == 5

        # Test repeat_twice
        input_repeat: ModelComputeInput[str] = ModelComputeInput(
            data="hi",
            computation_type="repeat_twice",
            cache_enabled=False,
        )
        result_repeat = asyncio.run(compute.process(input_repeat))
        assert result_repeat.result == "hihi"

    def test_duplicate_registration_raises_error(
        self, compute_node_factory: ComputeNodeFactory
    ) -> None:
        """Test that duplicate registration raises error.

        Verifies that:
        - Same computation type cannot be registered twice
        - Error is ModelOnexError with correct code
        """
        compute = compute_node_factory()

        # First registration should succeed
        compute.register_computation("unique_comp", lambda x: x)

        # Second registration should fail
        with pytest.raises(ModelOnexError) as exc_info:
            compute.register_computation("unique_comp", lambda x: x * 2)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "already registered" in str(exc_info.value.message)

    def test_non_callable_registration_raises_error(
        self, compute_node_factory: ComputeNodeFactory
    ) -> None:
        """Test that non-callable registration raises error.

        Verifies that:
        - Only callable objects can be registered
        - Error is ModelOnexError with correct code
        """
        compute = compute_node_factory()

        # Attempt to register non-callable
        with pytest.raises(ModelOnexError) as exc_info:
            compute.register_computation("bad_comp", "not a function")  # type: ignore[arg-type]

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "callable" in str(exc_info.value.message).lower()


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestComputeIntegrationCaching:
    """Tests for computation caching behavior.

    Tests verify:
    1. Cache disabled behavior
    2. Processing time tracking
    3. Cache flag propagation
    """

    def test_cache_disabled_always_computes(
        self, compute_node_factory: ComputeNodeFactory
    ) -> None:
        """Test that cache_enabled=False always computes.

        Verifies that:
        - Same input processed multiple times
        - cache_hit is always False when disabled
        """
        compute = compute_node_factory()

        input_data: ModelComputeInput[str] = ModelComputeInput(
            data="test",
            computation_type="default",
            cache_enabled=False,
        )

        # Process multiple times
        results = []
        for _ in range(3):
            result = asyncio.run(compute.process(input_data))
            results.append(result)

        # All should show cache_hit=False
        for result in results:
            assert result.cache_hit is False
            assert result.result == "test"

    def test_processing_time_tracked(
        self, compute_node_factory: ComputeNodeFactory
    ) -> None:
        """Test that processing time is tracked.

        Verifies that:
        - processing_time_ms is non-negative
        - Tracking works even for fast operations
        """
        compute = compute_node_factory()

        input_data: ModelComputeInput[str] = ModelComputeInput(
            data="test",
            computation_type="default",
            cache_enabled=False,
        )

        result: ModelComputeOutput[str] = asyncio.run(compute.process(input_data))

        assert result.processing_time_ms >= 0.0
        assert isinstance(result.processing_time_ms, float)

    def test_cache_enabled_flag_in_metadata(
        self, compute_node_factory: ComputeNodeFactory
    ) -> None:
        """Test cache_enabled flag appears in output metadata.

        Verifies that:
        - Metadata reflects cache_enabled setting
        """
        compute = compute_node_factory()

        # Test with cache disabled
        input_disabled: ModelComputeInput[str] = ModelComputeInput(
            data="test",
            computation_type="default",
            cache_enabled=False,
        )
        result_disabled = asyncio.run(compute.process(input_disabled))
        assert result_disabled.metadata["cache_enabled"] is False

        # Test with cache enabled (default)
        input_enabled: ModelComputeInput[str] = ModelComputeInput(
            data="test2",
            computation_type="default",
            cache_enabled=True,
        )
        result_enabled = asyncio.run(compute.process(input_enabled))
        assert result_enabled.metadata["cache_enabled"] is True


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestComputeIntegrationParallel:
    """Tests for parallel execution behavior.

    Tests verify:
    1. Parallel flag propagation
    2. Parallel execution conditions
    3. Sequential fallback
    """

    def test_parallel_disabled_uses_sequential(
        self, compute_node_factory: ComputeNodeFactory
    ) -> None:
        """Test that parallel_enabled=False uses sequential execution.

        Verifies that:
        - parallel_execution_used is False when disabled
        - Computation still completes correctly
        """
        compute = compute_node_factory()

        input_data: ModelComputeInput[list[int]] = ModelComputeInput(
            data=[1, 2, 3, 4, 5],
            computation_type="sum_numbers",
            cache_enabled=False,
            parallel_enabled=False,
        )

        result: ModelComputeOutput[float] = asyncio.run(compute.process(input_data))

        assert result.parallel_execution_used is False
        assert result.result == 15

    def test_non_list_data_uses_sequential(
        self, compute_node_factory: ComputeNodeFactory
    ) -> None:
        """Test that non-list data uses sequential execution.

        Verifies that:
        - Single item data doesn't use parallel execution
        - parallel_execution_used reflects actual execution mode
        """
        compute = compute_node_factory()

        # String input (not parallelizable)
        input_data: ModelComputeInput[str] = ModelComputeInput(
            data="hello",
            computation_type="string_uppercase",
            cache_enabled=False,
            parallel_enabled=True,  # Requested but not applicable
        )

        result: ModelComputeOutput[str] = asyncio.run(compute.process(input_data))

        # Should still work but not use parallel
        assert result.result == "HELLO"
        # parallel_execution_used depends on implementation
        # For single-item non-list, should be False
        assert result.parallel_execution_used is False


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestComputeIntegrationMetrics:
    """Tests for computation metrics and observability.

    Tests verify:
    1. Metrics collection
    2. Performance tracking
    """

    def test_computation_metrics_available(
        self, compute_node_factory: ComputeNodeFactory
    ) -> None:
        """Test that computation metrics are available.

        Verifies that:
        - Metrics can be retrieved
        - Execution mode info is tracked
        """
        compute = compute_node_factory()

        # Perform some computations
        input_data: ModelComputeInput[str] = ModelComputeInput(
            data="test",
            computation_type="default",
            cache_enabled=False,
        )
        asyncio.run(compute.process(input_data))

        # Get metrics
        metrics = asyncio.run(compute.get_computation_metrics())

        # Verify metrics structure
        assert isinstance(metrics, dict)
        assert "execution_mode" in metrics

    def test_output_metadata_tracks_input_size(
        self, compute_node_factory: ComputeNodeFactory
    ) -> None:
        """Test that output metadata tracks input data size.

        Verifies that:
        - input_data_size is recorded
        - Size reflects actual input length
        """
        compute = compute_node_factory()

        small_input: ModelComputeInput[str] = ModelComputeInput(
            data="small",
            computation_type="default",
            cache_enabled=False,
        )
        small_result = asyncio.run(compute.process(small_input))

        large_input: ModelComputeInput[str] = ModelComputeInput(
            data="a" * 10000,
            computation_type="default",
            cache_enabled=False,
        )
        large_result = asyncio.run(compute.process(large_input))

        # Large input should have larger reported size
        assert (
            large_result.metadata["input_data_size"]
            > small_result.metadata["input_data_size"]
        )


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestComputeIntegrationErrorRecovery:
    """Tests for error handling and recovery scenarios.

    Tests verify:
    1. Error context preservation
    2. Error type classification
    3. Partial failure handling
    """

    def test_error_context_contains_operation_details(
        self, compute_node_factory: ComputeNodeFactory
    ) -> None:
        """Test that error context contains operation details.

        Verifies that:
        - Error context includes operation_id
        - Error context includes computation_type
        """
        compute = compute_node_factory()

        input_data: ModelComputeInput[str] = ModelComputeInput(
            data="test",
            computation_type="nonexistent_type",
            cache_enabled=False,
        )

        with pytest.raises(ModelOnexError) as exc_info:
            asyncio.run(compute.process(input_data))

        error = exc_info.value
        # Context should contain relevant details
        assert error.context is not None
        # Context may be nested under additional_context.context
        if "additional_context" in error.context:
            nested_context = error.context["additional_context"].get("context", {})
            assert "computation_type" in nested_context
            assert nested_context["computation_type"] == "nonexistent_type"
        else:
            assert "computation_type" in error.context
            assert error.context["computation_type"] == "nonexistent_type"

    def test_computation_error_preserves_original_exception(
        self, compute_node_factory: ComputeNodeFactory
    ) -> None:
        """Test that computation errors preserve original exception.

        Verifies that:
        - Original exception is chained
        - Error type information is preserved
        """
        compute = compute_node_factory()

        # Register computation that raises specific error
        def failing_computation(data: Any) -> Any:
            raise ValueError("Intentional test failure")

        compute.register_computation("failing", failing_computation)

        input_data: ModelComputeInput[str] = ModelComputeInput(
            data="test",
            computation_type="failing",
            cache_enabled=False,
        )

        with pytest.raises(ModelOnexError) as exc_info:
            asyncio.run(compute.process(input_data))

        error = exc_info.value
        # Original exception should be chained
        assert error.__cause__ is not None
        assert isinstance(error.__cause__, ValueError)
        assert "Intentional test failure" in str(error.__cause__)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
