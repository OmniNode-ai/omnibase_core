"""
Unit tests for NodeCompute.execute_compute() and _contract_to_input() methods.

Tests cover:
- Valid contract execution with process() delegation
- Invalid contract type handling with proper error codes
- Contract field extraction (input_state, legacy input_data)
- Computation type extraction from various sources
- Optional fields extraction (cache_enabled, parallel_enabled)

Author: ONEX Framework Team
Version: 1.0.0
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.compute.model_compute_input import ModelComputeInput
from omnibase_core.models.compute.model_compute_output import ModelComputeOutput
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.model_contract_compute import ModelContractCompute
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.nodes.node_compute import NodeCompute


def _get_context_value(error: ModelOnexError, key: str) -> Any:
    """
    Helper to extract context values from ModelOnexError.

    The error context structure is:
    - Standard keys (file_path, line_number, etc.) are at top level
    - Custom context keys are nested under 'additional_context' -> 'context'

    Args:
        error: The ModelOnexError instance
        key: The key to look for in context

    Returns:
        The value if found, None otherwise
    """
    context = error.context
    # Check top level first
    if key in context:
        return context[key]
    # Check in additional_context -> context
    additional = context.get("additional_context", {})
    if isinstance(additional, dict):
        inner_context = additional.get("context", {})
        if isinstance(inner_context, dict) and key in inner_context:
            return inner_context[key]
    return None


def _create_mock_contract(
    input_state: Any = None,
    input_data: Any = None,
    metadata: dict[str, Any] | None = None,
    algorithm: Any = None,
    computation_type: str | None = None,
) -> MagicMock:
    """
    Create a mock contract object that simulates ModelContractCompute.

    This is used to test _contract_to_input without needing the full
    ModelContractCompute validation overhead.

    Args:
        input_state: Value for input_state attribute
        input_data: Value for input_data attribute (legacy)
        metadata: Value for metadata attribute
        algorithm: Mock algorithm config
        computation_type: Optional computation_type attribute

    Returns:
        MagicMock with appropriate attributes set
    """
    mock = MagicMock(spec=ModelContractCompute)
    mock.input_state = input_state
    mock.input_data = input_data
    mock.metadata = metadata or {}
    mock.algorithm = algorithm
    mock.computation_type = computation_type
    return mock


@pytest.fixture
def test_container() -> ModelONEXContainer:
    """Create a test container for NodeCompute initialization."""
    return ModelONEXContainer()


@pytest.fixture
def node(test_container: ModelONEXContainer) -> NodeCompute[Any, Any]:
    """Create a NodeCompute instance for testing."""
    return NodeCompute(test_container)


@pytest.fixture
def mock_contract_factory() -> Callable[..., MagicMock]:
    """
    Factory fixture for creating mock contracts with consistent defaults.

    This fixture provides a callable that wraps _create_mock_contract(),
    allowing tests to create mock contracts with a consistent interface.

    Returns:
        A callable that creates MagicMock contracts with the specified attributes.

    Example:
        def test_example(mock_contract_factory):
            contract = mock_contract_factory(
                input_state={"data": "value"},
                metadata={"key": "value"},
            )
            assert contract.input_state == {"data": "value"}
    """

    def _factory(
        input_state: Any = None,
        input_data: Any = None,
        metadata: dict[str, Any] | None = None,
        algorithm: Any = None,
        computation_type: str | None = None,
    ) -> MagicMock:
        return _create_mock_contract(
            input_state=input_state,
            input_data=input_data,
            metadata=metadata,
            algorithm=algorithm,
            computation_type=computation_type,
        )

    return _factory


@pytest.mark.unit
class TestNodeComputeExecuteCompute:
    """Tests for NodeCompute.execute_compute() method."""

    @pytest.mark.asyncio
    async def test_execute_compute_valid_contract_calls_process(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test that execute_compute with valid contract calls process()."""
        # Create a real ModelContractCompute instance using MagicMock with spec
        mock_contract = MagicMock(spec=ModelContractCompute)
        mock_contract.input_state = {"text": "hello world"}
        mock_contract.metadata = {}
        mock_contract.algorithm = MagicMock()
        mock_contract.algorithm.algorithm_type = "string_uppercase"

        # Create mock output
        mock_output = ModelComputeOutput(
            result="HELLO WORLD",
            operation_id=uuid4(),
            computation_type="string_uppercase",
            processing_time_ms=1.5,
            cache_hit=False,
            parallel_execution_used=False,
        )

        # Mock the process method
        with patch.object(
            node, "process", new_callable=AsyncMock, return_value=mock_output
        ) as mock_process:
            result = await node.execute_compute(mock_contract)

            # Verify process was called with ModelComputeInput
            mock_process.assert_called_once()
            call_args = mock_process.call_args[0][0]
            assert isinstance(call_args, ModelComputeInput)

            # Verify the result is returned correctly
            assert result == mock_output
            assert result.result == "HELLO WORLD"
            assert result.computation_type == "string_uppercase"

    @pytest.mark.asyncio
    async def test_execute_compute_valid_contract_returns_output(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test that execute_compute returns correct ModelComputeOutput."""
        # Create mock contract with default computation type
        mock_contract = MagicMock(spec=ModelContractCompute)
        mock_contract.input_state = {"data": "test"}
        mock_contract.metadata = {}
        mock_contract.algorithm = MagicMock()
        mock_contract.algorithm.algorithm_type = "default"

        result = await node.execute_compute(mock_contract)

        # Verify output structure
        assert isinstance(result, ModelComputeOutput)
        assert result.computation_type == "default"
        assert result.processing_time_ms >= 0
        assert isinstance(result.cache_hit, bool)
        assert isinstance(result.parallel_execution_used, bool)
        # Default computation returns input unchanged
        assert result.result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_execute_compute_invalid_contract_type_dict(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test that passing a dict raises ModelOnexError with VALIDATION_ERROR."""
        invalid_contract = {"name": "test", "input_state": {"data": "value"}}

        with pytest.raises(ModelOnexError) as exc_info:
            await node.execute_compute(invalid_contract)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Invalid contract type" in str(error.message)
        assert error.context is not None
        assert _get_context_value(error, "node_id") is not None
        assert _get_context_value(error, "provided_type") == "dict"
        assert _get_context_value(error, "expected_type") == "ModelContractCompute"

    @pytest.mark.asyncio
    async def test_execute_compute_invalid_contract_type_string(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test that passing a string raises ModelOnexError with VALIDATION_ERROR."""
        invalid_contract = "not a contract"

        with pytest.raises(ModelOnexError) as exc_info:
            await node.execute_compute(invalid_contract)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Invalid contract type" in str(error.message)
        assert error.context is not None
        assert _get_context_value(error, "provided_type") == "str"
        assert _get_context_value(error, "expected_type") == "ModelContractCompute"

    @pytest.mark.asyncio
    async def test_execute_compute_invalid_contract_type_none(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test that passing None raises ModelOnexError with VALIDATION_ERROR."""
        with pytest.raises(ModelOnexError) as exc_info:
            await node.execute_compute(None)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Invalid contract type" in str(error.message)
        assert error.context is not None
        assert _get_context_value(error, "provided_type") == "NoneType"

    @pytest.mark.asyncio
    async def test_execute_compute_invalid_contract_type_wrong_model(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test that passing wrong Pydantic model raises ModelOnexError."""
        # Use ModelComputeInput as a wrong model type
        wrong_model = ModelComputeInput(
            data={"test": "data"},
            computation_type="default",
        )

        with pytest.raises(ModelOnexError) as exc_info:
            await node.execute_compute(wrong_model)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Invalid contract type" in str(error.message)
        assert error.context is not None
        assert "ModelComputeInput" in _get_context_value(error, "provided_type")

    @pytest.mark.asyncio
    async def test_execute_compute_contract_with_input_state(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test that contract with input_state field uses it correctly."""
        input_state_data = {"values": [1, 2, 3], "operation": "sum"}
        mock_contract = MagicMock(spec=ModelContractCompute)
        mock_contract.input_state = input_state_data
        mock_contract.metadata = {}
        mock_contract.algorithm = MagicMock()
        mock_contract.algorithm.algorithm_type = "default"

        with patch.object(node, "process", new_callable=AsyncMock) as mock_process:
            mock_process.return_value = ModelComputeOutput(
                result=input_state_data,
                operation_id=uuid4(),
                computation_type="default",
                processing_time_ms=1.0,
            )

            await node.execute_compute(mock_contract)

            # Verify input_state was passed to process
            call_args = mock_process.call_args[0][0]
            assert isinstance(call_args, ModelComputeInput)
            assert call_args.data == input_state_data

    @pytest.mark.asyncio
    async def test_execute_compute_error_context_contains_node_id(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test that error context contains node_id for debugging."""
        invalid_contract = 12345  # Integer is invalid

        with pytest.raises(ModelOnexError) as exc_info:
            await node.execute_compute(invalid_contract)

        error = exc_info.value
        assert error.context is not None
        node_id_from_context = _get_context_value(error, "node_id")
        assert node_id_from_context is not None
        assert str(node.node_id) == node_id_from_context


@pytest.mark.unit
class TestNodeComputeContractToInput:
    """Tests for NodeCompute._contract_to_input() method."""

    def test_contract_to_input_with_input_state(
        self,
        node: NodeCompute[Any, Any],
        mock_contract_factory: Callable[..., MagicMock],
    ) -> None:
        """Test _contract_to_input extracts input_state correctly."""
        mock_contract = mock_contract_factory(
            input_state={"text": "hello world"},
            algorithm=MagicMock(algorithm_type="default"),
        )

        result = node._contract_to_input(mock_contract)

        assert isinstance(result, ModelComputeInput)
        assert result.data == {"text": "hello world"}

    def test_contract_to_input_extracts_metadata(
        self,
        node: NodeCompute[Any, Any],
        mock_contract_factory: Callable[..., MagicMock],
    ) -> None:
        """Test _contract_to_input extracts metadata correctly."""
        metadata = {"custom_key": "custom_value", "priority": "high"}
        mock_contract = mock_contract_factory(
            input_state={"data": "value"},
            metadata=metadata,
            algorithm=MagicMock(algorithm_type="default"),
        )

        result = node._contract_to_input(mock_contract)

        assert result.metadata == metadata

    def test_contract_to_input_with_legacy_input_data(
        self,
        node: NodeCompute[Any, Any],
        mock_contract_factory: Callable[..., MagicMock],
    ) -> None:
        """Test _contract_to_input falls back to input_data when input_state is None."""
        mock_contract = mock_contract_factory(
            input_state=None,
            input_data={"legacy": "data"},
        )

        with patch("omnibase_core.nodes.node_compute.emit_log_event") as mock_log:
            result = node._contract_to_input(mock_contract)

            # Verify fallback to input_data
            assert result.data == {"legacy": "data"}

            # Verify warning was logged
            mock_log.assert_called()
            call_args = mock_log.call_args
            # First positional arg is log level (WARNING)
            assert "WARNING" in str(call_args[0][0])
            # Second positional arg is message
            assert "legacy" in call_args[0][1].lower()

    def test_contract_to_input_missing_both_fields_raises_error(
        self,
        node: NodeCompute[Any, Any],
        mock_contract_factory: Callable[..., MagicMock],
    ) -> None:
        """Test _contract_to_input raises error when both input_state and input_data are None."""
        mock_contract = mock_contract_factory(
            input_state=None,
            input_data=None,
        )

        with pytest.raises(ModelOnexError) as exc_info:
            node._contract_to_input(mock_contract)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "input_state" in str(error.message)
        assert "input_data" in str(error.message)
        assert error.context is not None
        assert _get_context_value(error, "node_id") is not None
        assert _get_context_value(error, "hint") is not None
        # Verify enhanced error context for debugging
        assert _get_context_value(error, "checked_attributes") == [
            "input_state",
            "input_data",
        ]
        assert _get_context_value(error, "input_state_value") == "None"
        assert _get_context_value(error, "input_data_value") == "None"

    def test_contract_to_input_computation_type_from_algorithm(
        self,
        node: NodeCompute[Any, Any],
        mock_contract_factory: Callable[..., MagicMock],
    ) -> None:
        """Test computation_type is extracted from algorithm.algorithm_type."""
        mock_algorithm = MagicMock()
        mock_algorithm.algorithm_type = "string_uppercase"

        mock_contract = mock_contract_factory(
            input_state={"data": "value"},
            algorithm=mock_algorithm,
        )

        result = node._contract_to_input(mock_contract)

        assert result.computation_type == "string_uppercase"

    def test_contract_to_input_computation_type_from_metadata(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test computation_type is extracted from metadata when algorithm is None."""
        mock_contract = _create_mock_contract(
            input_state={"data": "value"},
            metadata={"computation_type": "custom_computation"},
            algorithm=None,
        )

        result = node._contract_to_input(mock_contract)

        assert result.computation_type == "custom_computation"

    def test_contract_to_input_computation_type_from_contract_attribute(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test computation_type is extracted from contract.computation_type attribute."""
        mock_contract = _create_mock_contract(
            input_state={"data": "value"},
            computation_type="attribute_computation",
        )

        result = node._contract_to_input(mock_contract)

        assert result.computation_type == "attribute_computation"

    def test_contract_to_input_computation_type_default(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test computation_type defaults to 'default' when not specified."""
        mock_contract = _create_mock_contract(
            input_state={"data": "value"},
        )

        result = node._contract_to_input(mock_contract)

        assert result.computation_type == "default"

    def test_contract_to_input_cache_enabled_from_metadata(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test cache_enabled is extracted from metadata."""
        mock_contract = _create_mock_contract(
            input_state={"data": "value"},
            metadata={"cache_enabled": False},
        )

        result = node._contract_to_input(mock_contract)

        assert result.cache_enabled is False

    def test_contract_to_input_cache_enabled_default_true(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test cache_enabled defaults to True when not specified."""
        mock_contract = _create_mock_contract(
            input_state={"data": "value"},
        )

        result = node._contract_to_input(mock_contract)

        assert result.cache_enabled is True

    def test_contract_to_input_parallel_enabled_from_metadata(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test parallel_enabled is extracted from metadata."""
        mock_contract = _create_mock_contract(
            input_state={"data": "value"},
            metadata={"parallel_enabled": True},
        )

        result = node._contract_to_input(mock_contract)

        assert result.parallel_enabled is True

    def test_contract_to_input_parallel_enabled_default_false(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test parallel_enabled defaults to False when not specified."""
        mock_contract = _create_mock_contract(
            input_state={"data": "value"},
        )

        result = node._contract_to_input(mock_contract)

        assert result.parallel_enabled is False

    def test_contract_to_input_computation_type_priority(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test computation_type priority: algorithm > metadata > contract attribute."""
        # Create mock with all three sources
        mock_algorithm = MagicMock()
        mock_algorithm.algorithm_type = "algorithm_source"

        mock_contract = _create_mock_contract(
            input_state={"data": "value"},
            metadata={"computation_type": "metadata_source"},
            algorithm=mock_algorithm,
            computation_type="attribute_source",
        )

        result = node._contract_to_input(mock_contract)

        # Algorithm should take priority
        assert result.computation_type == "algorithm_source"

    def test_contract_to_input_metadata_priority_over_attribute(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test metadata computation_type takes priority over contract attribute."""
        mock_contract = _create_mock_contract(
            input_state={"data": "value"},
            metadata={"computation_type": "metadata_source"},
            computation_type="attribute_source",
        )

        result = node._contract_to_input(mock_contract)

        # Metadata should take priority over attribute
        assert result.computation_type == "metadata_source"

    def test_contract_to_input_handles_empty_metadata(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test _contract_to_input handles None metadata gracefully."""
        # Create mock with None metadata (not empty dict)
        mock_contract = MagicMock(spec=ModelContractCompute)
        mock_contract.input_state = {"data": "value"}
        mock_contract.metadata = None
        mock_contract.algorithm = None
        mock_contract.computation_type = None

        result = node._contract_to_input(mock_contract)

        # Should not raise, metadata should be empty dict
        assert result.metadata == {}

    def test_contract_to_input_preserves_complex_input_state(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test _contract_to_input preserves complex nested input_state."""
        complex_input = {
            "nested": {
                "level1": {
                    "level2": [1, 2, 3],
                },
            },
            "array": [{"a": 1}, {"b": 2}],
            "mixed": {"num": 42, "str": "test", "bool": True},
        }

        mock_contract = _create_mock_contract(
            input_state=complex_input,
            algorithm=MagicMock(algorithm_type="default"),
        )

        result = node._contract_to_input(mock_contract)

        assert result.data == complex_input


@pytest.mark.unit
class TestNodeComputeExecuteComputeIntegration:
    """Integration tests for execute_compute with real process() execution."""

    @pytest.mark.asyncio
    async def test_execute_compute_full_pipeline_default(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test full execute_compute pipeline with default computation."""
        mock_contract = MagicMock(spec=ModelContractCompute)
        mock_contract.input_state = {"test": "data"}
        mock_contract.metadata = {}
        mock_contract.algorithm = MagicMock()
        mock_contract.algorithm.algorithm_type = "default"

        result = await node.execute_compute(mock_contract)

        assert isinstance(result, ModelComputeOutput)
        assert result.computation_type == "default"
        # Default computation returns input unchanged
        assert result.result == {"test": "data"}

    @pytest.mark.asyncio
    async def test_execute_compute_full_pipeline_string_uppercase(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test full execute_compute pipeline with string_uppercase computation."""
        mock_contract = MagicMock(spec=ModelContractCompute)
        mock_contract.input_state = "hello world"
        mock_contract.metadata = {}
        mock_contract.algorithm = MagicMock()
        mock_contract.algorithm.algorithm_type = "string_uppercase"

        result = await node.execute_compute(mock_contract)

        assert isinstance(result, ModelComputeOutput)
        assert result.computation_type == "string_uppercase"
        assert result.result == "HELLO WORLD"

    @pytest.mark.asyncio
    async def test_execute_compute_full_pipeline_sum_numbers(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test full execute_compute pipeline with sum_numbers computation."""
        mock_contract = MagicMock(spec=ModelContractCompute)
        mock_contract.input_state = [1.0, 2.0, 3.0, 4.0, 5.0]
        mock_contract.metadata = {}
        mock_contract.algorithm = MagicMock()
        mock_contract.algorithm.algorithm_type = "sum_numbers"

        result = await node.execute_compute(mock_contract)

        assert isinstance(result, ModelComputeOutput)
        assert result.computation_type == "sum_numbers"
        assert result.result == 15.0

    @pytest.mark.asyncio
    async def test_execute_compute_with_caching(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test execute_compute uses caching when enabled."""
        mock_contract = MagicMock(spec=ModelContractCompute)
        mock_contract.input_state = {"test": "cache_data"}
        mock_contract.metadata = {"cache_enabled": True}
        mock_contract.algorithm = MagicMock()
        mock_contract.algorithm.algorithm_type = "default"

        # First call should compute
        result1 = await node.execute_compute(mock_contract)
        assert result1.cache_hit is False

        # Second call with same contract should hit cache
        result2 = await node.execute_compute(mock_contract)
        assert result2.cache_hit is True
        assert result2.result == result1.result

    @pytest.mark.asyncio
    async def test_execute_compute_without_caching(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test execute_compute does not cache when disabled."""
        mock_contract = MagicMock(spec=ModelContractCompute)
        mock_contract.input_state = {"test": "no_cache_data"}
        mock_contract.metadata = {"cache_enabled": False}
        mock_contract.algorithm = MagicMock()
        mock_contract.algorithm.algorithm_type = "default"

        # First call
        result1 = await node.execute_compute(mock_contract)
        assert result1.cache_hit is False

        # Second call should also compute (no caching)
        result2 = await node.execute_compute(mock_contract)
        assert result2.cache_hit is False

    @pytest.mark.asyncio
    async def test_execute_compute_unknown_computation_type(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test execute_compute raises error for unknown computation type."""
        mock_contract = MagicMock(spec=ModelContractCompute)
        mock_contract.input_state = {"data": "value"}
        mock_contract.metadata = {}
        mock_contract.algorithm = MagicMock()
        mock_contract.algorithm.algorithm_type = "nonexistent_computation"

        with pytest.raises(ModelOnexError) as exc_info:
            await node.execute_compute(mock_contract)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.OPERATION_FAILED
        assert "Unknown computation type" in str(error.message)
        # Verify enhanced error context includes error_type for debugging
        assert _get_context_value(error, "error_type") == "ModelOnexError"
        assert (
            _get_context_value(error, "computation_type") == "nonexistent_computation"
        )
        # Verify processing_time_ms is captured
        assert _get_context_value(error, "processing_time_ms") is not None

    @pytest.mark.asyncio
    async def test_execute_compute_error_context_includes_cache_and_parallel_status(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test error context includes cache_enabled and parallel_enabled for debugging."""
        mock_contract = MagicMock(spec=ModelContractCompute)
        mock_contract.input_state = {"data": "value"}
        mock_contract.metadata = {"cache_enabled": False, "parallel_enabled": True}
        mock_contract.algorithm = MagicMock()
        mock_contract.algorithm.algorithm_type = "nonexistent_computation"

        with pytest.raises(ModelOnexError) as exc_info:
            await node.execute_compute(mock_contract)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.OPERATION_FAILED
        # Verify cache_enabled and parallel_enabled are in error context
        assert _get_context_value(error, "cache_enabled") is False
        assert _get_context_value(error, "parallel_enabled") is True

    @pytest.mark.asyncio
    async def test_execute_compute_error_context_default_cache_and_parallel_values(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test error context includes default values for cache_enabled and parallel_enabled."""
        mock_contract = MagicMock(spec=ModelContractCompute)
        mock_contract.input_state = {"data": "value"}
        mock_contract.metadata = {}  # No explicit settings - use defaults
        mock_contract.algorithm = MagicMock()
        mock_contract.algorithm.algorithm_type = "nonexistent_computation"

        with pytest.raises(ModelOnexError) as exc_info:
            await node.execute_compute(mock_contract)

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.OPERATION_FAILED
        # Verify default values: cache_enabled=True, parallel_enabled=False
        assert _get_context_value(error, "cache_enabled") is True
        assert _get_context_value(error, "parallel_enabled") is False

    @pytest.mark.asyncio
    async def test_execute_compute_with_custom_registered_computation(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test execute_compute with a custom registered computation."""
        # Register custom computation
        node.register_computation("double_values", lambda data: [x * 2 for x in data])

        mock_contract = MagicMock(spec=ModelContractCompute)
        mock_contract.input_state = [1, 2, 3]
        mock_contract.metadata = {}
        mock_contract.algorithm = MagicMock()
        mock_contract.algorithm.algorithm_type = "double_values"

        result = await node.execute_compute(mock_contract)

        assert result.computation_type == "double_values"
        assert result.result == [2, 4, 6]


@pytest.mark.unit
class TestNodeComputeEdgeCases:
    """Edge case tests for NodeCompute execution scenarios."""

    @pytest.mark.asyncio
    async def test_execute_compute_with_empty_list_input_state(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test execute_compute handles empty list input_state correctly.

        Verifies that an empty list is a valid input_state value and
        passes through to the computation without raising validation errors.
        The default computation should return the empty list unchanged.
        """
        mock_contract = MagicMock(spec=ModelContractCompute)
        mock_contract.input_state = []
        mock_contract.metadata = {}
        mock_contract.algorithm = MagicMock()
        mock_contract.algorithm.algorithm_type = "default"

        result = await node.execute_compute(mock_contract)

        assert isinstance(result, ModelComputeOutput)
        assert result.computation_type == "default"
        assert result.result == []
        assert result.cache_hit is False

    @pytest.mark.asyncio
    async def test_execute_compute_with_empty_dict_input_state(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test execute_compute handles empty dict input_state correctly.

        Verifies that an empty dict is a valid input_state value and
        passes through to the computation without raising validation errors.
        The default computation should return the empty dict unchanged.
        """
        mock_contract = MagicMock(spec=ModelContractCompute)
        mock_contract.input_state = {}
        mock_contract.metadata = {}
        mock_contract.algorithm = MagicMock()
        mock_contract.algorithm.algorithm_type = "default"

        result = await node.execute_compute(mock_contract)

        assert isinstance(result, ModelComputeOutput)
        assert result.computation_type == "default"
        assert result.result == {}
        assert result.cache_hit is False

    @pytest.mark.asyncio
    async def test_execute_compute_parallel_warning_single_value(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test that parallel execution with non-parallelizable data triggers warning.

        When parallel_enabled=True but data is a single string (not list/tuple
        with >1 element), a WARNING should be logged indicating that parallel
        execution was requested but data is not parallelizable, and sequential
        execution is used instead.
        """
        mock_contract = MagicMock(spec=ModelContractCompute)
        mock_contract.input_state = "single string value"
        mock_contract.metadata = {"parallel_enabled": True}
        mock_contract.algorithm = MagicMock()
        mock_contract.algorithm.algorithm_type = "default"

        with patch("omnibase_core.nodes.node_compute.emit_log_event") as mock_log:
            result = await node.execute_compute(mock_contract)

            # Verify result is correct (computation still works)
            assert isinstance(result, ModelComputeOutput)
            assert result.result == "single string value"
            assert result.parallel_execution_used is False

            # Find the WARNING call about parallel execution
            warning_calls = [
                call
                for call in mock_log.call_args_list
                if "WARNING" in str(call[0][0]) and "parallel" in call[0][1].lower()
            ]
            assert len(warning_calls) >= 1, (
                "Expected WARNING log about parallel execution not being supported"
            )

            # Verify warning message content
            warning_call = warning_calls[0]
            warning_message = warning_call[0][1]
            assert "not parallelizable" in warning_message.lower()
            assert "sequential" in warning_message.lower()

    @pytest.mark.asyncio
    async def test_execute_compute_parallel_warning_single_element_list(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test parallel warning when list has only 1 element.

        When parallel_enabled=True but data is a list with only 1 element,
        a WARNING should be logged since parallel execution requires >1 element
        to distribute work across threads.
        """
        mock_contract = MagicMock(spec=ModelContractCompute)
        mock_contract.input_state = ["single_element"]
        mock_contract.metadata = {"parallel_enabled": True}
        mock_contract.algorithm = MagicMock()
        mock_contract.algorithm.algorithm_type = "default"

        with patch("omnibase_core.nodes.node_compute.emit_log_event") as mock_log:
            result = await node.execute_compute(mock_contract)

            # Verify result is correct
            assert isinstance(result, ModelComputeOutput)
            assert result.result == ["single_element"]
            assert result.parallel_execution_used is False

            # Find the WARNING call about parallel execution
            warning_calls = [
                call
                for call in mock_log.call_args_list
                if "WARNING" in str(call[0][0]) and "parallel" in call[0][1].lower()
            ]
            assert len(warning_calls) >= 1, (
                "Expected WARNING log when parallel requested with single-element list"
            )

    @pytest.mark.asyncio
    async def test_execute_compute_with_none_algorithm_type(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test fallback when algorithm exists but algorithm_type is None.

        When contract has an algorithm object but algorithm.algorithm_type is None,
        the computation_type should fall back to metadata['computation_type'],
        then to contract.computation_type, then to 'default'.

        This test verifies the fallback chain works correctly when the primary
        source (algorithm.algorithm_type) is explicitly None.
        """
        # Case 1: Falls back to metadata
        mock_contract = MagicMock(spec=ModelContractCompute)
        mock_contract.input_state = {"test": "data"}
        mock_contract.metadata = {"computation_type": "metadata_fallback"}
        mock_contract.algorithm = MagicMock()
        mock_contract.algorithm.algorithm_type = None  # Explicitly None
        mock_contract.computation_type = "attribute_fallback"

        # Register the custom computation type
        node.register_computation("metadata_fallback", lambda data: data)

        result = await node.execute_compute(mock_contract)

        assert isinstance(result, ModelComputeOutput)
        # Should use metadata computation_type since algorithm_type is None
        assert result.computation_type == "metadata_fallback"
        assert result.result == {"test": "data"}

    @pytest.mark.asyncio
    async def test_execute_compute_with_none_algorithm_type_uses_contract_attribute(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test fallback to contract.computation_type when algorithm_type is None.

        When both algorithm.algorithm_type and metadata['computation_type'] are
        unavailable, should fall back to contract.computation_type attribute.
        """
        mock_contract = MagicMock(spec=ModelContractCompute)
        mock_contract.input_state = {"test": "data"}
        mock_contract.metadata = {}  # No computation_type in metadata
        mock_contract.algorithm = MagicMock()
        mock_contract.algorithm.algorithm_type = None  # Explicitly None
        mock_contract.computation_type = "attribute_computation"

        # Register the custom computation type
        node.register_computation("attribute_computation", lambda data: data)

        result = await node.execute_compute(mock_contract)

        assert isinstance(result, ModelComputeOutput)
        assert result.computation_type == "attribute_computation"

    @pytest.mark.asyncio
    async def test_execute_compute_with_none_algorithm_type_defaults(
        self,
        node: NodeCompute[Any, Any],
    ) -> None:
        """Test defaults to 'default' when all computation_type sources are None.

        When algorithm.algorithm_type is None, metadata has no computation_type,
        and contract.computation_type is None, should default to 'default'.
        """
        mock_contract = MagicMock(spec=ModelContractCompute)
        mock_contract.input_state = {"test": "data"}
        mock_contract.metadata = {}  # No computation_type
        mock_contract.algorithm = MagicMock()
        mock_contract.algorithm.algorithm_type = None
        mock_contract.computation_type = None

        result = await node.execute_compute(mock_contract)

        assert isinstance(result, ModelComputeOutput)
        assert result.computation_type == "default"
        # Default computation returns input unchanged
        assert result.result == {"test": "data"}
