"""Unit tests for ModelReducerInput[T].

This module provides comprehensive tests for the generic ModelReducerInput model,
which defines the input contract for REDUCER nodes in the ONEX architecture.

Test Coverage:
    - Model instantiation with minimal and full fields
    - Generic type parameter validation (int, str, dict, list, custom Pydantic models)
    - Field validation (required/optional fields, numeric ranges, enum constraints)
    - Serialization/deserialization (dict and JSON roundtrips)
    - Frozen behavior (immutability guarantees)
    - Edge cases (empty data, large datasets, nested types, unicode, special chars)
    - Thread safety via immutability (safe for parallel test execution)

Architecture Context:
    ModelReducerInput[T] is the input model for REDUCER nodes, which perform
    FSM-driven state management and data aggregation. The generic type parameter T
    represents the element type in the data list being reduced.

Test Pattern References:
    - tests/unit/models/test_model_intent.py (625 lines) - Intent pattern tests
    - tests/unit/models/fsm/test_model_fsm_state_snapshot.py (572 lines) - FSM tests
    - tests/unit/models/fsm/test_model_fsm_transition_result.py (717 lines) - Result tests

Related Models:
    - ModelReducerOutput[T] - Output contract for REDUCER nodes
    - ModelReducerMetadata - Metadata container for reducer operations
    - EnumReductionType - Reduction operation types (FOLD, ACCUMULATE, MERGE, etc.)
    - EnumConflictResolution - Conflict resolution strategies
    - EnumStreamingMode - Streaming processing modes (BATCH, WINDOWED, REAL_TIME)

Notes:
    - All tests use pytest markers (@pytest.mark.unit)
    - Generic type parameters are tested with multiple types
    - Immutability is enforced via frozen=True in model_config
    - Thread-safe for pytest-xdist parallel execution
    - Parametrized tests reduce duplication while maintaining coverage
"""

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_reducer_types import (
    EnumConflictResolution,
    EnumReductionType,
    EnumStreamingMode,
)
from omnibase_core.models.common.model_reducer_metadata import ModelReducerMetadata
from omnibase_core.models.reducer.model_reducer_input import ModelReducerInput

pytestmark = pytest.mark.unit


# Custom model for testing generic type parameters
class SampleModel(BaseModel):
    """Sample model for testing ModelReducerInput with custom Pydantic models."""

    name: str
    value: int


class TestModelReducerInputInstantiation:
    """Test ModelReducerInput instantiation with various configurations."""

    def test_create_with_minimal_fields(self):
        """Test creating ModelReducerInput with only required fields.

        Validates that the model can be instantiated with just data and reduction_type,
        and all optional fields receive their default values correctly."""
        reducer_input = ModelReducerInput[int](
            data=[1, 2, 3],
            reduction_type=EnumReductionType.FOLD,
        )

        assert reducer_input is not None
        assert isinstance(reducer_input, ModelReducerInput)
        assert reducer_input.data == [1, 2, 3]
        assert reducer_input.reduction_type == EnumReductionType.FOLD
        # Check defaults
        assert isinstance(reducer_input.operation_id, UUID)
        assert reducer_input.conflict_resolution == EnumConflictResolution.LAST_WINS
        assert reducer_input.streaming_mode == EnumStreamingMode.BATCH
        assert reducer_input.batch_size == 1000
        assert reducer_input.window_size_ms == 5000
        assert isinstance(reducer_input.metadata, ModelReducerMetadata)
        assert isinstance(reducer_input.timestamp, datetime)

    def test_create_with_all_fields(self):
        """Test creating ModelReducerInput with all fields populated.

        Validates that all fields (required and optional) can be explicitly set
        and are correctly stored without defaults overriding provided values."""
        test_operation_id = uuid4()
        test_metadata = ModelReducerMetadata(
            source="test_source",
            correlation_id="test-correlation-123",
            group_key="test_group",
        )
        test_timestamp = datetime(2025, 12, 16, 10, 30, 0)

        reducer_input = ModelReducerInput[str](
            data=["a", "b", "c"],
            reduction_type=EnumReductionType.GROUP,
            operation_id=test_operation_id,
            conflict_resolution=EnumConflictResolution.MERGE,
            streaming_mode=EnumStreamingMode.WINDOWED,
            batch_size=500,
            window_size_ms=10000,
            metadata=test_metadata,
            timestamp=test_timestamp,
        )

        assert reducer_input.data == ["a", "b", "c"]
        assert reducer_input.reduction_type == EnumReductionType.GROUP
        assert reducer_input.operation_id == test_operation_id
        assert reducer_input.conflict_resolution == EnumConflictResolution.MERGE
        assert reducer_input.streaming_mode == EnumStreamingMode.WINDOWED
        assert reducer_input.batch_size == 500
        assert reducer_input.window_size_ms == 10000
        assert reducer_input.metadata == test_metadata
        assert reducer_input.timestamp == test_timestamp

    @pytest.mark.parametrize(
        ("type_param", "data", "reduction_type", "expected_type"),
        [
            pytest.param(
                int, [10, 20, 30, 40], EnumReductionType.ACCUMULATE, int, id="int"
            ),
            pytest.param(
                str,
                ["apple", "banana", "cherry"],
                EnumReductionType.DEDUPLICATE,
                str,
                id="str",
            ),
            pytest.param(
                dict,
                [{"key": "a", "value": 1}, {"key": "b", "value": 2}],
                EnumReductionType.MERGE,
                dict,
                id="dict",
            ),
            pytest.param(
                list,
                [[1, 2], [3, 4], [5, 6]],
                EnumReductionType.AGGREGATE,
                list,
                id="list",
            ),
        ],
    )
    def test_generic_type_parameter(
        self, type_param, data, reduction_type, expected_type
    ):
        """Test ModelReducerInput with various generic type parameters.

        Validates that the generic type parameter system correctly handles int, str,
        dict, and list types, maintaining type integrity throughout instantiation."""
        reducer_input = ModelReducerInput[type_param](  # type: ignore[valid-type]  # Runtime type parameter for testing
            data=data,
            reduction_type=reduction_type,
        )

        assert isinstance(reducer_input, ModelReducerInput)
        assert all(isinstance(x, expected_type) for x in reducer_input.data)
        assert reducer_input.data == data

    def test_generic_type_parameter_custom_model(self):
        """Test ModelReducerInput with custom Pydantic model type parameter.

        Validates that the generic type parameter supports custom Pydantic models,
        enabling strongly-typed domain objects within reducer inputs."""
        test_models = [
            SampleModel(name="model1", value=100),
            SampleModel(name="model2", value=200),
            SampleModel(name="model3", value=300),
        ]

        reducer_input = ModelReducerInput[SampleModel](
            data=test_models,
            reduction_type=EnumReductionType.NORMALIZE,
        )

        assert isinstance(reducer_input, ModelReducerInput)
        assert all(isinstance(x, SampleModel) for x in reducer_input.data)
        assert len(reducer_input.data) == 3
        assert reducer_input.data[0].name == "model1"
        assert reducer_input.data[1].value == 200

    def test_operation_id_auto_generation(self):
        """Test that operation_id is auto-generated when not provided.

        Validates that each instance receives a unique UUID4 when operation_id is
        not explicitly set, ensuring operation traceability and correlation."""
        input1 = ModelReducerInput[int](data=[1], reduction_type=EnumReductionType.FOLD)
        input2 = ModelReducerInput[int](data=[2], reduction_type=EnumReductionType.FOLD)

        assert isinstance(input1.operation_id, UUID)
        assert isinstance(input2.operation_id, UUID)
        assert input1.operation_id != input2.operation_id

    def test_timestamp_auto_generation(self):
        """Test that timestamp is auto-generated when not provided.

        Validates that the model automatically captures creation time when timestamp
        is not explicitly provided, falling within expected time boundaries."""
        before = datetime.now()
        reducer_input = ModelReducerInput[int](
            data=[1, 2, 3],
            reduction_type=EnumReductionType.FOLD,
        )
        after = datetime.now()

        assert isinstance(reducer_input.timestamp, datetime)
        assert before <= reducer_input.timestamp <= after


class TestModelReducerInputValidation:
    """Test ModelReducerInput field validation and constraints."""

    @pytest.mark.parametrize(
        ("missing_field", "field_name"),
        [
            pytest.param({"reduction_type": EnumReductionType.FOLD}, "data", id="data"),
            pytest.param({"data": [1, 2, 3]}, "reduction_type", id="reduction_type"),
        ],
    )
    def test_required_fields_missing(self, missing_field, field_name):
        """Test that missing required fields raise ValidationError.

        Validates that both data and reduction_type are required fields and cannot
        be omitted during model instantiation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerInput[int](**missing_field)

        assert field_name in str(exc_info.value)

    def test_data_type_validation_must_be_list(self):
        """Test that data must be a list.

        Validates that the data field enforces list type and rejects non-list values,
        ensuring consistent collection handling across all reducer operations."""
        # Valid list
        reducer_input = ModelReducerInput[int](
            data=[1, 2, 3],
            reduction_type=EnumReductionType.FOLD,
        )
        assert isinstance(reducer_input.data, list)

        # Invalid types should fail
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerInput[int](
                data="not a list",  # type: ignore[arg-type]  # Intentionally invalid for testing
                reduction_type=EnumReductionType.FOLD,
            )
        assert "data" in str(exc_info.value).lower()

    def test_reduction_type_validation(self):
        """Test that reduction_type must be valid EnumReductionType.

        Validates that all enum values are accepted and invalid strings are rejected,
        ensuring type safety for reduction operations and preventing typos."""
        # Valid enum values
        for reduction_type in EnumReductionType:
            reducer_input = ModelReducerInput[int](
                data=[1, 2],
                reduction_type=reduction_type,
            )
            assert reducer_input.reduction_type == reduction_type

        # Invalid string should fail
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerInput[int](
                data=[1, 2],
                reduction_type="invalid_reduction_type",  # type: ignore[arg-type]  # Intentionally invalid for testing
            )
        assert "reduction_type" in str(exc_info.value).lower()

    @pytest.mark.parametrize(
        ("batch_size", "should_pass", "error_msg"),
        [
            pytest.param(-1, False, "greater than 0", id="negative"),
            pytest.param(0, False, "greater than 0", id="zero"),
            pytest.param(1, True, None, id="min_valid"),
            pytest.param(1000, True, None, id="default"),
            pytest.param(10000, True, None, id="max_valid"),
            pytest.param(10001, False, "less than or equal to 10000", id="exceeds_max"),
        ],
    )
    def test_batch_size_validation(self, batch_size, should_pass, error_msg):
        """Test batch_size validation with various values.

        Validates that batch_size must be positive (1-10000) and rejects invalid
        values with appropriate error messages."""
        if should_pass:
            reducer_input = ModelReducerInput[int](
                data=[1, 2],
                reduction_type=EnumReductionType.FOLD,
                batch_size=batch_size,
            )
            assert reducer_input.batch_size == batch_size
        else:
            with pytest.raises(ValidationError) as exc_info:
                ModelReducerInput[int](
                    data=[1, 2],
                    reduction_type=EnumReductionType.FOLD,
                    batch_size=batch_size,
                )
            assert error_msg in str(exc_info.value)

    @pytest.mark.parametrize(
        ("window_size_ms", "should_pass", "error_msg"),
        [
            pytest.param(999, False, "greater than or equal to 1000", id="below_min"),
            pytest.param(1000, True, None, id="min_valid"),
            pytest.param(5000, True, None, id="default"),
            pytest.param(60000, True, None, id="max_valid"),
            pytest.param(60001, False, "less than or equal to 60000", id="exceeds_max"),
        ],
    )
    def test_window_size_ms_validation(self, window_size_ms, should_pass, error_msg):
        """Test window_size_ms validation with various values.

        Validates that window_size_ms must be between 1000-60000ms and rejects
        invalid values with appropriate error messages."""
        if should_pass:
            reducer_input = ModelReducerInput[int](
                data=[1, 2],
                reduction_type=EnumReductionType.FOLD,
                window_size_ms=window_size_ms,
            )
            assert reducer_input.window_size_ms == window_size_ms
        else:
            with pytest.raises(ValidationError) as exc_info:
                ModelReducerInput[int](
                    data=[1, 2],
                    reduction_type=EnumReductionType.FOLD,
                    window_size_ms=window_size_ms,
                )
            assert error_msg in str(exc_info.value)

    def test_invalid_field_types(self):
        """Test that invalid field types raise ValidationError.

        Validates comprehensive type checking across all fields, ensuring that
        incorrect types (wrong enums, invalid UUIDs, etc) are rejected."""
        # Invalid data type (not a list)
        with pytest.raises(ValidationError):
            ModelReducerInput[int](
                data=123,  # type: ignore[arg-type]  # Intentionally invalid for testing
                reduction_type=EnumReductionType.FOLD,
            )

        # Invalid reduction_type
        with pytest.raises(ValidationError):
            ModelReducerInput[int](
                data=[1, 2],
                reduction_type="not_an_enum",  # type: ignore[arg-type]  # Intentionally invalid for testing
            )

        # Invalid conflict_resolution
        with pytest.raises(ValidationError):
            ModelReducerInput[int](
                data=[1, 2],
                reduction_type=EnumReductionType.FOLD,
                conflict_resolution="invalid",  # type: ignore[arg-type]  # Intentionally invalid for testing
            )

        # Invalid streaming_mode
        with pytest.raises(ValidationError):
            ModelReducerInput[int](
                data=[1, 2],
                reduction_type=EnumReductionType.FOLD,
                streaming_mode="invalid",  # type: ignore[arg-type]  # Intentionally invalid for testing
            )

    def test_extra_fields_rejected(self):
        """Test that extra fields are rejected (model_config extra='forbid').

        Validates that the model enforces strict field validation, rejecting any
        fields not defined in the schema to prevent typos and data corruption."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerInput[int](
                data=[1, 2],
                reduction_type=EnumReductionType.FOLD,
                extra_field="should_fail",  # type: ignore[call-arg]  # Intentionally invalid for testing
            )
        assert "extra_field" in str(exc_info.value).lower()

    def test_conflict_resolution_validation(self):
        """Test that all EnumConflictResolution values are accepted.

        Validates that every conflict resolution strategy (LAST_WINS, FIRST_WINS,
        MERGE) can be successfully applied to reducer input configurations."""
        for resolution in EnumConflictResolution:
            reducer_input = ModelReducerInput[int](
                data=[1, 2],
                reduction_type=EnumReductionType.FOLD,
                conflict_resolution=resolution,
            )
            assert reducer_input.conflict_resolution == resolution

    def test_streaming_mode_validation(self):
        """Test that all EnumStreamingMode values are accepted.

        Validates that every streaming mode (BATCH, WINDOWED, REAL_TIME) is supported
        and can be configured without errors for different processing patterns."""
        for mode in EnumStreamingMode:
            reducer_input = ModelReducerInput[int](
                data=[1, 2],
                reduction_type=EnumReductionType.FOLD,
                streaming_mode=mode,
            )
            assert reducer_input.streaming_mode == mode


class TestModelReducerInputSerialization:
    """Test ModelReducerInput serialization to dict and JSON."""

    def test_model_dump(self):
        """Test serializing to dictionary.

        Validates that the model can be converted to a dictionary representation
        with all fields (data, metadata, timestamps) preserved correctly."""
        test_operation_id = uuid4()
        test_metadata = ModelReducerMetadata(
            source="test_source",
            correlation_id="test-123",
        )
        test_timestamp = datetime(2025, 12, 16, 12, 0, 0)

        reducer_input = ModelReducerInput[int](
            data=[1, 2, 3],
            reduction_type=EnumReductionType.FOLD,
            operation_id=test_operation_id,
            conflict_resolution=EnumConflictResolution.MERGE,
            streaming_mode=EnumStreamingMode.WINDOWED,
            batch_size=500,
            window_size_ms=10000,
            metadata=test_metadata,
            timestamp=test_timestamp,
        )

        data = reducer_input.model_dump()

        assert isinstance(data, dict)
        assert data["data"] == [1, 2, 3]
        assert data["reduction_type"] == EnumReductionType.FOLD
        assert data["operation_id"] == test_operation_id
        assert data["conflict_resolution"] == EnumConflictResolution.MERGE
        assert data["streaming_mode"] == EnumStreamingMode.WINDOWED
        assert data["batch_size"] == 500
        assert data["window_size_ms"] == 10000
        assert data["timestamp"] == test_timestamp

    def test_model_dump_json(self):
        """Test serializing to JSON string.

        Validates that the model can be serialized to JSON format for network
        transmission, storage, and cross-service communication."""
        reducer_input = ModelReducerInput[str](
            data=["a", "b", "c"],
            reduction_type=EnumReductionType.GROUP,
        )

        json_str = reducer_input.model_dump_json()

        assert isinstance(json_str, str)
        assert '"data"' in json_str
        assert '"reduction_type"' in json_str
        assert '"operation_id"' in json_str
        assert "group" in json_str.lower()

    def test_model_validate(self):
        """Test deserializing from dictionary.

        Validates that a dictionary can be converted back to a ModelReducerInput
        instance with all fields correctly reconstructed and types preserved."""
        test_operation_id = uuid4()
        test_timestamp = datetime(2025, 12, 16, 12, 0, 0)

        data = {
            "data": [10, 20, 30],
            "reduction_type": "fold",
            "operation_id": str(test_operation_id),
            "conflict_resolution": "merge",
            "streaming_mode": "batch",
            "batch_size": 2000,
            "window_size_ms": 15000,
            "metadata": {"source": "test"},
            "timestamp": test_timestamp.isoformat(),
        }

        reducer_input = ModelReducerInput[int].model_validate(data)

        assert isinstance(reducer_input, ModelReducerInput)
        assert reducer_input.data == [10, 20, 30]
        assert reducer_input.reduction_type == EnumReductionType.FOLD
        assert reducer_input.operation_id == test_operation_id
        assert reducer_input.conflict_resolution == EnumConflictResolution.MERGE
        assert reducer_input.streaming_mode == EnumStreamingMode.BATCH
        assert reducer_input.batch_size == 2000
        assert reducer_input.window_size_ms == 15000

    def test_model_validate_json(self):
        """Test deserializing from JSON string.

        Validates that a JSON string can be deserialized back to a ModelReducerInput
        instance with proper type conversions (strings→UUIDs, enums, etc)."""
        test_operation_id = uuid4()

        json_str = f"""{{
            "data": ["x", "y", "z"],
            "reduction_type": "group",
            "operation_id": "{test_operation_id}",
            "conflict_resolution": "last_wins",
            "streaming_mode": "windowed",
            "batch_size": 1500,
            "window_size_ms": 20000,
            "metadata": {{}},
            "timestamp": "2025-12-16T12:00:00"
        }}"""

        reducer_input = ModelReducerInput[str].model_validate_json(json_str)

        assert isinstance(reducer_input, ModelReducerInput)
        assert reducer_input.data == ["x", "y", "z"]
        assert reducer_input.reduction_type == EnumReductionType.GROUP
        assert reducer_input.operation_id == test_operation_id
        assert reducer_input.streaming_mode == EnumStreamingMode.WINDOWED

    @pytest.mark.parametrize(
        ("type_param", "data", "reduction_type"),
        [
            pytest.param(int, [100, 200, 300], EnumReductionType.ACCUMULATE, id="int"),
            pytest.param(
                str, ["alpha", "beta", "gamma"], EnumReductionType.DEDUPLICATE, id="str"
            ),
            pytest.param(
                dict, [{"key": "a"}, {"key": "b"}], EnumReductionType.MERGE, id="dict"
            ),
            pytest.param(
                list, [[1, 2], [3, 4]], EnumReductionType.AGGREGATE, id="list"
            ),
        ],
    )
    def test_roundtrip_serialization(self, type_param, data, reduction_type):
        """Test roundtrip serialization for various data types.

        Validates that data can be serialized to dict/JSON and back without loss
        of data or type information across int, str, dict, and list types."""
        original = ModelReducerInput[type_param](  # type: ignore[valid-type]  # Runtime type parameter for testing
            data=data,
            reduction_type=reduction_type,
        )

        # Serialize and deserialize
        serialized = original.model_dump()
        restored = ModelReducerInput[type_param].model_validate(serialized)  # type: ignore[valid-type]  # Runtime type parameter for testing

        assert restored.data == original.data
        assert restored.reduction_type == original.reduction_type
        assert restored.operation_id == original.operation_id

    def test_roundtrip_preserves_all_fields(self):
        """Test that roundtrip serialization preserves all fields.

        Validates comprehensive field preservation including complex nested metadata
        through complete serialization-deserialization cycles."""
        test_metadata = ModelReducerMetadata(
            source="origin",
            correlation_id="corr-123",
            group_key="group-a",
        )

        original = ModelReducerInput[int](
            data=[1, 2, 3, 4, 5],
            reduction_type=EnumReductionType.NORMALIZE,
            conflict_resolution=EnumConflictResolution.FIRST_WINS,
            streaming_mode=EnumStreamingMode.REAL_TIME,
            batch_size=100,
            window_size_ms=30000,
            metadata=test_metadata,
        )

        data = original.model_dump()
        restored = ModelReducerInput[int].model_validate(data)

        assert restored.data == original.data
        assert restored.reduction_type == original.reduction_type
        assert restored.operation_id == original.operation_id
        assert restored.conflict_resolution == original.conflict_resolution
        assert restored.streaming_mode == original.streaming_mode
        assert restored.batch_size == original.batch_size
        assert restored.window_size_ms == original.window_size_ms

    def test_serialization_handles_optional_fields(self):
        """Test that serialization handles optional fields correctly.

        Validates that models created with minimal fields serialize correctly with
        default values properly applied during deserialization."""
        # Create with minimal fields
        minimal = ModelReducerInput[int](
            data=[1, 2],
            reduction_type=EnumReductionType.FOLD,
        )

        data = minimal.model_dump()
        restored = ModelReducerInput[int].model_validate(data)

        # Defaults should be preserved
        assert restored.conflict_resolution == EnumConflictResolution.LAST_WINS
        assert restored.streaming_mode == EnumStreamingMode.BATCH
        assert restored.batch_size == 1000
        assert restored.window_size_ms == 5000


class TestModelReducerInputGenericTyping:
    """Test generic type parameter behavior and preservation."""

    @pytest.mark.parametrize(
        ("type_param", "data", "expected_type"),
        [
            pytest.param(int, [1, 2, 3, 4, 5], int, id="int"),
            pytest.param(str, ["one", "two", "three"], str, id="str"),
            pytest.param(dict, [{"a": 1}, {"b": 2}, {"c": 3}], dict, id="dict"),
        ],
    )
    def test_type_parameter_preserves_type(self, type_param, data, expected_type):
        """Test that type parameter is preserved for various types.

        Validates that int, str, and dict type parameters maintain their types
        throughout the model lifecycle without coercion or corruption."""
        reducer_input = ModelReducerInput[type_param](  # type: ignore[valid-type]  # Runtime type parameter for testing
            data=data,
            reduction_type=EnumReductionType.FOLD,
        )

        assert all(isinstance(x, expected_type) for x in reducer_input.data)

    def test_type_parameter_preserves_custom_model_type(self):
        """Test that custom Pydantic model type parameter is preserved.

        Validates that custom Pydantic model types are maintained with full access
        to their fields, methods, and validation logic."""
        models = [
            SampleModel(name="test1", value=10),
            SampleModel(name="test2", value=20),
        ]

        reducer_input = ModelReducerInput[SampleModel](
            data=models,
            reduction_type=EnumReductionType.NORMALIZE,
        )

        assert all(isinstance(x, SampleModel) for x in reducer_input.data)
        assert reducer_input.data[0].name == "test1"
        assert reducer_input.data[1].value == 20

    def test_multiple_instances_different_types_independent(self):
        """Test that multiple instances with different types are independent.

        Validates that multiple ModelReducerInput instances with different generic
        types can coexist without interference, type pollution, or state leakage."""
        int_input = ModelReducerInput[int](
            data=[1, 2, 3],
            reduction_type=EnumReductionType.FOLD,
        )

        str_input = ModelReducerInput[str](
            data=["a", "b", "c"],
            reduction_type=EnumReductionType.GROUP,
        )

        dict_input = ModelReducerInput[dict](
            data=[{"x": 1}, {"y": 2}],
            reduction_type=EnumReductionType.MERGE,
        )

        # Each instance should maintain its type
        assert all(isinstance(x, int) for x in int_input.data)
        assert all(isinstance(x, str) for x in str_input.data)
        assert all(isinstance(x, dict) for x in dict_input.data)

    def test_generic_type_in_nested_structures(self):
        """Test generic types in nested structures.

        Validates that deeply nested data structures (dicts containing lists/dicts)
        maintain their integrity and accessibility through the generic type system."""
        # List of dicts with nested structures
        nested_data = [
            {"items": [1, 2, 3], "meta": {"count": 3}},
            {"items": [4, 5], "meta": {"count": 2}},
        ]

        reducer_input = ModelReducerInput[dict](
            data=nested_data,
            reduction_type=EnumReductionType.AGGREGATE,
        )

        assert reducer_input.data == nested_data
        assert reducer_input.data[0]["items"] == [1, 2, 3]
        assert reducer_input.data[1]["meta"]["count"] == 2


class TestModelReducerInputFrozenBehavior:
    """Test frozen behavior (immutability) of ModelReducerInput."""

    @pytest.mark.parametrize(
        ("field_name", "new_value"),
        [
            pytest.param("data", [4, 5, 6], id="data"),
            pytest.param(
                "reduction_type", EnumReductionType.AGGREGATE, id="reduction_type"
            ),
            pytest.param("batch_size", 1000, id="batch_size"),
            pytest.param("window_size_ms", 20000, id="window_size_ms"),
            pytest.param("operation_id", uuid4(), id="operation_id"),
        ],
    )
    def test_field_immutable(self, field_name, new_value):
        """Test that fields cannot be modified after creation.

        Validates that all fields (data, reduction_type, batch_size, window_size_ms,
        operation_id) are frozen and raise ValidationError on modification attempts."""
        reducer_input = ModelReducerInput[int](
            data=[1, 2, 3],
            reduction_type=EnumReductionType.FOLD,
        )

        with pytest.raises(ValidationError) as exc_info:
            setattr(reducer_input, field_name, new_value)  # type: ignore[misc]

        assert "frozen" in str(exc_info.value).lower()

    def test_cannot_add_new_fields_after_creation(self):
        """Test that new fields cannot be added after creation.

        Validates that the frozen model prevents dynamic field addition, maintaining
        strict schema compliance and preventing accidental data corruption."""
        reducer_input = ModelReducerInput[int](
            data=[1, 2, 3],
            reduction_type=EnumReductionType.FOLD,
        )

        with pytest.raises(ValidationError) as exc_info:
            reducer_input.new_field = "value"  # type: ignore[attr-defined]  # Intentionally accessing non-existent field

        assert "frozen" in str(exc_info.value).lower()


class TestModelReducerInputEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_data_list(self):
        """Test that empty data list is valid.

        Validates that reducer inputs can be created with empty data lists, which
        may represent initial states, filtered results, or no-op operations."""
        reducer_input = ModelReducerInput[int](
            data=[],
            reduction_type=EnumReductionType.FOLD,
        )

        assert reducer_input.data == []
        assert isinstance(reducer_input.data, list)

    def test_single_item_data_list(self):
        """Test data list with single item.

        Validates boundary case of single-element data lists, which are valid and
        may represent atomic operations or minimal batch sizes."""
        reducer_input = ModelReducerInput[int](
            data=[42],
            reduction_type=EnumReductionType.FOLD,
        )

        assert reducer_input.data == [42]
        assert len(reducer_input.data) == 1

    def test_large_data_list(self):
        """Test data list with many items (1000+).

        Validates that the model handles large data collections efficiently without
        performance degradation, memory issues, or serialization problems."""
        large_data = list(range(1000))

        reducer_input = ModelReducerInput[int](
            data=large_data,
            reduction_type=EnumReductionType.AGGREGATE,
        )

        assert len(reducer_input.data) == 1000
        assert reducer_input.data == large_data

    def test_nested_generic_types(self):
        """Test nested generic types (list of dicts).

        Validates that complex nested structures (dictionaries containing lists and
        other dictionaries) are correctly preserved without corruption."""
        nested_data = [
            {"users": ["alice", "bob"], "count": 2},
            {"users": ["charlie"], "count": 1},
        ]

        reducer_input = ModelReducerInput[dict](
            data=nested_data,
            reduction_type=EnumReductionType.GROUP,
        )

        assert reducer_input.data == nested_data
        assert reducer_input.data[0]["users"] == ["alice", "bob"]

    def test_none_values_in_optional_metadata_fields(self):
        """Test None values for optional metadata fields.

        Validates that optional metadata fields (source, correlation_id, group_key)
        can be explicitly set to None without causing validation errors."""
        metadata = ModelReducerMetadata(
            source=None,
            correlation_id=None,
            group_key=None,
        )

        reducer_input = ModelReducerInput[int](
            data=[1, 2, 3],
            reduction_type=EnumReductionType.FOLD,
            metadata=metadata,
        )

        assert reducer_input.metadata.source is None
        assert reducer_input.metadata.correlation_id is None
        assert reducer_input.metadata.group_key is None

    def test_default_values_for_optional_fields(self):
        """Test that default values are applied correctly.

        Validates that all optional fields receive appropriate default values when
        not explicitly provided during instantiation (conflict_resolution, etc)."""
        reducer_input = ModelReducerInput[int](
            data=[1, 2],
            reduction_type=EnumReductionType.FOLD,
        )

        # Check all defaults
        assert reducer_input.conflict_resolution == EnumConflictResolution.LAST_WINS
        assert reducer_input.streaming_mode == EnumStreamingMode.BATCH
        assert reducer_input.batch_size == 1000
        assert reducer_input.window_size_ms == 5000
        assert isinstance(reducer_input.metadata, ModelReducerMetadata)
        assert isinstance(reducer_input.operation_id, UUID)
        assert isinstance(reducer_input.timestamp, datetime)

    def test_unicode_in_string_data(self):
        """Test unicode characters in string data.

        Validates that the model correctly handles international characters, emoji,
        and various writing systems (Arabic, Cyrillic, Chinese, etc)."""
        unicode_data = ["hello", "世界", "مرحبا", "🌍", "Привет"]

        reducer_input = ModelReducerInput[str](
            data=unicode_data,
            reduction_type=EnumReductionType.DEDUPLICATE,
        )

        assert reducer_input.data == unicode_data
        assert "世界" in reducer_input.data
        assert "🌍" in reducer_input.data

    def test_special_characters_in_data(self):
        """Test special characters in data.

        Validates that whitespace, newlines, tabs, and quotes are correctly preserved
        in data values without corruption or escaping issues."""
        special_data = [
            {"key": "value with spaces"},
            {"key": "value\twith\ttabs"},
            {"key": "value\nwith\nnewlines"},
            {"key": 'value"with"quotes'},
        ]

        reducer_input = ModelReducerInput[dict](
            data=special_data,
            reduction_type=EnumReductionType.MERGE,
        )

        assert reducer_input.data == special_data
        assert reducer_input.data[0]["key"] == "value with spaces"

    def test_metadata_with_all_fields_populated(self):
        """Test metadata with all fields populated.

        Validates that complex metadata with all optional fields set (trace IDs,
        partition IDs, window IDs, tags) is correctly stored and accessible."""
        test_partition_id = uuid4()
        test_window_id = uuid4()

        metadata = ModelReducerMetadata(
            source="event_stream",
            trace_id="trace-123",
            span_id="span-456",
            correlation_id="corr-789",
            group_key="group-a",
            partition_id=test_partition_id,
            window_id=test_window_id,
            tags=["tag1", "tag2", "tag3"],
        )

        reducer_input = ModelReducerInput[int](
            data=[1, 2, 3],
            reduction_type=EnumReductionType.GROUP,
            metadata=metadata,
        )

        assert reducer_input.metadata.source == "event_stream"
        assert reducer_input.metadata.trace_id == "trace-123"
        assert reducer_input.metadata.correlation_id == "corr-789"
        assert reducer_input.metadata.partition_id == test_partition_id
        assert reducer_input.metadata.tags == ["tag1", "tag2", "tag3"]

    def test_all_reduction_types(self):
        """Test that all reduction types are supported.

        Validates comprehensive support for every reduction operation type defined
        in the EnumReductionType enumeration (FOLD, ACCUMULATE, MERGE, etc)."""
        for reduction_type in EnumReductionType:
            reducer_input = ModelReducerInput[int](
                data=[1, 2, 3],
                reduction_type=reduction_type,
            )
            assert reducer_input.reduction_type == reduction_type

    def test_all_conflict_resolution_strategies(self):
        """Test that all conflict resolution strategies are supported.

        Validates that every conflict resolution strategy (LAST_WINS, FIRST_WINS,
        MERGE) can be configured without errors."""
        for resolution in EnumConflictResolution:
            reducer_input = ModelReducerInput[int](
                data=[1, 2, 3],
                reduction_type=EnumReductionType.FOLD,
                conflict_resolution=resolution,
            )
            assert reducer_input.conflict_resolution == resolution

    def test_all_streaming_modes(self):
        """Test that all streaming modes are supported.

        Validates that every streaming mode (BATCH, WINDOWED, REAL_TIME) can be
        configured for different processing patterns."""
        for mode in EnumStreamingMode:
            reducer_input = ModelReducerInput[int](
                data=[1, 2, 3],
                reduction_type=EnumReductionType.FOLD,
                streaming_mode=mode,
            )
            assert reducer_input.streaming_mode == mode


class TestModelReducerInputThreadSafety:
    """Test thread safety of ModelReducerInput via immutability.

    Validates that ModelReducerInput instances are safe to access concurrently
    from multiple threads, as required by pytest-xdist parallel execution and
    concurrent processing scenarios.

    Reference: docs/guides/THREADING.md - Thread Safety Guidelines
    """

    def test_concurrent_read_access_from_multiple_threads(self):
        """Test that multiple threads can safely read from the same instance.

        Validates that concurrent read operations from 10+ threads do not cause
        race conditions, data corruption, or access violations."""
        # Create a single instance
        reducer_input = ModelReducerInput[int](
            data=list(range(100)),
            reduction_type=EnumReductionType.FOLD,
            batch_size=500,
            window_size_ms=10000,
        )

        results = []
        errors = []

        def read_fields():
            """Read all fields from the instance."""
            try:
                # Read all fields multiple times
                for _ in range(10):
                    _ = reducer_input.data
                    _ = reducer_input.reduction_type
                    _ = reducer_input.operation_id
                    _ = reducer_input.batch_size
                    _ = reducer_input.window_size_ms
                    _ = reducer_input.metadata
                    _ = reducer_input.timestamp
                results.append(True)
            except Exception as e:
                errors.append(e)

        # Launch 15 threads to read concurrently
        threads = [threading.Thread(target=read_fields) for _ in range(15)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Validate no errors occurred
        assert len(errors) == 0, f"Errors during concurrent reads: {errors}"
        assert len(results) == 15, "Not all threads completed successfully"

    def test_concurrent_read_with_thread_pool(self):
        """Test concurrent reads using ThreadPoolExecutor.

        Validates that the model is safe to access from a thread pool,
        which is a common pattern in production systems."""
        reducer_input = ModelReducerInput[str](
            data=["a", "b", "c", "d", "e"],
            reduction_type=EnumReductionType.GROUP,
        )

        def access_model(iteration: int) -> tuple:
            """Access model fields and return values."""
            return (
                iteration,
                len(reducer_input.data),
                reducer_input.reduction_type,
                reducer_input.batch_size,
            )

        # Use thread pool to access model concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(access_model, i) for i in range(20)]
            results = [future.result() for future in futures]

        # Validate all accesses succeeded
        assert len(results) == 20
        # Validate data consistency across all threads
        for iteration, data_len, reduction_type, batch_size in results:
            assert data_len == 5
            assert reduction_type == EnumReductionType.GROUP
            assert batch_size == 1000  # Default value

    def test_immutability_prevents_race_conditions(self):
        """Test that immutability prevents write-based race conditions.

        Validates that the frozen model prevents concurrent modification attempts,
        ensuring thread safety through immutability."""
        reducer_input = ModelReducerInput[int](
            data=[1, 2, 3],
            reduction_type=EnumReductionType.FOLD,
        )

        errors = []

        def attempt_modification():
            """Attempt to modify fields (should fail)."""
            try:
                reducer_input.data = [4, 5, 6]  # type: ignore[misc]
            except ValidationError:
                errors.append("data_modification_blocked")

            try:
                reducer_input.batch_size = 2000  # type: ignore[misc]
            except ValidationError:
                errors.append("batch_size_modification_blocked")

        # Launch multiple threads attempting modifications
        threads = [threading.Thread(target=attempt_modification) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All modification attempts should be blocked
        assert len(errors) == 10  # 5 threads × 2 fields

    def test_serialization_thread_safety(self):
        """Test that serialization is thread-safe.

        Validates that multiple threads can serialize the same instance
        concurrently without corruption or deadlocks."""
        reducer_input = ModelReducerInput[dict](
            data=[{"key": f"value_{i}"} for i in range(50)],
            reduction_type=EnumReductionType.MERGE,
        )

        serialized_results = []
        errors = []

        def serialize_model():
            """Serialize model to dict and JSON."""
            try:
                dict_result = reducer_input.model_dump()
                json_result = reducer_input.model_dump_json()
                serialized_results.append((dict_result, json_result))
            except Exception as e:
                errors.append(e)

        # Launch threads to serialize concurrently
        threads = [threading.Thread(target=serialize_model) for _ in range(12)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Validate no errors and all serializations succeeded
        assert len(errors) == 0, f"Serialization errors: {errors}"
        assert len(serialized_results) == 12

        # Validate all serializations are identical
        first_dict = serialized_results[0][0]
        for dict_result, _ in serialized_results:
            assert dict_result["data"] == first_dict["data"]
            assert dict_result["reduction_type"] == first_dict["reduction_type"]


class TestModelReducerInputAsyncSafe:
    """Test async-safe behavior of ModelReducerInput.

    Validates that ModelReducerInput instances can be safely used in async
    contexts, including concurrent asyncio tasks and event loop scenarios.

    Reference: docs/guides/THREADING.md - Async Safety Guidelines
    """

    @pytest.mark.asyncio
    async def test_concurrent_async_read_access(self):
        """Test concurrent access from multiple asyncio tasks.

        Validates that multiple async tasks can safely read from the same
        instance without event loop conflicts or coroutine interference."""
        reducer_input = ModelReducerInput[int](
            data=list(range(100)),
            reduction_type=EnumReductionType.ACCUMULATE,
            batch_size=750,
        )

        async def read_fields() -> dict:
            """Async function to read all fields."""
            # Simulate async work
            await asyncio.sleep(0.001)

            return {
                "data_len": len(reducer_input.data),
                "reduction_type": reducer_input.reduction_type,
                "batch_size": reducer_input.batch_size,
                "operation_id": reducer_input.operation_id,
            }

        # Launch 20 concurrent async tasks
        tasks = [read_fields() for _ in range(20)]
        results = await asyncio.gather(*tasks)

        # Validate all tasks succeeded
        assert len(results) == 20
        # Validate data consistency
        for result in results:
            assert result["data_len"] == 100
            assert result["reduction_type"] == EnumReductionType.ACCUMULATE
            assert result["batch_size"] == 750

    @pytest.mark.asyncio
    async def test_async_serialization(self):
        """Test that serialization works correctly in async contexts.

        Validates that model serialization (dict/JSON) is safe to call from
        async functions without blocking the event loop."""
        reducer_input = ModelReducerInput[str](
            data=["alpha", "beta", "gamma", "delta"],
            reduction_type=EnumReductionType.DEDUPLICATE,
        )

        async def serialize_async() -> tuple:
            """Async serialization operation."""
            await asyncio.sleep(0.001)  # Simulate async work
            dict_result = reducer_input.model_dump()
            json_result = reducer_input.model_dump_json()
            return (dict_result, json_result)

        # Run multiple serializations concurrently
        tasks = [serialize_async() for _ in range(15)]
        results = await asyncio.gather(*tasks)

        # Validate all succeeded
        assert len(results) == 15
        # Validate consistency
        for dict_result, json_result in results:
            assert dict_result["data"] == ["alpha", "beta", "gamma", "delta"]
            assert "deduplicate" in json_result.lower()

    @pytest.mark.asyncio
    async def test_async_deserialization(self):
        """Test async-safe deserialization from dict and JSON.

        Validates that model_validate and model_validate_json work correctly
        in async contexts without blocking or coroutine conflicts."""

        async def create_and_serialize() -> str:
            """Create instance and serialize to JSON."""
            reducer_input = ModelReducerInput[int](
                data=[10, 20, 30],
                reduction_type=EnumReductionType.FOLD,
            )
            await asyncio.sleep(0.001)
            return reducer_input.model_dump_json()

        async def deserialize(json_str: str) -> ModelReducerInput[int]:
            """Deserialize from JSON."""
            await asyncio.sleep(0.001)
            return ModelReducerInput[int].model_validate_json(json_str)

        # Create and serialize
        json_str = await create_and_serialize()

        # Deserialize concurrently
        tasks = [deserialize(json_str) for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # Validate all deserializations succeeded
        assert len(results) == 10
        for instance in results:
            assert instance.data == [10, 20, 30]
            assert instance.reduction_type == EnumReductionType.FOLD

    @pytest.mark.asyncio
    async def test_mixed_sync_async_access(self):
        """Test that instance can be accessed from both sync and async contexts.

        Validates that the model is safe to use in mixed synchronous and
        asynchronous code, which is common in production systems."""
        reducer_input = ModelReducerInput[dict](
            data=[{"id": i, "value": i * 10} for i in range(20)],
            reduction_type=EnumReductionType.AGGREGATE,
        )

        # Sync access
        sync_data_len = len(reducer_input.data)
        sync_type = reducer_input.reduction_type

        async def async_access() -> tuple:
            """Async access to same instance."""
            await asyncio.sleep(0.001)
            return (len(reducer_input.data), reducer_input.reduction_type)

        # Run async access multiple times
        tasks = [async_access() for _ in range(10)]
        async_results = await asyncio.gather(*tasks)

        # Validate consistency between sync and async access
        assert sync_data_len == 20
        assert sync_type == EnumReductionType.AGGREGATE
        for data_len, reduction_type in async_results:
            assert data_len == sync_data_len
            assert reduction_type == sync_type


class TestModelReducerInputUUIDFormatPreservation:
    """Test UUID format preservation through serialization.

    Validates that UUID fields maintain correct format and type through
    serialization/deserialization cycles, as required by distributed systems
    and event-driven architectures.
    """

    def test_operation_id_uuid_format_in_dict(self):
        """Test that operation_id preserves UUID format in dict serialization.

        Validates that UUID objects are correctly represented in dictionary
        form and can be reconstructed without format loss."""
        test_uuid = uuid4()

        reducer_input = ModelReducerInput[int](
            data=[1, 2, 3],
            reduction_type=EnumReductionType.FOLD,
            operation_id=test_uuid,
        )

        # Serialize to dict
        data_dict = reducer_input.model_dump()

        # UUID should be preserved as UUID object in dict
        assert isinstance(data_dict["operation_id"], UUID)
        assert data_dict["operation_id"] == test_uuid
        assert str(data_dict["operation_id"]) == str(test_uuid)

    def test_operation_id_uuid_format_in_json(self):
        """Test that operation_id preserves UUID format in JSON serialization.

        Validates that UUID objects are correctly serialized to string format
        in JSON and maintain standard UUID string representation."""
        test_uuid = uuid4()

        reducer_input = ModelReducerInput[int](
            data=[1, 2, 3],
            reduction_type=EnumReductionType.FOLD,
            operation_id=test_uuid,
        )

        # Serialize to JSON
        json_str = reducer_input.model_dump_json()

        # UUID should be serialized as string in JSON
        assert str(test_uuid) in json_str
        # Validate standard UUID format (8-4-4-4-12 hex digits)
        uuid_str = str(test_uuid)
        assert len(uuid_str) == 36
        assert uuid_str.count("-") == 4

    def test_uuid_roundtrip_preservation(self):
        """Test UUID format preservation through complete roundtrip.

        Validates that UUID objects survive dict→JSON→dict→model cycles
        without format corruption or type loss."""
        original_uuid = uuid4()

        # Create original instance
        original = ModelReducerInput[int](
            data=[10, 20, 30],
            reduction_type=EnumReductionType.ACCUMULATE,
            operation_id=original_uuid,
        )

        # Roundtrip through dict
        dict_data = original.model_dump()
        from_dict = ModelReducerInput[int].model_validate(dict_data)
        assert isinstance(from_dict.operation_id, UUID)
        assert from_dict.operation_id == original_uuid

        # Roundtrip through JSON
        json_str = original.model_dump_json()
        from_json = ModelReducerInput[int].model_validate_json(json_str)
        assert isinstance(from_json.operation_id, UUID)
        assert from_json.operation_id == original_uuid

    def test_uuid_string_input_conversion(self):
        """Test that UUID strings are correctly converted to UUID objects.

        Validates that the model accepts UUID strings and converts them to
        proper UUID objects during validation."""
        uuid_str = str(uuid4())

        reducer_input = ModelReducerInput[int](
            data=[1, 2, 3],
            reduction_type=EnumReductionType.FOLD,
            operation_id=uuid_str,  # type: ignore[arg-type]
        )

        # Should be converted to UUID object
        assert isinstance(reducer_input.operation_id, UUID)
        assert str(reducer_input.operation_id) == uuid_str

    def test_metadata_correlation_id_preservation(self):
        """Test that metadata correlation_id (string) is preserved.

        Validates that correlation IDs in metadata maintain their format
        through serialization, supporting distributed tracing systems."""
        correlation_id = f"corr-{uuid4()}"

        metadata = ModelReducerMetadata(
            source="test_source",
            correlation_id=correlation_id,
        )

        reducer_input = ModelReducerInput[int](
            data=[1, 2, 3],
            reduction_type=EnumReductionType.FOLD,
            metadata=metadata,
        )

        # Roundtrip through JSON
        json_str = reducer_input.model_dump_json()
        restored = ModelReducerInput[int].model_validate_json(json_str)

        # Correlation ID should be preserved exactly
        assert restored.metadata.correlation_id == correlation_id
        assert correlation_id in json_str

    def test_metadata_uuid_fields_preservation(self):
        """Test that metadata UUID fields (partition_id, window_id) are preserved.

        Validates that UUID fields in nested metadata objects maintain correct
        format through serialization cycles."""
        partition_id = uuid4()
        window_id = uuid4()

        metadata = ModelReducerMetadata(
            source="event_stream",
            partition_id=partition_id,
            window_id=window_id,
        )

        reducer_input = ModelReducerInput[int](
            data=[1, 2, 3],
            reduction_type=EnumReductionType.GROUP,
            metadata=metadata,
        )

        # Roundtrip through dict
        dict_data = reducer_input.model_dump()
        restored = ModelReducerInput[int].model_validate(dict_data)

        # UUIDs should be preserved
        assert isinstance(restored.metadata.partition_id, UUID)
        assert isinstance(restored.metadata.window_id, UUID)
        assert restored.metadata.partition_id == partition_id
        assert restored.metadata.window_id == window_id
