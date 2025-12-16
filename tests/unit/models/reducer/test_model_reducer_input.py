"""
Unit tests for ModelReducerInput[T].

This module provides comprehensive tests for the generic ModelReducerInput model
including:
- Model instantiation with minimal and full fields
- Generic type parameter validation (int, str, dict, list, custom models)
- Field validation (required/optional, ranges, constraints)
- Serialization/deserialization (dict and JSON)
- Frozen behavior (immutability)
- Edge cases (empty data, large data, nested types, unicode, etc.)
- Thread safety via immutability

Test Pattern Reference:
    - tests/unit/models/test_model_intent.py (625 lines)
    - tests/unit/models/fsm/test_model_fsm_state_snapshot.py (572 lines)
    - tests/unit/models/fsm/test_model_fsm_transition_result.py (717 lines)
"""

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

    def test_generic_type_parameter_int(self):
        """Test ModelReducerInput with int type parameter."""
        reducer_input = ModelReducerInput[int](
            data=[10, 20, 30, 40],
            reduction_type=EnumReductionType.ACCUMULATE,
        )

        assert isinstance(reducer_input, ModelReducerInput)
        assert all(isinstance(x, int) for x in reducer_input.data)
        assert reducer_input.data == [10, 20, 30, 40]

    def test_generic_type_parameter_str(self):
        """Test ModelReducerInput with str type parameter."""
        reducer_input = ModelReducerInput[str](
            data=["apple", "banana", "cherry"],
            reduction_type=EnumReductionType.DEDUPLICATE,
        )

        assert isinstance(reducer_input, ModelReducerInput)
        assert all(isinstance(x, str) for x in reducer_input.data)
        assert reducer_input.data == ["apple", "banana", "cherry"]

    def test_generic_type_parameter_dict(self):
        """Test ModelReducerInput with dict type parameter."""
        test_data = [
            {"key": "a", "value": 1},
            {"key": "b", "value": 2},
            {"key": "c", "value": 3},
        ]

        reducer_input = ModelReducerInput[dict](
            data=test_data,
            reduction_type=EnumReductionType.MERGE,
        )

        assert isinstance(reducer_input, ModelReducerInput)
        assert all(isinstance(x, dict) for x in reducer_input.data)
        assert reducer_input.data == test_data

    def test_generic_type_parameter_list(self):
        """Test ModelReducerInput with list type parameter."""
        test_data = [[1, 2], [3, 4], [5, 6]]

        reducer_input = ModelReducerInput[list](
            data=test_data,
            reduction_type=EnumReductionType.AGGREGATE,
        )

        assert isinstance(reducer_input, ModelReducerInput)
        assert all(isinstance(x, list) for x in reducer_input.data)
        assert reducer_input.data == test_data

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

    def test_required_fields_data_missing(self):
        """Test that missing data field raises ValidationError.

        Validates that data is a required field and cannot be omitted during
        model instantiation, as reducer inputs must have data to process."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerInput[int](reduction_type=EnumReductionType.FOLD)

        assert "data" in str(exc_info.value)

    def test_required_fields_reduction_type_missing(self):
        """Test that missing reduction_type field raises ValidationError.

        Validates that reduction_type is a required field specifying the operation
        to be performed on the data (FOLD, ACCUMULATE, MERGE, etc)."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerInput[int](data=[1, 2, 3])

        assert "reduction_type" in str(exc_info.value)

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
                data="not a list",  # type: ignore[misc]
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
                reduction_type="invalid_reduction_type",  # type: ignore[misc]
            )
        assert "reduction_type" in str(exc_info.value).lower()

    def test_batch_size_validation_negative(self):
        """Test that negative batch_size raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerInput[int](
                data=[1, 2],
                reduction_type=EnumReductionType.FOLD,
                batch_size=-1,
            )
        assert "greater than 0" in str(exc_info.value)

    def test_batch_size_validation_zero(self):
        """Test that zero batch_size raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerInput[int](
                data=[1, 2],
                reduction_type=EnumReductionType.FOLD,
                batch_size=0,
            )
        assert "greater than 0" in str(exc_info.value)

    def test_batch_size_validation_positive(self):
        """Test that positive batch_size values are accepted."""
        for batch_size in [1, 100, 1000, 5000, 10000]:
            reducer_input = ModelReducerInput[int](
                data=[1, 2],
                reduction_type=EnumReductionType.FOLD,
                batch_size=batch_size,
            )
            assert reducer_input.batch_size == batch_size

    def test_batch_size_validation_exceeds_max(self):
        """Test that batch_size exceeding 10000 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerInput[int](
                data=[1, 2],
                reduction_type=EnumReductionType.FOLD,
                batch_size=10001,
            )
        assert "less than or equal to 10000" in str(exc_info.value)

    def test_window_size_ms_validation_below_min(self):
        """Test that window_size_ms below 1000 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerInput[int](
                data=[1, 2],
                reduction_type=EnumReductionType.FOLD,
                window_size_ms=999,
            )
        assert "greater than or equal to 1000" in str(exc_info.value)

    def test_window_size_ms_validation_at_min(self):
        """Test that window_size_ms at minimum (1000) is accepted."""
        reducer_input = ModelReducerInput[int](
            data=[1, 2],
            reduction_type=EnumReductionType.FOLD,
            window_size_ms=1000,
        )
        assert reducer_input.window_size_ms == 1000

    def test_window_size_ms_validation_positive(self):
        """Test that valid window_size_ms values are accepted."""
        for window_size_ms in [1000, 5000, 30000, 60000]:
            reducer_input = ModelReducerInput[int](
                data=[1, 2],
                reduction_type=EnumReductionType.FOLD,
                window_size_ms=window_size_ms,
            )
            assert reducer_input.window_size_ms == window_size_ms

    def test_window_size_ms_validation_exceeds_max(self):
        """Test that window_size_ms exceeding 60000 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerInput[int](
                data=[1, 2],
                reduction_type=EnumReductionType.FOLD,
                window_size_ms=60001,
            )
        assert "less than or equal to 60000" in str(exc_info.value)

    def test_invalid_field_types(self):
        """Test that invalid field types raise ValidationError.

        Validates comprehensive type checking across all fields, ensuring that
        incorrect types (wrong enums, invalid UUIDs, etc) are rejected."""
        # Invalid data type (not a list)
        with pytest.raises(ValidationError):
            ModelReducerInput[int](
                data=123,  # type: ignore[misc]
                reduction_type=EnumReductionType.FOLD,
            )

        # Invalid reduction_type
        with pytest.raises(ValidationError):
            ModelReducerInput[int](
                data=[1, 2],
                reduction_type="not_an_enum",  # type: ignore[misc]
            )

        # Invalid conflict_resolution
        with pytest.raises(ValidationError):
            ModelReducerInput[int](
                data=[1, 2],
                reduction_type=EnumReductionType.FOLD,
                conflict_resolution="invalid",  # type: ignore[misc]
            )

        # Invalid streaming_mode
        with pytest.raises(ValidationError):
            ModelReducerInput[int](
                data=[1, 2],
                reduction_type=EnumReductionType.FOLD,
                streaming_mode="invalid",  # type: ignore[misc]
            )

    def test_extra_fields_rejected(self):
        """Test that extra fields are rejected (model_config extra='forbid').

        Validates that the model enforces strict field validation, rejecting any
        fields not defined in the schema to prevent typos and data corruption."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerInput[int](
                data=[1, 2],
                reduction_type=EnumReductionType.FOLD,
                extra_field="should_fail",  # type: ignore[misc]
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

    def test_roundtrip_serialization_with_int_data(self):
        """Test roundtrip serialization with int data."""
        original = ModelReducerInput[int](
            data=[100, 200, 300],
            reduction_type=EnumReductionType.ACCUMULATE,
            batch_size=250,
        )

        # Serialize
        data = original.model_dump()

        # Deserialize
        restored = ModelReducerInput[int].model_validate(data)

        assert restored.data == original.data
        assert restored.reduction_type == original.reduction_type
        assert restored.batch_size == original.batch_size
        assert restored.operation_id == original.operation_id

    def test_roundtrip_serialization_with_str_data(self):
        """Test roundtrip serialization with str data."""
        original = ModelReducerInput[str](
            data=["alpha", "beta", "gamma"],
            reduction_type=EnumReductionType.DEDUPLICATE,
            window_size_ms=25000,
        )

        # Serialize
        json_str = original.model_dump_json()

        # Deserialize
        restored = ModelReducerInput[str].model_validate_json(json_str)

        assert restored.data == original.data
        assert restored.reduction_type == original.reduction_type
        assert restored.window_size_ms == original.window_size_ms

    def test_roundtrip_serialization_with_dict_data(self):
        """Test roundtrip serialization with dict data."""
        original = ModelReducerInput[dict](
            data=[{"key": "a"}, {"key": "b"}],
            reduction_type=EnumReductionType.MERGE,
        )

        data = original.model_dump()
        restored = ModelReducerInput[dict].model_validate(data)

        assert restored.data == original.data
        assert restored.reduction_type == original.reduction_type

    def test_roundtrip_serialization_with_list_data(self):
        """Test roundtrip serialization with list data."""
        original = ModelReducerInput[list](
            data=[[1, 2], [3, 4]],
            reduction_type=EnumReductionType.AGGREGATE,
        )

        json_str = original.model_dump_json()
        restored = ModelReducerInput[list].model_validate_json(json_str)

        assert restored.data == original.data
        assert restored.reduction_type == original.reduction_type

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

    def test_type_parameter_preserves_int_type(self):
        """Test that int type parameter is preserved."""
        reducer_input = ModelReducerInput[int](
            data=[1, 2, 3, 4, 5],
            reduction_type=EnumReductionType.FOLD,
        )

        assert all(isinstance(x, int) for x in reducer_input.data)

    def test_type_parameter_preserves_str_type(self):
        """Test that str type parameter is preserved."""
        reducer_input = ModelReducerInput[str](
            data=["one", "two", "three"],
            reduction_type=EnumReductionType.GROUP,
        )

        assert all(isinstance(x, str) for x in reducer_input.data)

    def test_type_parameter_preserves_dict_type(self):
        """Test that dict type parameter is preserved."""
        reducer_input = ModelReducerInput[dict](
            data=[{"a": 1}, {"b": 2}, {"c": 3}],
            reduction_type=EnumReductionType.MERGE,
        )

        assert all(isinstance(x, dict) for x in reducer_input.data)

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

    def test_data_field_immutable(self):
        """Test that data field cannot be modified after creation."""
        reducer_input = ModelReducerInput[int](
            data=[1, 2, 3],
            reduction_type=EnumReductionType.FOLD,
        )

        with pytest.raises(ValidationError) as exc_info:
            reducer_input.data = [4, 5, 6]  # type: ignore[misc]

        assert "frozen" in str(exc_info.value).lower()

    def test_reduction_type_field_immutable(self):
        """Test that reduction_type field cannot be modified."""
        reducer_input = ModelReducerInput[int](
            data=[1, 2, 3],
            reduction_type=EnumReductionType.FOLD,
        )

        with pytest.raises(ValidationError) as exc_info:
            reducer_input.reduction_type = EnumReductionType.AGGREGATE  # type: ignore[misc]

        assert "frozen" in str(exc_info.value).lower()

    def test_batch_size_field_immutable(self):
        """Test that batch_size field cannot be modified."""
        reducer_input = ModelReducerInput[int](
            data=[1, 2, 3],
            reduction_type=EnumReductionType.FOLD,
            batch_size=500,
        )

        with pytest.raises(ValidationError) as exc_info:
            reducer_input.batch_size = 1000  # type: ignore[misc]

        assert "frozen" in str(exc_info.value).lower()

    def test_window_size_ms_field_immutable(self):
        """Test that window_size_ms field cannot be modified."""
        reducer_input = ModelReducerInput[int](
            data=[1, 2, 3],
            reduction_type=EnumReductionType.FOLD,
            window_size_ms=10000,
        )

        with pytest.raises(ValidationError) as exc_info:
            reducer_input.window_size_ms = 20000  # type: ignore[misc]

        assert "frozen" in str(exc_info.value).lower()

    def test_operation_id_field_immutable(self):
        """Test that operation_id field cannot be modified."""
        reducer_input = ModelReducerInput[int](
            data=[1, 2, 3],
            reduction_type=EnumReductionType.FOLD,
        )

        with pytest.raises(ValidationError) as exc_info:
            reducer_input.operation_id = uuid4()  # type: ignore[misc]

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
            reducer_input.new_field = "value"  # type: ignore[misc]

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

    def test_boundary_values_batch_size_min(self):
        """Test batch_size at minimum boundary (1)."""
        reducer_input = ModelReducerInput[int](
            data=[1, 2],
            reduction_type=EnumReductionType.FOLD,
            batch_size=1,
        )

        assert reducer_input.batch_size == 1

    def test_boundary_values_batch_size_max(self):
        """Test batch_size at maximum boundary (10000)."""
        reducer_input = ModelReducerInput[int](
            data=[1, 2],
            reduction_type=EnumReductionType.FOLD,
            batch_size=10000,
        )

        assert reducer_input.batch_size == 10000

    def test_boundary_values_window_size_ms_min(self):
        """Test window_size_ms at minimum boundary (1000)."""
        reducer_input = ModelReducerInput[int](
            data=[1, 2],
            reduction_type=EnumReductionType.FOLD,
            window_size_ms=1000,
        )

        assert reducer_input.window_size_ms == 1000

    def test_boundary_values_window_size_ms_max(self):
        """Test window_size_ms at maximum boundary (60000)."""
        reducer_input = ModelReducerInput[int](
            data=[1, 2],
            reduction_type=EnumReductionType.FOLD,
            window_size_ms=60000,
        )

        assert reducer_input.window_size_ms == 60000

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
