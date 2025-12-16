"""Unit tests for ModelReducerOutput[T].

Tests all aspects of the reducer output model including:
- Model instantiation with generic type parameters
- Field validation and boundary conditions
- Frozen behavior (immutability)
- Serialization/deserialization
- Generic typing behavior
- Edge cases and boundary values

Architecture Context:
    ModelReducerOutput[T] is the output model for REDUCER nodes, containing
    the result of FSM-driven state management and data aggregation operations.

Related Models:
    - ModelReducerInput[T] - Input contract for REDUCER nodes
    - ModelIntent - Intent pattern for side effects
    - ModelReducerMetadata - Metadata container for operations

Notes:
    - Parametrized tests reduce duplication while maintaining comprehensive coverage
    - All tests use pytest markers (@pytest.mark.unit)
    - Thread-safe for pytest-xdist parallel execution
"""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_reducer_types import EnumReductionType, EnumStreamingMode
from omnibase_core.models.common.model_reducer_metadata import ModelReducerMetadata
from omnibase_core.models.reducer.model_intent import ModelIntent
from omnibase_core.models.reducer.model_reducer_output import ModelReducerOutput

pytestmark = pytest.mark.unit


# Test helper model for generic type testing
class ModelTestData(BaseModel):
    """Test model for generic type parameter testing."""

    value: int
    label: str


class TestModelReducerOutputInstantiation:
    """Test ModelReducerOutput instantiation with various configurations."""

    def test_create_with_minimal_fields(self):
        """Test creating ModelReducerOutput with only required fields.

        Validates that the model can be instantiated with required fields only,
        and all optional fields receive their default values correctly."""
        operation_id = uuid4()

        output = ModelReducerOutput[int](
            result=42,
            operation_id=operation_id,
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.5,
            items_processed=100,
        )

        assert output is not None
        assert isinstance(output, ModelReducerOutput)
        assert output.result == 42
        assert output.operation_id == operation_id
        assert output.reduction_type == EnumReductionType.FOLD
        assert output.processing_time_ms == 10.5
        assert output.items_processed == 100
        # Test defaults
        assert output.conflicts_resolved == 0
        assert output.streaming_mode == EnumStreamingMode.BATCH
        assert output.batches_processed == 1
        assert output.intents == ()
        assert isinstance(output.metadata, ModelReducerMetadata)
        assert isinstance(output.timestamp, datetime)

    def test_create_with_all_fields(self):
        """Test creating ModelReducerOutput with all fields populated.

        Validates that all fields (required and optional) can be explicitly set
        and are correctly stored without defaults overriding provided values."""
        operation_id = uuid4()
        intent_id = uuid4()
        window_id = uuid4()

        intent = ModelIntent(
            intent_id=intent_id,
            intent_type="log_metrics",
            target="metrics_service",
            payload={"metric": "reduction_time", "value": 42.5},
        )

        metadata = ModelReducerMetadata(
            source="api_gateway",
            trace_id="trace123",
            correlation_id="corr456",
            group_key="user_group_1",
            window_id=window_id,
            tags=["production", "high_priority"],
            trigger="user_action",
        )

        output = ModelReducerOutput[dict](
            result={"status": "success", "count": 10},
            operation_id=operation_id,
            reduction_type=EnumReductionType.AGGREGATE,
            processing_time_ms=42.75,
            items_processed=250,
            conflicts_resolved=3,
            streaming_mode=EnumStreamingMode.WINDOWED,
            batches_processed=5,
            intents=(intent,),
            metadata=metadata,
        )

        assert output.result == {"status": "success", "count": 10}
        assert output.operation_id == operation_id
        assert output.reduction_type == EnumReductionType.AGGREGATE
        assert output.processing_time_ms == 42.75
        assert output.items_processed == 250
        assert output.conflicts_resolved == 3
        assert output.streaming_mode == EnumStreamingMode.WINDOWED
        assert output.batches_processed == 5
        assert len(output.intents) == 1
        assert output.intents[0].intent_id == intent_id
        assert output.metadata.source == "api_gateway"
        assert output.metadata.trace_id == "trace123"
        assert output.metadata.window_id == window_id

    @pytest.mark.parametrize(
        ("type_param", "result", "reduction_type", "expected_type"),
        [
            pytest.param(int, 999, EnumReductionType.FOLD, int, id="int"),
            pytest.param(
                str, "aggregation_complete", EnumReductionType.ACCUMULATE, str, id="str"
            ),
            pytest.param(
                dict,
                {"total": 500, "average": 50.0, "max": 100},
                EnumReductionType.AGGREGATE,
                dict,
                id="dict",
            ),
            pytest.param(
                list, [1, 2, 3, 5, 8, 13, 21], EnumReductionType.FILTER, list, id="list"
            ),
        ],
    )
    def test_generic_type_parameter(
        self, type_param, result, reduction_type, expected_type
    ):
        """Test ModelReducerOutput with various generic type parameters.

        Validates that the generic type parameter system correctly handles int, str,
        dict, and list types for results."""
        output = ModelReducerOutput[type_param](
            result=result,
            operation_id=uuid4(),
            reduction_type=reduction_type,
            processing_time_ms=10.0,
            items_processed=5,
        )

        assert isinstance(output.result, expected_type)
        assert output.result == result

    def test_generic_type_parameter_custom_model(self):
        """Test ModelReducerOutput with custom Pydantic model type parameter.

        Validates that custom Pydantic models can be used as result types,
        enabling strongly-typed domain objects in reducer outputs."""
        test_data = ModelTestData(value=42, label="answer")

        output = ModelReducerOutput[ModelTestData](
            result=test_data,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.TRANSFORM,
            processing_time_ms=6.5,
            items_processed=1,
        )

        assert isinstance(output.result, ModelTestData)
        assert output.result.value == 42
        assert output.result.label == "answer"


class TestModelReducerOutputValidation:
    """Test ModelReducerOutput field validation."""

    @pytest.mark.parametrize(
        ("missing_field", "field_name"),
        [
            pytest.param(
                {
                    "operation_id": uuid4(),
                    "reduction_type": EnumReductionType.FOLD,
                    "processing_time_ms": 10.0,
                    "items_processed": 5,
                },
                "result",
                id="result",
            ),
            pytest.param(
                {
                    "result": 42,
                    "reduction_type": EnumReductionType.FOLD,
                    "processing_time_ms": 10.0,
                    "items_processed": 5,
                },
                "operation_id",
                id="operation_id",
            ),
            pytest.param(
                {
                    "result": 42,
                    "operation_id": uuid4(),
                    "processing_time_ms": 10.0,
                    "items_processed": 5,
                },
                "reduction_type",
                id="reduction_type",
            ),
            pytest.param(
                {
                    "result": 42,
                    "operation_id": uuid4(),
                    "reduction_type": EnumReductionType.FOLD,
                    "items_processed": 5,
                },
                "processing_time_ms",
                id="processing_time_ms",
            ),
            pytest.param(
                {
                    "result": 42,
                    "operation_id": uuid4(),
                    "reduction_type": EnumReductionType.FOLD,
                    "processing_time_ms": 10.0,
                },
                "items_processed",
                id="items_processed",
            ),
        ],
    )
    def test_required_field_missing(self, missing_field, field_name):
        """Test that required fields raise ValidationError when missing.

        Validates that all required fields (result, operation_id, reduction_type,
        processing_time_ms, items_processed) must be provided."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerOutput[int](**missing_field)

        error_msg = str(exc_info.value)
        assert field_name in error_msg
        assert "Field required" in error_msg

    def test_result_type_validation(self):
        """Test that result field accepts correct type.

        Validates that the result field correctly stores values matching the
        generic type parameter."""
        # Should accept int when typed as int
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )
        assert output.result == 42

    def test_operation_id_uuid_validation(self):
        """Test that operation_id must be a valid UUID.

        Validates UUID type enforcement and automatic conversion from string
        representations to UUID objects."""
        valid_uuid = uuid4()

        output = ModelReducerOutput[int](
            result=42,
            operation_id=valid_uuid,
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )

        assert isinstance(output.operation_id, UUID)
        assert output.operation_id == valid_uuid

        # Test that string UUIDs are converted
        uuid_str = str(uuid4())
        output2 = ModelReducerOutput[int](
            result=42,
            operation_id=uuid_str,  # type: ignore[arg-type]
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )
        assert isinstance(output2.operation_id, UUID)

    def test_reduction_type_validation(self):
        """Test that reduction_type must be a valid EnumReductionType.

        Validates that all enum values are accepted and invalid strings are rejected,
        ensuring type safety for reduction operations."""
        # Test all valid reduction types
        for reduction_type in EnumReductionType:
            output = ModelReducerOutput[int](
                result=42,
                operation_id=uuid4(),
                reduction_type=reduction_type,
                processing_time_ms=10.0,
                items_processed=5,
            )
            assert output.reduction_type == reduction_type

        # Test invalid reduction type
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerOutput[int](
                result=42,
                operation_id=uuid4(),
                reduction_type="invalid_type",  # type: ignore[arg-type]
                processing_time_ms=10.0,
                items_processed=5,
            )

        assert "reduction_type" in str(exc_info.value)

    @pytest.mark.parametrize(
        ("value", "description"),
        [
            pytest.param(-1.0, "negative", id="negative"),
            pytest.param(0.0, "zero", id="zero"),
            pytest.param(42.5, "positive", id="positive"),
        ],
    )
    def test_processing_time_ms_validation(self, value, description):
        """Test processing_time_ms validation.

        Note: The model does not enforce non-negative constraints on processing time,
        allowing flexibility for special cases or error conditions."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=value,
            items_processed=5,
        )

        assert output.processing_time_ms == value

    @pytest.mark.parametrize(
        ("value", "description"),
        [
            pytest.param(-1, "negative", id="negative"),
            pytest.param(0, "zero", id="zero"),
            pytest.param(1000, "positive", id="positive"),
        ],
    )
    def test_items_processed_validation(self, value, description):
        """Test items_processed validation.

        Note: The model does not enforce non-negative constraints on item counts,
        allowing flexibility for special cases or rollback scenarios."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=value,
        )

        assert output.items_processed == value

    def test_invalid_field_types(self):
        """Test that invalid field types are rejected.

        Validates comprehensive type checking across all fields, ensuring that
        incorrect types are rejected with clear validation error messages."""
        # Invalid operation_id (not UUID-compatible)
        with pytest.raises(ValidationError):
            ModelReducerOutput[int](
                result=42,
                operation_id="not-a-uuid",  # type: ignore[arg-type]
                reduction_type=EnumReductionType.FOLD,
                processing_time_ms=10.0,
                items_processed=5,
            )

        # Invalid processing_time_ms (string)
        with pytest.raises(ValidationError):
            ModelReducerOutput[int](
                result=42,
                operation_id=uuid4(),
                reduction_type=EnumReductionType.FOLD,
                processing_time_ms="not-a-number",  # type: ignore[arg-type]
                items_processed=5,
            )

        # Invalid items_processed (float instead of int)
        # Note: Pydantic may coerce float to int, so use string
        with pytest.raises(ValidationError):
            ModelReducerOutput[int](
                result=42,
                operation_id=uuid4(),
                reduction_type=EnumReductionType.FOLD,
                processing_time_ms=10.0,
                items_processed="not-a-number",  # type: ignore[arg-type]
            )

    def test_extra_fields_rejected(self):
        """Test that extra fields are rejected (extra='forbid').

        Validates that the model enforces strict field validation, rejecting any
        fields not defined in the schema to prevent typos and data corruption."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerOutput[int](
                result=42,
                operation_id=uuid4(),
                reduction_type=EnumReductionType.FOLD,
                processing_time_ms=10.0,
                items_processed=5,
                extra_field="should_fail",  # type: ignore[misc]
            )

        error_msg = str(exc_info.value)
        assert "extra_field" in error_msg
        assert "Extra inputs are not permitted" in error_msg


class TestModelReducerOutputSerialization:
    """Test ModelReducerOutput serialization and deserialization."""

    def test_model_dump(self):
        """Test serializing output to dictionary.

        Validates that the model can be converted to a dictionary representation
        with all fields (result, metadata, intents) preserved correctly."""
        operation_id = uuid4()

        output = ModelReducerOutput[int](
            result=42,
            operation_id=operation_id,
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.5,
            items_processed=100,
            conflicts_resolved=2,
        )

        data = output.model_dump()

        assert isinstance(data, dict)
        assert data["result"] == 42
        assert data["operation_id"] == operation_id
        assert data["reduction_type"] == EnumReductionType.FOLD
        assert data["processing_time_ms"] == 10.5
        assert data["items_processed"] == 100
        assert data["conflicts_resolved"] == 2
        assert "timestamp" in data

    def test_model_dump_json(self):
        """Test serializing output to JSON string.

        Validates that the model can be serialized to JSON format for network
        transmission, storage, and cross-service communication."""
        output = ModelReducerOutput[str](
            result="success",
            operation_id=uuid4(),
            reduction_type=EnumReductionType.ACCUMULATE,
            processing_time_ms=8.3,
            items_processed=50,
        )

        json_str = output.model_dump_json()

        assert isinstance(json_str, str)
        assert "result" in json_str
        assert "success" in json_str
        assert "operation_id" in json_str
        assert "reduction_type" in json_str
        assert "processing_time_ms" in json_str
        assert "items_processed" in json_str

    def test_model_validate(self):
        """Test deserializing output from dictionary.

        Validates that a dictionary can be converted back to a ModelReducerOutput
        instance with all fields correctly reconstructed and types preserved."""
        operation_id = uuid4()

        data = {
            "result": 42,
            "operation_id": operation_id,
            "reduction_type": EnumReductionType.FOLD,
            "processing_time_ms": 10.5,
            "items_processed": 100,
        }

        output = ModelReducerOutput[int].model_validate(data)

        assert output.result == 42
        assert output.operation_id == operation_id
        assert output.reduction_type == EnumReductionType.FOLD
        assert output.processing_time_ms == 10.5
        assert output.items_processed == 100

    def test_model_validate_json(self):
        """Test deserializing output from JSON string.

        Validates that a JSON string can be deserialized back to a ModelReducerOutput
        instance with proper type conversions (strings→UUIDs, enums, etc)."""
        operation_id = str(uuid4())

        json_str = f"""{{
            "result": "completed",
            "operation_id": "{operation_id}",
            "reduction_type": "accumulate",
            "processing_time_ms": 8.3,
            "items_processed": 50
        }}"""

        output = ModelReducerOutput[str].model_validate_json(json_str)

        assert output.result == "completed"
        assert str(output.operation_id) == operation_id
        assert output.reduction_type == EnumReductionType.ACCUMULATE
        assert output.processing_time_ms == 8.3
        assert output.items_processed == 50

    @pytest.mark.parametrize(
        ("type_param", "result", "reduction_type"),
        [
            pytest.param(int, 999, EnumReductionType.FOLD, id="int"),
            pytest.param(
                dict,
                {"total": 500, "count": 10, "average": 50.0},
                EnumReductionType.AGGREGATE,
                id="dict",
            ),
            pytest.param(
                list, [1, 2, 3, 5, 8, 13], EnumReductionType.FILTER, id="list"
            ),
        ],
    )
    def test_roundtrip_serialization(self, type_param, result, reduction_type):
        """Test roundtrip serialization for various result types.

        Validates that results can be serialized to dict/JSON and back without loss
        of data or type information."""
        original = ModelReducerOutput[type_param](
            result=result,
            operation_id=uuid4(),
            reduction_type=reduction_type,
            processing_time_ms=10.0,
            items_processed=5,
        )

        # Serialize and deserialize
        data = original.model_dump()
        restored = ModelReducerOutput[type_param].model_validate(data)

        assert restored.result == original.result
        assert restored.operation_id == original.operation_id
        assert restored.reduction_type == original.reduction_type
        assert restored.processing_time_ms == original.processing_time_ms
        assert restored.items_processed == original.items_processed

    def test_uuid_serialization_format(self):
        """Test that operation_id is serialized as string in JSON."""
        operation_id = uuid4()

        output = ModelReducerOutput[int](
            result=42,
            operation_id=operation_id,
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )

        json_str = output.model_dump_json()

        # UUID should be serialized as string
        assert str(operation_id) in json_str

    def test_roundtrip_preserves_all_fields(self):
        """Test that roundtrip serialization preserves all fields.

        Validates comprehensive field preservation including complex nested metadata,
        intents, and all optional fields through complete serialization cycles."""
        operation_id = uuid4()
        window_id = uuid4()

        intent = ModelIntent(
            intent_type="log",
            target="service",
            payload={"key": "value"},
        )

        metadata = ModelReducerMetadata(
            source="test_source",
            trace_id="trace123",
            correlation_id="corr456",
            window_id=window_id,
            tags=["test", "production"],
        )

        original = ModelReducerOutput[int](
            result=42,
            operation_id=operation_id,
            reduction_type=EnumReductionType.AGGREGATE,
            processing_time_ms=15.5,
            items_processed=100,
            conflicts_resolved=5,
            streaming_mode=EnumStreamingMode.WINDOWED,
            batches_processed=3,
            intents=(intent,),
            metadata=metadata,
        )

        # Serialize and deserialize
        data = original.model_dump()
        restored = ModelReducerOutput[int].model_validate(data)

        assert restored.result == original.result
        assert restored.operation_id == original.operation_id
        assert restored.reduction_type == original.reduction_type
        assert restored.conflicts_resolved == original.conflicts_resolved
        assert restored.streaming_mode == original.streaming_mode
        assert restored.batches_processed == original.batches_processed
        assert len(restored.intents) == len(original.intents)
        assert restored.metadata.source == original.metadata.source

    def test_serialization_handles_optional_fields(self):
        """Test that serialization correctly handles optional metadata fields.

        Validates that models created with minimal fields serialize correctly with
        default values properly applied during deserialization."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )

        # Should serialize without error even with default metadata
        json_str = output.model_dump_json()
        assert json_str is not None

        # Should deserialize without error
        restored = ModelReducerOutput[int].model_validate_json(json_str)
        assert restored.result == 42


class TestModelReducerOutputGenericTyping:
    """Test ModelReducerOutput generic type parameter behavior."""

    @pytest.mark.parametrize(
        ("type_param", "result", "expected_type"),
        [
            pytest.param(int, 42, int, id="int"),
            pytest.param(str, "completed", str, id="str"),
            pytest.param(dict, {"status": "success", "count": 10}, dict, id="dict"),
            pytest.param(list, [1, 2, 3, 4, 5], list, id="list"),
        ],
    )
    def test_type_parameter_preserves_type(self, type_param, result, expected_type):
        """Test that generic type parameter preserves result type.

        Validates that int, str, dict, and list type parameters maintain their types
        throughout the model lifecycle."""
        output = ModelReducerOutput[type_param](
            result=result,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )

        assert isinstance(output.result, expected_type)

    def test_type_parameter_preserves_custom_model_type(self):
        """Test that custom Pydantic model type parameter is preserved.

        Validates that custom Pydantic model types are maintained with full access
        to their fields, methods, and validation logic."""
        test_data = ModelTestData(value=100, label="test")

        output = ModelReducerOutput[ModelTestData](
            result=test_data,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.TRANSFORM,
            processing_time_ms=7.0,
            items_processed=1,
        )

        assert isinstance(output.result, ModelTestData)
        assert output.result.value == 100
        assert output.result.label == "test"

    def test_multiple_instances_different_result_types_independent(self):
        """Test that multiple instances with different result types are independent.

        Validates that multiple ModelReducerOutput instances with different generic
        types can coexist without interference, type pollution, or state leakage."""
        output_int = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )

        output_str = ModelReducerOutput[str](
            result="success",
            operation_id=uuid4(),
            reduction_type=EnumReductionType.ACCUMULATE,
            processing_time_ms=8.0,
            items_processed=3,
        )

        output_dict = ModelReducerOutput[dict](
            result={"key": "value"},
            operation_id=uuid4(),
            reduction_type=EnumReductionType.MERGE,
            processing_time_ms=15.0,
            items_processed=7,
        )

        # All should have correct types
        assert isinstance(output_int.result, int)
        assert isinstance(output_str.result, str)
        assert isinstance(output_dict.result, dict)

        # All should have different operation_ids
        assert output_int.operation_id != output_str.operation_id
        assert output_str.operation_id != output_dict.operation_id

    def test_generic_type_in_nested_structures(self):
        """Test generic type parameter with nested data structures.

        Validates that deeply nested data structures (dicts containing lists/dicts)
        maintain their integrity and accessibility through the generic type system."""
        nested_result = {
            "level1": {
                "level2": {
                    "values": [1, 2, 3],
                    "metadata": {"source": "test"},
                }
            }
        }

        output = ModelReducerOutput[dict](
            result=nested_result,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.AGGREGATE,
            processing_time_ms=20.0,
            items_processed=15,
        )

        assert isinstance(output.result, dict)
        assert output.result["level1"]["level2"]["values"] == [1, 2, 3]


class TestModelReducerOutputFrozenBehavior:
    """Test frozen behavior (immutability) of ModelReducerOutput."""

    @pytest.mark.parametrize(
        ("field_name", "new_value"),
        [
            pytest.param("result", 100, id="result"),
            pytest.param("operation_id", uuid4(), id="operation_id"),
            pytest.param(
                "reduction_type", EnumReductionType.ACCUMULATE, id="reduction_type"
            ),
            pytest.param("processing_time_ms", 20.0, id="processing_time_ms"),
            pytest.param("items_processed", 10, id="items_processed"),
            pytest.param("metadata", ModelReducerMetadata(source="new"), id="metadata"),
            pytest.param("intents", (), id="intents"),
        ],
    )
    def test_field_immutable(self, field_name, new_value):
        """Test that fields cannot be modified after creation.

        Validates that all fields are frozen and raise ValidationError on
        modification attempts."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )

        with pytest.raises(ValidationError) as exc_info:
            setattr(output, field_name, new_value)  # type: ignore[misc]

        assert "frozen" in str(exc_info.value).lower()

    def test_cannot_add_new_fields_after_creation(self):
        """Test that new fields cannot be added after creation.

        Validates that the frozen model prevents dynamic field addition, maintaining
        strict schema compliance and preventing accidental data corruption."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )

        with pytest.raises(ValidationError):
            output.new_field = "value"  # type: ignore[attr-defined]


class TestModelReducerOutputEdgeCases:
    """Test edge cases and boundary conditions for ModelReducerOutput."""

    def test_zero_processing_time(self):
        """Test edge case of zero processing time (instant processing).

        Validates that zero processing time is accepted for operations that
        complete instantaneously or synchronously without measurable overhead."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=0.0,
            items_processed=5,
        )

        assert output.processing_time_ms == 0.0

    def test_zero_items_processed(self):
        """Test edge case of zero items processed (no items).

        Validates that zero item counts are accepted for operations with
        empty input sets, filters that match nothing, or no-op reductions."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=5.0,
            items_processed=0,
        )

        assert output.items_processed == 0

    def test_large_processing_time(self):
        """Test edge case of very large processing time (millions of ms).

        Validates that the model can handle extreme processing time values
        without overflow, precision loss, or serialization issues."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=999999999.99,
            items_processed=5,
        )

        assert output.processing_time_ms == 999999999.99

    def test_large_items_processed(self):
        """Test edge case of very large items_processed count.

        Validates that the model can handle extreme item counts (billions+)
        without overflow or integer representation issues."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=999999999,
        )

        assert output.items_processed == 999999999

    def test_complex_result_structures(self):
        """Test edge case of complex nested result structures.

        Validates that deeply nested and complex result structures with multiple
        levels of nesting are preserved correctly throughout the model lifecycle."""
        complex_result = {
            "data": {
                "users": [
                    {"id": 1, "name": "Alice", "scores": [10, 20, 30]},
                    {"id": 2, "name": "Bob", "scores": [15, 25, 35]},
                ],
                "metadata": {
                    "total": 2,
                    "averages": {"Alice": 20.0, "Bob": 25.0},
                },
            }
        }

        output = ModelReducerOutput[dict](
            result=complex_result,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.AGGREGATE,
            processing_time_ms=50.0,
            items_processed=2,
        )

        assert output.result["data"]["users"][0]["name"] == "Alice"
        assert output.result["data"]["metadata"]["total"] == 2

    def test_none_values_for_optional_fields(self):
        """Test that optional metadata fields can be None.

        Validates that optional metadata fields (source, trace_id, correlation_id)
        can be explicitly set to None without causing validation errors."""
        metadata = ModelReducerMetadata(
            source=None,
            trace_id=None,
            correlation_id=None,
        )

        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
            metadata=metadata,
        )

        assert output.metadata.source is None
        assert output.metadata.trace_id is None

    def test_metadata_with_nested_structures(self):
        """Test metadata with all fields populated including complex tags.

        Validates that complex metadata with all optional fields set (trace IDs,
        window IDs, tags) is correctly stored and accessible through the reducer output.
        """
        window_id = uuid4()
        partition_id = uuid4()

        metadata = ModelReducerMetadata(
            source="api_gateway",
            trace_id="trace_abc123",
            span_id="span_xyz789",
            correlation_id="corr_def456",
            group_key="user_group_premium",
            partition_id=partition_id,
            window_id=window_id,
            tags=["production", "high_priority", "user_initiated"],
            trigger="user_action_completed",
        )

        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.AGGREGATE,
            processing_time_ms=15.0,
            items_processed=100,
            metadata=metadata,
        )

        assert output.metadata.source == "api_gateway"
        assert output.metadata.window_id == window_id
        assert len(output.metadata.tags) == 3
        assert "high_priority" in output.metadata.tags

    def test_multiple_intents(self):
        """Test output with multiple intents in tuple.

        Validates that the model correctly stores and preserves multiple intents
        in their specified order, maintaining intent chain integrity."""
        intent1 = ModelIntent(intent_type="log", target="service1")
        intent2 = ModelIntent(intent_type="emit", target="service2")
        intent3 = ModelIntent(intent_type="notify", target="service3")

        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
            intents=(intent1, intent2, intent3),
        )

        assert len(output.intents) == 3
        assert output.intents[0].target == "service1"
        assert output.intents[1].target == "service2"
        assert output.intents[2].target == "service3"

    def test_uuid_string_conversion_roundtrip(self):
        """Test UUID to string conversion and back in serialization.

        Validates that UUID objects are correctly converted to strings during
        JSON serialization and back to UUID objects during deserialization."""
        operation_id = uuid4()

        output = ModelReducerOutput[int](
            result=42,
            operation_id=operation_id,
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )

        # Serialize to JSON (UUID becomes string)
        json_str = output.model_dump_json()

        # Deserialize from JSON (string becomes UUID)
        restored = ModelReducerOutput[int].model_validate_json(json_str)

        assert isinstance(restored.operation_id, UUID)
        assert restored.operation_id == operation_id

    def test_all_reduction_types(self):
        """Test creating output with all valid reduction types.

        Validates comprehensive support for every reduction operation type defined
        in the EnumReductionType enumeration (FOLD, ACCUMULATE, MERGE, etc)."""
        for reduction_type in EnumReductionType:
            output = ModelReducerOutput[int](
                result=42,
                operation_id=uuid4(),
                reduction_type=reduction_type,
                processing_time_ms=10.0,
                items_processed=5,
            )
            assert output.reduction_type == reduction_type

    def test_all_streaming_modes(self):
        """Test creating output with all valid streaming modes.

        Validates that every streaming mode (BATCH, WINDOWED, REAL_TIME) can be
        configured and persisted in output metadata for different processing patterns.
        """
        for streaming_mode in EnumStreamingMode:
            output = ModelReducerOutput[int](
                result=42,
                operation_id=uuid4(),
                reduction_type=EnumReductionType.FOLD,
                processing_time_ms=10.0,
                items_processed=5,
                streaming_mode=streaming_mode,
            )
            assert output.streaming_mode == streaming_mode
