"""Comprehensive unit tests for NodeReducer."""

import uuid
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from omnibase_core.enums.enum_conflict_resolution import EnumConflictResolution
from omnibase_core.enums.enum_reduction_type import EnumReductionType
from omnibase_core.enums.enum_streaming_mode import EnumStreamingMode
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.infrastructure.node_reducer import NodeReducer
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.infrastructure.model_conflict_resolver import (
    ModelConflictResolver,
)
from omnibase_core.models.infrastructure.model_streaming_window import (
    ModelStreamingWindow,
)
from omnibase_core.models.operations.model_reducer_input import ModelReducerInput
from omnibase_core.models.operations.model_reducer_output import ModelReducerOutput


@pytest.fixture
def mock_container():
    """Create a mock ModelONEXContainer for testing."""
    container = MagicMock(spec=ModelONEXContainer)
    container.get_service = MagicMock(return_value=None)
    return container


@pytest.fixture
def mock_contract_model():
    """Create a mock contract model."""
    contract = MagicMock()
    contract.node_type = "reducer"
    contract.version = "1.0.0"
    contract.validate_node_specific_config = MagicMock(return_value=None)
    return contract


@pytest.fixture
def node_reducer(mock_container, mock_contract_model):
    """Create a NodeReducer instance for testing."""
    with patch.object(
        NodeReducer, "_load_contract_model", return_value=mock_contract_model
    ):
        reducer = NodeReducer(mock_container)
        # Initialize state for testing
        reducer.state = {"status": "ready"}
        reducer.created_at = datetime.now()
        reducer.node_id = str(uuid.uuid4())
        reducer.version = "1.0.0"
        return reducer


class TestNodeReducerInitialization:
    """Tests for NodeReducer initialization."""

    @pytest.mark.asyncio
    async def test_initialization_with_container(
        self, mock_container, mock_contract_model
    ):
        """Test NodeReducer initializes with valid container."""
        with patch.object(
            NodeReducer, "_load_contract_model", return_value=mock_contract_model
        ):
            reducer = NodeReducer(mock_container)

            assert reducer.default_batch_size == 1000
            assert reducer.max_memory_usage_mb == 512
            assert reducer.streaming_buffer_size == 10000
            assert isinstance(reducer.reduction_functions, dict)
            assert isinstance(reducer.reduction_metrics, dict)
            assert isinstance(reducer.active_windows, dict)

    @pytest.mark.asyncio
    async def test_builtin_reducers_registered(self, node_reducer):
        """Test that built-in reducers are automatically registered."""
        assert EnumReductionType.FOLD in node_reducer.reduction_functions
        assert EnumReductionType.AGGREGATE in node_reducer.reduction_functions
        assert EnumReductionType.NORMALIZE in node_reducer.reduction_functions
        assert EnumReductionType.MERGE in node_reducer.reduction_functions

    @pytest.mark.asyncio
    async def test_initial_state_empty(self, node_reducer):
        """Test that reducer starts with empty state."""
        assert len(node_reducer.active_windows) == 0
        assert len(node_reducer.reduction_metrics) == 0


class TestNodeReducerValidation:
    """Tests for NodeReducer input validation."""

    @pytest.mark.asyncio
    async def test_validate_valid_input(self, node_reducer):
        """Test validation passes for valid input."""
        input_data = ModelReducerInput(
            data=[1, 2, 3],
            reduction_type=EnumReductionType.FOLD,
            reducer_function="sum",
        )

        # Should not raise
        node_reducer._validate_reducer_input(input_data)

    @pytest.mark.asyncio
    async def test_validate_none_data_raises_error(self, node_reducer):
        """Test validation fails for None data."""
        # Pydantic validates data type before our code runs
        # So this will raise a Pydantic ValidationError, not ModelOnexError
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            input_data = ModelReducerInput(
                data=None,
                reduction_type=EnumReductionType.FOLD,
            )

    @pytest.mark.asyncio
    async def test_validate_invalid_reduction_type_raises_error(self, node_reducer):
        """Test validation fails for invalid reduction type."""
        input_data = ModelReducerInput(
            data=[1, 2, 3],
            reduction_type=EnumReductionType.FOLD,
        )

        # Mock the reduction type to be invalid
        input_data.reduction_type = "invalid"

        with pytest.raises(ModelOnexError) as exc_info:
            node_reducer._validate_reducer_input(input_data)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR


class TestNodeReducerFoldOperation:
    """Tests for FOLD reduction operation."""

    @pytest.mark.asyncio
    async def test_fold_sum_numeric_data(self, node_reducer):
        """Test FOLD with sum reducer on numeric data."""
        input_data = ModelReducerInput(
            data=[1, 2, 3, 4, 5],
            reduction_type=EnumReductionType.FOLD,
            reducer_function="sum",
            accumulator_init=0,
        )

        result = await node_reducer.process(input_data)

        assert isinstance(result, ModelReducerOutput)
        assert result.result == 15
        assert result.items_processed == 5
        assert result.reduction_type == EnumReductionType.FOLD

    @pytest.mark.asyncio
    async def test_fold_default_sum_without_reducer_function(self, node_reducer):
        """Test FOLD defaults to sum for numeric data."""
        input_data = ModelReducerInput(
            data=[10, 20, 30],
            reduction_type=EnumReductionType.FOLD,
            accumulator_init=0,
        )

        result = await node_reducer.process(input_data)

        assert result.result == 60
        assert result.items_processed == 3

    @pytest.mark.asyncio
    async def test_fold_max_reducer(self, node_reducer):
        """Test FOLD with max reducer."""
        input_data = ModelReducerInput(
            data=[5, 2, 9, 1, 7],
            reduction_type=EnumReductionType.FOLD,
            reducer_function="max",
            accumulator_init=0,
        )

        result = await node_reducer.process(input_data)

        assert result.result == 9

    @pytest.mark.asyncio
    async def test_fold_min_reducer(self, node_reducer):
        """Test FOLD with min reducer."""
        input_data = ModelReducerInput(
            data=[5, 2, 9, 1, 7],
            reduction_type=EnumReductionType.FOLD,
            reducer_function="min",
            accumulator_init=100,
        )

        result = await node_reducer.process(input_data)

        assert result.result == 1

    @pytest.mark.asyncio
    async def test_fold_concat_strings(self, node_reducer):
        """Test FOLD with string concatenation."""
        input_data = ModelReducerInput(
            data=["hello", " ", "world"],
            reduction_type=EnumReductionType.FOLD,
            reducer_function="concat",
            accumulator_init="",
        )

        result = await node_reducer.process(input_data)

        assert result.result == "hello world"

    @pytest.mark.asyncio
    async def test_fold_empty_data_returns_init(self, node_reducer):
        """Test FOLD with empty data returns accumulator_init."""
        input_data = ModelReducerInput(
            data=[],
            reduction_type=EnumReductionType.FOLD,
            reducer_function="sum",
            accumulator_init=42,
        )

        result = await node_reducer.process(input_data)

        assert result.result == 42
        assert result.items_processed == 0

    @pytest.mark.asyncio
    async def test_fold_unknown_reducer_raises_error(self, node_reducer):
        """Test FOLD with unknown reducer function raises error."""
        input_data = ModelReducerInput(
            data=[1, 2, 3],
            reduction_type=EnumReductionType.FOLD,
            reducer_function="unknown_function",
            accumulator_init=0,
        )

        with pytest.raises(ModelOnexError) as exc_info:
            await node_reducer.process(input_data)

        # The error is wrapped in OPERATION_FAILED
        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
        assert "unknown reducer function" in str(exc_info.value).lower()


class TestNodeReducerAggregateOperation:
    """Tests for AGGREGATE reduction operation."""

    @pytest.mark.asyncio
    async def test_aggregate_group_by_single_field(self, node_reducer):
        """Test AGGREGATE with grouping by single field."""
        input_data = ModelReducerInput(
            data=[
                {"status": "open", "priority": 1},
                {"status": "open", "priority": 2},
                {"status": "closed", "priority": 3},
            ],
            reduction_type=EnumReductionType.AGGREGATE,
            group_key="status",
        )

        result = await node_reducer.process(input_data)

        assert isinstance(result.result, dict)
        assert "open" in result.result
        assert "closed" in result.result
        assert result.result["open"]["count"] == 2
        assert result.result["closed"]["count"] == 1

    @pytest.mark.asyncio
    async def test_aggregate_numeric_statistics(self, node_reducer):
        """Test AGGREGATE computes numeric statistics."""
        input_data = ModelReducerInput(
            data=[
                {"category": "A", "value": 10},
                {"category": "A", "value": 20},
                {"category": "B", "value": 30},
            ],
            reduction_type=EnumReductionType.AGGREGATE,
            group_key="category",
        )

        result = await node_reducer.process(input_data)

        # Check category A statistics
        assert result.result["A"]["value_sum"] == 30
        assert result.result["A"]["value_avg"] == 15.0
        assert result.result["A"]["value_min"] == 10
        assert result.result["A"]["value_max"] == 20

    @pytest.mark.asyncio
    async def test_aggregate_empty_data_returns_empty_dict(self, node_reducer):
        """Test AGGREGATE with empty data returns empty dict."""
        input_data = ModelReducerInput(
            data=[],
            reduction_type=EnumReductionType.AGGREGATE,
            group_key="status",
        )

        result = await node_reducer.process(input_data)

        assert result.result == {}
        assert result.items_processed == 0


class TestNodeReducerNormalizeOperation:
    """Tests for NORMALIZE reduction operation."""

    @pytest.mark.asyncio
    async def test_normalize_min_max_scaling(self, node_reducer):
        """Test NORMALIZE with min-max scaling."""
        # Note: The normalize_reducer expects ModelSchemaValue objects in metadata
        # but has a bug where it uses them directly as dict keys without calling .to_value()
        input_data = ModelReducerInput(
            data=[
                {"id": 1, "score": 0},
                {"id": 2, "score": 50},
                {"id": 3, "score": 100},
            ],
            reduction_type=EnumReductionType.NORMALIZE,
            metadata={
                "score_field": ModelSchemaValue.from_value("score"),
                "normalization_method": ModelSchemaValue.from_value("min_max"),
            },
        )

        result = await node_reducer.process(input_data)

        # Verify normalized values
        assert result.result[0]["score_normalized"] == 0.0
        assert result.result[1]["score_normalized"] == 0.5
        assert result.result[2]["score_normalized"] == 1.0

    @pytest.mark.asyncio
    async def test_normalize_rank_method(self, node_reducer):
        """Test NORMALIZE with rank method."""
        input_data = ModelReducerInput(
            data=[
                {"id": 1, "score": 85},
                {"id": 2, "score": 95},
                {"id": 3, "score": 75},
            ],
            reduction_type=EnumReductionType.NORMALIZE,
            metadata={
                "score_field": ModelSchemaValue.from_value("score"),
                "normalization_method": ModelSchemaValue.from_value("rank"),
            },
        )

        result = await node_reducer.process(input_data)

        # Find items by score to check rank
        for item in result.result:
            if item["score"] == 95:
                assert item["score_rank"] == 1
            elif item["score"] == 85:
                assert item["score_rank"] == 2
            elif item["score"] == 75:
                assert item["score_rank"] == 3

    @pytest.mark.asyncio
    async def test_normalize_empty_data_returns_empty_list(self, node_reducer):
        """Test NORMALIZE with empty data returns empty list."""
        input_data = ModelReducerInput(
            data=[],
            reduction_type=EnumReductionType.NORMALIZE,
            metadata={
                "score_field": ModelSchemaValue.from_value("score"),
            },
        )

        result = await node_reducer.process(input_data)

        assert result.result == []

    @pytest.mark.asyncio
    async def test_normalize_constant_scores(self, node_reducer):
        """Test NORMALIZE handles constant scores correctly."""
        input_data = ModelReducerInput(
            data=[
                {"id": 1, "score": 50},
                {"id": 2, "score": 50},
                {"id": 3, "score": 50},
            ],
            reduction_type=EnumReductionType.NORMALIZE,
            metadata={
                "score_field": ModelSchemaValue.from_value("score"),
                "normalization_method": ModelSchemaValue.from_value("min_max"),
            },
        )

        result = await node_reducer.process(input_data)

        # When all scores are the same, normalized should be 0.5
        assert all(item["score_normalized"] == 0.5 for item in result.result)


class TestNodeReducerMergeOperation:
    """Tests for MERGE reduction operation."""

    @pytest.mark.asyncio
    async def test_merge_dictionaries(self, node_reducer):
        """Test MERGE combines dictionaries."""
        input_data = ModelReducerInput(
            data=[
                {"a": 1, "b": 2},
                {"c": 3, "d": 4},
            ],
            reduction_type=EnumReductionType.MERGE,
        )

        result = await node_reducer.process(input_data)

        assert result.result == {"a": 1, "b": 2, "c": 3, "d": 4}

    @pytest.mark.asyncio
    async def test_merge_lists(self, node_reducer):
        """Test MERGE combines lists."""
        input_data = ModelReducerInput(
            data=[
                [1, 2, 3],
                [4, 5, 6],
            ],
            reduction_type=EnumReductionType.MERGE,
        )

        result = await node_reducer.process(input_data)

        assert result.result == [1, 2, 3, 4, 5, 6]

    @pytest.mark.asyncio
    async def test_merge_with_conflict_resolution(self, node_reducer):
        """Test MERGE with conflict resolution strategy."""
        input_data = ModelReducerInput(
            data=[
                {"key": "first"},
                {"key": "second"},
            ],
            reduction_type=EnumReductionType.MERGE,
            conflict_resolution=EnumConflictResolution.LAST_WINS,
        )

        result = await node_reducer.process(input_data)

        assert result.result["key"] == "second"

    @pytest.mark.asyncio
    async def test_merge_empty_data_returns_empty_dict(self, node_reducer):
        """Test MERGE with empty data returns empty dict."""
        input_data = ModelReducerInput(
            data=[],
            reduction_type=EnumReductionType.MERGE,
        )

        result = await node_reducer.process(input_data)

        assert result.result == {}


class TestNodeReducerStreamingModes:
    """Tests for different streaming modes."""

    @pytest.mark.asyncio
    async def test_batch_mode_processes_all_at_once(self, node_reducer):
        """Test BATCH mode processes all data at once."""
        input_data = ModelReducerInput(
            data=[1, 2, 3, 4, 5],
            reduction_type=EnumReductionType.FOLD,
            reducer_function="sum",
            streaming_mode=EnumStreamingMode.BATCH,
            accumulator_init=0,
        )

        result = await node_reducer.process(input_data)

        assert result.result == 15
        assert result.batches_processed == 1
        assert result.streaming_mode == EnumStreamingMode.BATCH

    @pytest.mark.asyncio
    async def test_incremental_mode_processes_in_batches(self, node_reducer):
        """Test INCREMENTAL mode processes data in batches."""
        input_data = ModelReducerInput(
            data=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            reduction_type=EnumReductionType.FOLD,
            reducer_function="sum",
            streaming_mode=EnumStreamingMode.INCREMENTAL,
            batch_size=3,
            accumulator_init=0,
        )

        result = await node_reducer.process(input_data)

        assert result.result == 55
        assert result.batches_processed >= 1
        assert result.streaming_mode == EnumStreamingMode.INCREMENTAL

    @pytest.mark.asyncio
    async def test_windowed_mode_processes_by_window(self, node_reducer):
        """Test WINDOWED mode processes data in time windows."""
        input_data = ModelReducerInput(
            data=[1, 2, 3, 4, 5],
            reduction_type=EnumReductionType.FOLD,
            reducer_function="sum",
            streaming_mode=EnumStreamingMode.WINDOWED,
            window_size_ms=1000,
            accumulator_init=0,
        )

        result = await node_reducer.process(input_data)

        assert isinstance(result.result, (int, float))
        assert result.streaming_mode == EnumStreamingMode.WINDOWED


class TestNodeReducerRSDOperations:
    """Tests for RSD-specific operations."""

    @pytest.mark.asyncio
    async def test_aggregate_rsd_tickets(self, node_reducer):
        """Test aggregating RSD tickets."""
        tickets = [
            {"id": "T1", "status": "open", "priority": 1},
            {"id": "T2", "status": "open", "priority": 2},
            {"id": "T3", "status": "closed", "priority": 3},
        ]

        result = await node_reducer.aggregate_rsd_tickets(
            tickets=tickets,
            group_by="status",
        )

        assert "open" in result
        assert "closed" in result
        assert result["open"]["count"] == 2
        assert result["closed"]["count"] == 1

    @pytest.mark.asyncio
    async def test_normalize_priority_scores(self, node_reducer):
        """Test normalizing priority scores."""
        tickets = [
            {"id": "T1", "priority_score": 10},
            {"id": "T2", "priority_score": 50},
            {"id": "T3", "priority_score": 90},
        ]

        result = await node_reducer.normalize_priority_scores(
            tickets_with_scores=tickets,
            score_field="priority_score",
            normalization_method="min_max",
        )

        assert len(result) == 3
        assert result[0]["priority_score_normalized"] == 0.0
        assert result[1]["priority_score_normalized"] == 0.5
        assert result[2]["priority_score_normalized"] == 1.0

    @pytest.mark.asyncio
    async def test_resolve_dependency_cycles_no_cycles(self, node_reducer):
        """Test dependency cycle detection with no cycles."""
        graph = {
            "A": ["B"],
            "B": ["C"],
            "C": [],
        }

        result = await node_reducer.resolve_dependency_cycles(graph)

        assert result["has_cycles"] is False
        assert result["cycle_count"] == 0
        assert "total_nodes" in result

    @pytest.mark.asyncio
    async def test_resolve_dependency_cycles_with_cycle(self, node_reducer):
        """Test dependency cycle detection with cycles."""
        graph = {
            "A": ["B"],
            "B": ["C"],
            "C": ["A"],
        }

        result = await node_reducer.resolve_dependency_cycles(graph)

        assert result["has_cycles"] is True
        assert result["cycle_count"] > 0
        assert len(result["cycles"]) > 0


class TestNodeReducerCustomRegistration:
    """Tests for custom reducer function registration."""

    @pytest.mark.asyncio
    async def test_register_custom_reducer_success(self, node_reducer):
        """Test registering custom reducer function."""

        async def custom_reducer(data, input_data, conflict_resolver):
            return len(data)

        # Use a reduction type that's not already registered
        custom_type = EnumReductionType.DEDUPLICATE

        # Clear if already exists
        if custom_type in node_reducer.reduction_functions:
            del node_reducer.reduction_functions[custom_type]

        node_reducer.register_reduction_function(custom_type, custom_reducer)

        assert custom_type in node_reducer.reduction_functions
        assert node_reducer.reduction_functions[custom_type] == custom_reducer

    @pytest.mark.asyncio
    async def test_register_duplicate_reducer_raises_error(self, node_reducer):
        """Test registering duplicate reducer raises error."""

        async def custom_reducer(data, input_data, conflict_resolver):
            return data

        # Try to register over existing FOLD reducer
        with pytest.raises(ModelOnexError) as exc_info:
            node_reducer.register_reduction_function(
                EnumReductionType.FOLD, custom_reducer
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "already registered" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_register_non_callable_raises_error(self, node_reducer):
        """Test registering non-callable raises error."""
        # Use a reduction type that's not already registered
        custom_type = EnumReductionType.SORT

        # Clear if already exists
        if custom_type in node_reducer.reduction_functions:
            del node_reducer.reduction_functions[custom_type]

        with pytest.raises(ModelOnexError) as exc_info:
            node_reducer.register_reduction_function(custom_type, "not_a_function")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "must be callable" in exc_info.value.message.lower()


class TestNodeReducerMetrics:
    """Tests for reduction metrics tracking."""

    @pytest.mark.asyncio
    async def test_metrics_updated_after_processing(self, node_reducer):
        """Test metrics are updated after processing."""
        input_data = ModelReducerInput(
            data=[1, 2, 3],
            reduction_type=EnumReductionType.FOLD,
            reducer_function="sum",
            accumulator_init=0,
        )

        await node_reducer.process(input_data)

        metrics = await node_reducer.get_reduction_metrics()

        assert "fold" in metrics
        assert metrics["fold"]["total_operations"] >= 1
        assert metrics["fold"]["success_count"] >= 1

    @pytest.mark.asyncio
    async def test_metrics_track_processing_time(self, node_reducer):
        """Test metrics track processing time."""
        input_data = ModelReducerInput(
            data=[1, 2, 3],
            reduction_type=EnumReductionType.FOLD,
            reducer_function="sum",
            accumulator_init=0,
        )

        await node_reducer.process(input_data)

        metrics = await node_reducer.get_reduction_metrics()

        assert metrics["fold"]["avg_processing_time_ms"] >= 0
        assert metrics["fold"]["min_processing_time_ms"] >= 0
        assert metrics["fold"]["max_processing_time_ms"] >= 0

    @pytest.mark.asyncio
    async def test_metrics_include_memory_usage(self, node_reducer):
        """Test metrics include memory usage information."""
        metrics = await node_reducer.get_reduction_metrics()

        assert "memory_usage" in metrics
        assert "max_memory_mb" in metrics["memory_usage"]
        assert "streaming_buffer_size" in metrics["memory_usage"]


class TestNodeReducerErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_process_with_unknown_reduction_type_raises_error(self, node_reducer):
        """Test processing with unknown reduction type raises error."""
        # Remove FOLD from registered functions to simulate unknown type
        del node_reducer.reduction_functions[EnumReductionType.FOLD]

        input_data = ModelReducerInput(
            data=[1, 2, 3],
            reduction_type=EnumReductionType.FOLD,
        )

        with pytest.raises(ModelOnexError) as exc_info:
            await node_reducer.process(input_data)

        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
        assert "no reduction function" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_metrics_updated_on_error(self, node_reducer):
        """Test metrics are updated even on error."""
        # Remove FOLD to force an error
        del node_reducer.reduction_functions[EnumReductionType.FOLD]

        input_data = ModelReducerInput(
            data=[1, 2, 3],
            reduction_type=EnumReductionType.FOLD,
        )

        try:
            await node_reducer.process(input_data)
        except ModelOnexError:
            pass

        # Metrics should still be updated
        assert "fold" in node_reducer.reduction_metrics
        assert node_reducer.reduction_metrics["fold"]["error_count"] >= 1


class TestNodeReducerIntrospection:
    """Tests for introspection capabilities."""

    @pytest.mark.asyncio
    async def test_get_introspection_data_success(self, node_reducer):
        """Test getting introspection data."""
        data = await node_reducer.get_introspection_data()

        assert "node_capabilities" in data
        assert "runtime_information" in data
        assert "reduction_management_information" in data
        assert "rsd_specific_information" in data

    @pytest.mark.asyncio
    async def test_introspection_includes_reduction_types(self, node_reducer):
        """Test introspection includes reduction types."""
        data = await node_reducer.get_introspection_data()

        reduction_info = data["reduction_management_information"]
        assert "registered_reduction_functions" in reduction_info
        assert "reduction_function_count" in reduction_info

    @pytest.mark.asyncio
    async def test_introspection_includes_streaming_capabilities(self, node_reducer):
        """Test introspection includes streaming capabilities."""
        data = await node_reducer.get_introspection_data()

        capabilities = data["node_capabilities"]
        assert "streaming_capabilities" in capabilities


class TestNodeReducerEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_process_single_item(self, node_reducer):
        """Test processing single item."""
        input_data = ModelReducerInput(
            data=[42],
            reduction_type=EnumReductionType.FOLD,
            reducer_function="sum",
            accumulator_init=0,
        )

        result = await node_reducer.process(input_data)

        assert result.result == 42
        assert result.items_processed == 1

    @pytest.mark.asyncio
    async def test_process_large_dataset(self, node_reducer):
        """Test processing large dataset."""
        large_data = list(range(10000))

        input_data = ModelReducerInput(
            data=large_data,
            reduction_type=EnumReductionType.FOLD,
            reducer_function="sum",
            accumulator_init=0,
        )

        result = await node_reducer.process(input_data)

        assert result.result == sum(large_data)
        assert result.items_processed == 10000

    @pytest.mark.asyncio
    async def test_process_mixed_type_data(self, node_reducer):
        """Test processing mixed type data."""
        input_data = ModelReducerInput(
            data=[
                {"type": "A", "value": 1},
                {"type": "B", "value": 2},
                {"type": "A", "value": 3},
            ],
            reduction_type=EnumReductionType.AGGREGATE,
            group_key="type",
        )

        result = await node_reducer.process(input_data)

        assert "A" in result.result
        assert "B" in result.result
        assert result.result["A"]["count"] == 2
        assert result.result["B"]["count"] == 1

    @pytest.mark.asyncio
    async def test_process_with_none_accumulator_init(self, node_reducer):
        """Test processing with None accumulator_init."""
        input_data = ModelReducerInput(
            data=[1, 2, 3],
            reduction_type=EnumReductionType.FOLD,
            accumulator_init=None,
        )

        result = await node_reducer.process(input_data)

        # Should default to sum for numeric data
        assert result.result == 6

    @pytest.mark.asyncio
    async def test_normalize_with_missing_score_field(self, node_reducer):
        """Test NORMALIZE handles missing score field."""
        input_data = ModelReducerInput(
            data=[
                {"id": 1},  # Missing score field
                {"id": 2, "score": 50},
            ],
            reduction_type=EnumReductionType.NORMALIZE,
            metadata={
                "score_field": ModelSchemaValue.from_value("score"),
            },
        )

        result = await node_reducer.process(input_data)

        # Should process items with scores, ignore items without
        assert len(result.result) == 2

    @pytest.mark.asyncio
    async def test_aggregate_with_non_numeric_fields(self, node_reducer):
        """Test AGGREGATE skips non-numeric fields for statistics."""
        input_data = ModelReducerInput(
            data=[
                {"category": "A", "name": "first", "value": 10},
                {"category": "A", "name": "second", "value": 20},
            ],
            reduction_type=EnumReductionType.AGGREGATE,
            group_key="category",
        )

        result = await node_reducer.process(input_data)

        # Should compute statistics for numeric 'value' field only
        assert "value_sum" in result.result["A"]
        assert "name_sum" not in result.result["A"]

    @pytest.mark.asyncio
    async def test_dependency_cycle_self_reference(self, node_reducer):
        """Test dependency cycle detection with self-reference."""
        graph = {
            "A": ["A"],  # Self-reference
        }

        result = await node_reducer.resolve_dependency_cycles(graph)

        assert result["has_cycles"] is True

    @pytest.mark.asyncio
    async def test_get_reducer_function_builtin(self, node_reducer):
        """Test _get_reducer_function returns built-in functions."""
        sum_func = node_reducer._get_reducer_function("sum")
        assert sum_func is not None
        assert callable(sum_func)

        max_func = node_reducer._get_reducer_function("max")
        assert max_func is not None
        assert callable(max_func)

    @pytest.mark.asyncio
    async def test_get_reducer_function_unknown(self, node_reducer):
        """Test _get_reducer_function returns None for unknown function."""
        func = node_reducer._get_reducer_function("unknown_function_xyz")
        assert func is None


class TestNodeReducerLifecycle:
    """Tests for lifecycle management."""

    @pytest.mark.asyncio
    async def test_initialize_node_resources(self, node_reducer):
        """Test _initialize_node_resources."""
        # Should not raise
        await node_reducer._initialize_node_resources()

    @pytest.mark.asyncio
    async def test_cleanup_node_resources(self, node_reducer):
        """Test _cleanup_node_resources clears windows."""
        # Add a window
        node_reducer.active_windows["test"] = ModelStreamingWindow(1000)

        await node_reducer._cleanup_node_resources()

        assert len(node_reducer.active_windows) == 0
