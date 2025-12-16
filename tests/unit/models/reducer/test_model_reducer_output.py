"""
Unit tests for ModelReducerOutput[T].

Tests all aspects of the reducer output model including:
- Model instantiation with generic type parameters
- Field validation and boundary conditions
- Frozen behavior (immutability)
- Serialization/deserialization
- Generic typing behavior
- Edge cases and boundary values
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
        """Test creating ModelReducerOutput with only required fields."""
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
        """Test creating ModelReducerOutput with all fields populated."""
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

    def test_generic_type_parameter_int(self):
        """Test ModelReducerOutput with int type parameter."""
        output = ModelReducerOutput[int](
            result=999,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=5.0,
            items_processed=10,
        )

        assert isinstance(output.result, int)
        assert output.result == 999

    def test_generic_type_parameter_str(self):
        """Test ModelReducerOutput with str type parameter."""
        output = ModelReducerOutput[str](
            result="aggregation_complete",
            operation_id=uuid4(),
            reduction_type=EnumReductionType.ACCUMULATE,
            processing_time_ms=8.2,
            items_processed=5,
        )

        assert isinstance(output.result, str)
        assert output.result == "aggregation_complete"

    def test_generic_type_parameter_dict(self):
        """Test ModelReducerOutput with dict type parameter."""
        result_dict = {"total": 500, "average": 50.0, "max": 100}

        output = ModelReducerOutput[dict](
            result=result_dict,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.AGGREGATE,
            processing_time_ms=15.3,
            items_processed=10,
        )

        assert isinstance(output.result, dict)
        assert output.result == result_dict
        assert output.result["total"] == 500

    def test_generic_type_parameter_list(self):
        """Test ModelReducerOutput with list type parameter."""
        result_list = [1, 2, 3, 5, 8, 13, 21]

        output = ModelReducerOutput[list](
            result=result_list,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FILTER,
            processing_time_ms=3.7,
            items_processed=20,
        )

        assert isinstance(output.result, list)
        assert output.result == result_list
        assert len(output.result) == 7

    def test_generic_type_parameter_custom_model(self):
        """Test ModelReducerOutput with custom Pydantic model type parameter."""
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

    def test_required_field_result_missing(self):
        """Test that result field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerOutput[int](
                operation_id=uuid4(),
                reduction_type=EnumReductionType.FOLD,
                processing_time_ms=10.0,
                items_processed=5,
            )

        error_msg = str(exc_info.value)
        assert "result" in error_msg
        assert "Field required" in error_msg

    def test_required_field_operation_id_missing(self):
        """Test that operation_id field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerOutput[int](
                result=42,
                reduction_type=EnumReductionType.FOLD,
                processing_time_ms=10.0,
                items_processed=5,
            )

        error_msg = str(exc_info.value)
        assert "operation_id" in error_msg
        assert "Field required" in error_msg

    def test_required_field_reduction_type_missing(self):
        """Test that reduction_type field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerOutput[int](
                result=42,
                operation_id=uuid4(),
                processing_time_ms=10.0,
                items_processed=5,
            )

        error_msg = str(exc_info.value)
        assert "reduction_type" in error_msg
        assert "Field required" in error_msg

    def test_required_field_processing_time_ms_missing(self):
        """Test that processing_time_ms field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerOutput[int](
                result=42,
                operation_id=uuid4(),
                reduction_type=EnumReductionType.FOLD,
                items_processed=5,
            )

        error_msg = str(exc_info.value)
        assert "processing_time_ms" in error_msg
        assert "Field required" in error_msg

    def test_required_field_items_processed_missing(self):
        """Test that items_processed field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerOutput[int](
                result=42,
                operation_id=uuid4(),
                reduction_type=EnumReductionType.FOLD,
                processing_time_ms=10.0,
            )

        error_msg = str(exc_info.value)
        assert "items_processed" in error_msg
        assert "Field required" in error_msg

    def test_result_type_validation(self):
        """Test that result field accepts correct type."""
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
        """Test that operation_id must be a valid UUID."""
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
            operation_id=uuid_str,  # type: ignore[misc]
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )
        assert isinstance(output2.operation_id, UUID)

    def test_reduction_type_validation(self):
        """Test that reduction_type must be a valid EnumReductionType."""
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
                reduction_type="invalid_type",  # type: ignore[misc]
                processing_time_ms=10.0,
                items_processed=5,
            )

        assert "reduction_type" in str(exc_info.value)

    def test_processing_time_ms_validation_negative(self):
        """Test that negative processing_time_ms is accepted (no constraint)."""
        # Note: The model does not enforce non-negative constraint
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=-1.0,
            items_processed=5,
        )

        assert output.processing_time_ms == -1.0

    def test_processing_time_ms_validation_zero(self):
        """Test that zero processing_time_ms is valid (instant processing)."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=0.0,
            items_processed=5,
        )

        assert output.processing_time_ms == 0.0

    def test_processing_time_ms_validation_positive(self):
        """Test that positive processing_time_ms is valid."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=42.5,
            items_processed=5,
        )

        assert output.processing_time_ms == 42.5

    def test_items_processed_validation_negative(self):
        """Test that negative items_processed is accepted (no constraint)."""
        # Note: The model does not enforce non-negative constraint
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=-1,
        )

        assert output.items_processed == -1

    def test_items_processed_validation_zero(self):
        """Test that zero items_processed is valid (no items processed)."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=5.0,
            items_processed=0,
        )

        assert output.items_processed == 0

    def test_items_processed_validation_positive(self):
        """Test that positive items_processed is valid."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=1000,
        )

        assert output.items_processed == 1000

    def test_invalid_field_types(self):
        """Test that invalid field types are rejected."""
        # Invalid result type (when model expects strict typing)
        # Note: Pydantic may coerce some types, so test truly incompatible types

        # Invalid operation_id (not UUID-compatible)
        with pytest.raises(ValidationError):
            ModelReducerOutput[int](
                result=42,
                operation_id="not-a-uuid",  # type: ignore[misc]
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
                processing_time_ms="not-a-number",  # type: ignore[misc]
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
                items_processed="not-a-number",  # type: ignore[misc]
            )

    def test_extra_fields_rejected(self):
        """Test that extra fields are rejected (extra='forbid')."""
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
        """Test serializing output to dictionary."""
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
        """Test serializing output to JSON string."""
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
        """Test deserializing output from dictionary."""
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
        """Test deserializing output from JSON string."""
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

    def test_roundtrip_serialization_with_int_result(self):
        """Test roundtrip serialization with int result."""
        original = ModelReducerOutput[int](
            result=999,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=15.7,
            items_processed=200,
        )

        # Serialize and deserialize
        data = original.model_dump()
        restored = ModelReducerOutput[int].model_validate(data)

        assert restored.result == original.result
        assert restored.operation_id == original.operation_id
        assert restored.reduction_type == original.reduction_type
        assert restored.processing_time_ms == original.processing_time_ms
        assert restored.items_processed == original.items_processed

    def test_roundtrip_serialization_with_dict_result(self):
        """Test roundtrip serialization with dict result."""
        result_dict = {"total": 500, "count": 10, "average": 50.0}

        original = ModelReducerOutput[dict](
            result=result_dict,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.AGGREGATE,
            processing_time_ms=25.2,
            items_processed=300,
        )

        # Serialize and deserialize
        json_str = original.model_dump_json()
        restored = ModelReducerOutput[dict].model_validate_json(json_str)

        assert restored.result == original.result
        assert restored.operation_id == original.operation_id
        assert restored.reduction_type == original.reduction_type

    def test_roundtrip_serialization_with_list_result(self):
        """Test roundtrip serialization with list result."""
        result_list = [1, 2, 3, 5, 8, 13]

        original = ModelReducerOutput[list](
            result=result_list,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FILTER,
            processing_time_ms=5.1,
            items_processed=20,
        )

        # Serialize and deserialize
        data = original.model_dump()
        restored = ModelReducerOutput[list].model_validate(data)

        assert restored.result == original.result
        assert len(restored.result) == len(original.result)

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
        """Test that roundtrip serialization preserves all fields."""
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
        """Test that serialization correctly handles optional metadata fields."""
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

    def test_type_parameter_preserves_int_type(self):
        """Test that generic type parameter preserves int type."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )

        assert isinstance(output.result, int)
        assert output.result == 42

    def test_type_parameter_preserves_str_type(self):
        """Test that generic type parameter preserves str type."""
        output = ModelReducerOutput[str](
            result="completed",
            operation_id=uuid4(),
            reduction_type=EnumReductionType.ACCUMULATE,
            processing_time_ms=8.0,
            items_processed=3,
        )

        assert isinstance(output.result, str)
        assert output.result == "completed"

    def test_type_parameter_preserves_dict_type(self):
        """Test that generic type parameter preserves dict type."""
        result_dict = {"status": "success", "count": 10}

        output = ModelReducerOutput[dict](
            result=result_dict,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.AGGREGATE,
            processing_time_ms=12.0,
            items_processed=10,
        )

        assert isinstance(output.result, dict)
        assert output.result["status"] == "success"

    def test_type_parameter_preserves_list_type(self):
        """Test that generic type parameter preserves list type."""
        result_list = [1, 2, 3, 4, 5]

        output = ModelReducerOutput[list](
            result=result_list,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FILTER,
            processing_time_ms=5.0,
            items_processed=10,
        )

        assert isinstance(output.result, list)
        assert len(output.result) == 5

    def test_type_parameter_preserves_custom_model_type(self):
        """Test that generic type parameter preserves custom model type."""
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
        """Test that multiple instances with different result types are independent."""
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
        """Test generic type parameter with nested data structures."""
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

    def test_result_field_immutable(self):
        """Test that result field cannot be modified after creation."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )

        with pytest.raises(ValidationError) as exc_info:
            output.result = 100  # type: ignore[misc]

        assert "frozen" in str(exc_info.value).lower()

    def test_operation_id_field_immutable(self):
        """Test that operation_id field cannot be modified after creation."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )

        with pytest.raises(ValidationError) as exc_info:
            output.operation_id = uuid4()  # type: ignore[misc]

        assert "frozen" in str(exc_info.value).lower()

    def test_reduction_type_field_immutable(self):
        """Test that reduction_type field cannot be modified after creation."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )

        with pytest.raises(ValidationError) as exc_info:
            output.reduction_type = EnumReductionType.ACCUMULATE  # type: ignore[misc]

        assert "frozen" in str(exc_info.value).lower()

    def test_processing_time_ms_field_immutable(self):
        """Test that processing_time_ms field cannot be modified after creation."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )

        with pytest.raises(ValidationError) as exc_info:
            output.processing_time_ms = 20.0  # type: ignore[misc]

        assert "frozen" in str(exc_info.value).lower()

    def test_items_processed_field_immutable(self):
        """Test that items_processed field cannot be modified after creation."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )

        with pytest.raises(ValidationError) as exc_info:
            output.items_processed = 10  # type: ignore[misc]

        assert "frozen" in str(exc_info.value).lower()

    def test_metadata_field_immutable(self):
        """Test that metadata field cannot be modified after creation."""
        metadata = ModelReducerMetadata(source="test")

        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
            metadata=metadata,
        )

        with pytest.raises(ValidationError) as exc_info:
            output.metadata = ModelReducerMetadata(source="new")  # type: ignore[misc]

        assert "frozen" in str(exc_info.value).lower()

    def test_intents_field_immutable(self):
        """Test that intents field cannot be modified after creation."""
        intent = ModelIntent(intent_type="log", target="service")

        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
            intents=(intent,),
        )

        with pytest.raises(ValidationError) as exc_info:
            output.intents = ()  # type: ignore[misc]

        assert "frozen" in str(exc_info.value).lower()

    def test_cannot_add_new_fields_after_creation(self):
        """Test that new fields cannot be added after creation."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
        )

        with pytest.raises((ValidationError, AttributeError)):
            output.new_field = "value"  # type: ignore[misc]


class TestModelReducerOutputEdgeCases:
    """Test edge cases and boundary conditions for ModelReducerOutput."""

    def test_zero_processing_time(self):
        """Test edge case of zero processing time (instant processing)."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=0.0,
            items_processed=5,
        )

        assert output.processing_time_ms == 0.0

    def test_zero_items_processed(self):
        """Test edge case of zero items processed (no items)."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=5.0,
            items_processed=0,
        )

        assert output.items_processed == 0

    def test_large_processing_time(self):
        """Test edge case of very large processing time (millions of ms)."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=999999999.99,
            items_processed=5,
        )

        assert output.processing_time_ms == 999999999.99

    def test_large_items_processed(self):
        """Test edge case of very large items_processed count."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=999999999,
        )

        assert output.items_processed == 999999999

    def test_complex_result_structures(self):
        """Test edge case of complex nested result structures."""
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
        """Test that optional metadata fields can be None."""
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
        """Test metadata with all fields populated including complex tags."""
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
        """Test output with multiple intents in tuple."""
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
        """Test UUID to string conversion and back in serialization."""
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

    def test_boundary_values_processing_time_ms(self):
        """Test boundary values for processing_time_ms field."""
        # Test zero (minimum valid value)
        output_min = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=0.0,
            items_processed=5,
        )
        assert output_min.processing_time_ms == 0.0

        # Test very large value
        output_max = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=float(10**9),  # 1 billion milliseconds
            items_processed=5,
        )
        assert output_max.processing_time_ms == float(10**9)

    def test_boundary_values_items_processed(self):
        """Test boundary values for items_processed field."""
        # Test zero (minimum valid value)
        output_min = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=0,
        )
        assert output_min.items_processed == 0

        # Test very large value
        output_max = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=10**9,  # 1 billion items
        )
        assert output_max.items_processed == 10**9

    def test_all_reduction_types(self):
        """Test creating output with all valid reduction types."""
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
        """Test creating output with all valid streaming modes."""
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
