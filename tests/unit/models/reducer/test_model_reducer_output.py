"""Unit tests for ModelReducerOutput[T] - REFACTORED with parametrization.

Tests all aspects of the reducer output model including:
- Model instantiation with generic type parameters
- Field validation and boundary conditions
- Frozen behavior (immutability)
- Serialization/deserialization
- Generic typing behavior
- Edge cases and boundary values
- Thread safety and concurrent access
- UUID format preservation
- Async-safe operations
- Performance benchmarks

Architecture Context:
    ModelReducerOutput[T] is the output model for REDUCER nodes, containing
    the result of FSM-driven state management and data aggregation operations.

Related Models:
    - ModelReducerInput[T] - Input contract for REDUCER nodes
    - ModelIntent - Intent pattern for side effects
    - ModelReducerMetadata - Metadata container for operations

Notes:
    - Parametrized tests reduce duplication while maintaining comprehensive coverage
    - Thread-safe for pytest-xdist parallel execution
"""

import concurrent.futures
import threading
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_reducer_types import EnumReductionType, EnumStreamingMode
from omnibase_core.models.common.model_reducer_metadata import ModelReducerMetadata
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.reducer.model_intent import ModelIntent
from omnibase_core.models.reducer.model_reducer_output import ModelReducerOutput
from omnibase_core.models.reducer.payloads import ModelPayloadLogEvent

pytestmark = pytest.mark.unit


# Test helper model for generic type testing
class ModelTestData(BaseModel):
    """Test model for generic type parameter testing."""

    value: int
    label: str


@pytest.mark.unit
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
            intent_type="log_event",
            target="metrics_service",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="reduction_time: 42.5",
            ),
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
        output = ModelReducerOutput[type_param](  # type: ignore[valid-type]  # Runtime type parameter in parametrized test
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


@pytest.mark.unit
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
            operation_id=uuid_str,  # type: ignore[arg-type]  # Testing string UUID coercion
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
                reduction_type="invalid_type",  # type: ignore[arg-type]  # Testing invalid enum value
                processing_time_ms=10.0,
                items_processed=5,
            )

        assert "reduction_type" in str(exc_info.value)

    @pytest.mark.parametrize(
        ("value", "description"),
        [
            pytest.param(-1.0, "sentinel", id="sentinel_negative_one"),
            pytest.param(0.0, "zero", id="zero"),
            pytest.param(42.5, "positive", id="positive"),
        ],
    )
    def test_processing_time_ms_validation(self, value, description):
        """Test processing_time_ms validation with valid values.

        The model enforces sentinel pattern for graceful degradation:
        - -1.0: SENTINEL VALUE - Timing measurement failed or unavailable.
                This allows the reducer to complete successfully even when
                timing cannot be measured, preventing cascading failures.
        - 0.0: Valid measurement - Operation completed instantaneously
        - Positive values: Valid measurements - Actual processing time in milliseconds

        This pattern follows the C/POSIX convention of -1 for "not found" or
        "unavailable", enabling operations to succeed even when non-critical
        metrics cannot be captured."""
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
            pytest.param(-1, "sentinel", id="sentinel_negative_one"),
            pytest.param(0, "zero", id="zero"),
            pytest.param(1000, "positive", id="positive"),
        ],
    )
    def test_items_processed_validation(self, value, description):
        """Test items_processed validation with valid values.

        The model enforces sentinel pattern for graceful degradation:
        - -1: SENTINEL VALUE - Count unavailable due to error or inability to measure.
              Allows reducer to complete successfully even when item count cannot
              be determined, preventing cascading failures.
        - 0: Valid count - No items were processed (empty input, filtered out, etc.)
        - Positive values: Valid counts - Actual number of items processed

        This pattern follows the C/POSIX convention of -1 for "not found" or
        "unavailable", enabling operations to succeed even when non-critical
        metrics cannot be captured."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=value,
        )

        assert output.items_processed == value

    @pytest.mark.parametrize(
        ("invalid_value", "description"),
        [
            pytest.param(-2.5, "float_negative", id="float_negative"),
            pytest.param(-10.0, "large_negative", id="large_negative"),
        ],
    )
    def test_processing_time_ms_invalid_sentinel_rejected(
        self, invalid_value, description
    ):
        """Test that processing_time_ms rejects negative values other than -1.0.

        Validates that the sentinel pattern enforcement correctly rejects invalid
        negative values while allowing only -1.0 as the error indicator."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelReducerOutput[int](
                result=42,
                operation_id=uuid4(),
                reduction_type=EnumReductionType.FOLD,
                processing_time_ms=invalid_value,
                items_processed=5,
            )

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "processing_time_ms" in error.message
        assert "sentinel" in error.message.lower() or "-1.0" in error.message

    @pytest.mark.parametrize(
        ("invalid_value", "description"),
        [
            pytest.param(-2, "small_negative", id="small_negative"),
            pytest.param(-100, "large_negative", id="large_negative"),
        ],
    )
    def test_items_processed_invalid_sentinel_rejected(
        self, invalid_value, description
    ):
        """Test that items_processed rejects negative values other than -1.

        Validates that the sentinel pattern enforcement correctly rejects invalid
        negative values while allowing only -1 as the error indicator."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelReducerOutput[int](
                result=42,
                operation_id=uuid4(),
                reduction_type=EnumReductionType.FOLD,
                processing_time_ms=10.0,
                items_processed=invalid_value,
            )

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "items_processed" in error.message
        assert "sentinel" in error.message.lower() or "-1" in error.message

    @pytest.mark.parametrize(
        ("special_value", "value_name"),
        [
            pytest.param(float("nan"), "NaN", id="nan"),
            pytest.param(float("inf"), "positive_infinity", id="positive_inf"),
            pytest.param(float("-inf"), "negative_infinity", id="negative_inf"),
        ],
    )
    def test_processing_time_ms_special_float_values_rejected(
        self, special_value, value_name
    ):
        """Test that processing_time_ms rejects special float values (NaN, Inf, -Inf).

        Validates that special IEEE 754 float values are rejected to prevent
        undefined behavior in calculations and comparisons."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelReducerOutput[int](
                result=42,
                operation_id=uuid4(),
                reduction_type=EnumReductionType.FOLD,
                processing_time_ms=special_value,
                items_processed=5,
            )

        error = exc_info.value
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "processing_time_ms" in error.message
        # Check for specific error message about the special value type
        error_lower = error.message.lower()
        assert "nan" in error_lower or "infinity" in error_lower or "inf" in error_lower

    @pytest.mark.parametrize(
        ("invalid_field", "invalid_value", "field_name"),
        [
            pytest.param(
                "operation_id",
                "not-a-uuid",
                "operation_id",
                id="invalid_uuid_string",
            ),
            pytest.param(
                "processing_time_ms",
                "not-a-number",
                "processing_time_ms",
                id="invalid_processing_time_type",
            ),
            pytest.param(
                "items_processed",
                "not-a-number",
                "items_processed",
                id="invalid_items_processed_type",
            ),
        ],
    )
    def test_invalid_field_types(self, invalid_field, invalid_value, field_name):
        """Test that invalid field types are rejected.

        Validates comprehensive type checking across all fields, ensuring that
        incorrect types are rejected with clear validation error messages."""
        base_params = {
            "result": 42,
            "operation_id": uuid4(),
            "reduction_type": EnumReductionType.FOLD,
            "processing_time_ms": 10.0,
            "items_processed": 5,
        }
        base_params[invalid_field] = invalid_value  # type: ignore[assignment]  # Testing invalid type

        with pytest.raises(ValidationError):
            ModelReducerOutput[int](**base_params)

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
                extra_field="should_fail",  # type: ignore[call-arg]  # Testing extra field rejection
            )

        error_msg = str(exc_info.value)
        assert "extra_field" in error_msg
        assert "Extra inputs are not permitted" in error_msg


@pytest.mark.unit
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
        original = ModelReducerOutput[type_param](  # type: ignore[valid-type]  # Runtime type parameter in parametrized test
            result=result,
            operation_id=uuid4(),
            reduction_type=reduction_type,
            processing_time_ms=10.0,
            items_processed=5,
        )

        # Serialize and deserialize
        data = original.model_dump()
        restored = ModelReducerOutput[type_param].model_validate(data)  # type: ignore[valid-type]  # Runtime type parameter in parametrized test

        assert restored.result == original.result  # type: ignore[operator]  # Runtime type comparison in parametrized test
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
            intent_type="log_event",
            target="service",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="test value",
            ),
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

        # Copy and verify (Protocol-based payloads don't support dict deserialization)
        restored = original.model_copy()

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


@pytest.mark.unit
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
        output = ModelReducerOutput[type_param](  # type: ignore[valid-type]  # Runtime type parameter in parametrized test
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


@pytest.mark.unit
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
            setattr(output, field_name, new_value)

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
            output.new_field = "value"  # type: ignore[attr-defined]  # Testing attribute addition prevention


@pytest.mark.unit
class TestModelReducerOutputEdgeCases:
    """Test edge cases and boundary conditions for ModelReducerOutput."""

    @pytest.mark.parametrize(
        ("processing_time_ms", "items_processed", "description"),
        [
            pytest.param(0.0, 5, "zero_processing_time", id="zero_processing_time"),
            pytest.param(5.0, 0, "zero_items_processed", id="zero_items_processed"),
            pytest.param(
                999999999.99, 5, "large_processing_time", id="large_processing_time"
            ),
            pytest.param(
                10.0, 999999999, "large_items_processed", id="large_items_processed"
            ),
            pytest.param(
                -1.0, 100, "sentinel_processing_time", id="sentinel_processing_time"
            ),
            pytest.param(
                10.0, -1, "sentinel_items_processed", id="sentinel_items_processed"
            ),
            pytest.param(-1.0, -1, "both_sentinels", id="both_sentinels"),
            pytest.param(0.001, 1, "minimal_positive_values", id="minimal_positive"),
            pytest.param(999999.999, 999999, "near_max_values", id="near_max_values"),
        ],
    )
    def test_boundary_value_combinations(
        self, processing_time_ms, items_processed, description
    ):
        """Test various boundary value combinations for numeric fields.

        Validates that the model correctly handles:
        - Zero values (instant processing, empty sets)
        - Sentinel values (-1.0, -1 for unavailable/error states)
        - Extreme values (large processing times, high item counts)
        - Minimal non-zero values
        - Combined edge cases (both sentinels simultaneously)

        These test cases ensure robust handling of boundary conditions
        without overflow, precision loss, or validation errors."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=processing_time_ms,
            items_processed=items_processed,
        )

        assert output.processing_time_ms == processing_time_ms
        assert output.items_processed == items_processed

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
        intent1 = ModelIntent(
            intent_type="log_event",
            target="service1",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )
        intent2 = ModelIntent(
            intent_type="emit",
            target="service2",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )
        intent3 = ModelIntent(
            intent_type="notify",
            target="service3",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )

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


@pytest.mark.unit
class TestModelReducerOutputThreadSafety:
    """Test thread safety and concurrent access patterns."""

    def test_concurrent_read_access(self):
        """Test that multiple threads can safely read the same output instance.

        Validates thread-safe read access due to frozen (immutable) model design."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=100,
        )

        results = []

        def read_output():
            """Read output fields from multiple threads."""
            for _ in range(100):
                results.append(
                    (
                        output.result,
                        output.operation_id,
                        output.processing_time_ms,
                        output.items_processed,
                    )
                )

        threads = [threading.Thread(target=read_output) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All reads should return consistent values
        assert len(results) == 1000
        assert all(r[0] == 42 for r in results)
        assert all(r[2] == 10.0 for r in results)
        assert all(r[3] == 100 for r in results)

    def test_concurrent_serialization(self):
        """Test concurrent serialization from multiple threads.

        Validates that multiple threads can safely serialize the same output
        instance without race conditions or data corruption."""
        output = ModelReducerOutput[dict](
            result={"status": "success", "count": 42},
            operation_id=uuid4(),
            reduction_type=EnumReductionType.AGGREGATE,
            processing_time_ms=25.5,
            items_processed=100,
        )

        json_results = []

        def serialize_output():
            """Serialize output from multiple threads."""
            for _ in range(50):
                json_str = output.model_dump_json()
                json_results.append(json_str)

        threads = [threading.Thread(target=serialize_output) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All serializations should be valid and consistent
        assert len(json_results) == 250
        assert all(
            '"status":"success"' in j or '"status": "success"' in j
            for j in json_results
        )
        assert all('"count":42' in j or '"count": 42' in j for j in json_results)

    def test_concurrent_metadata_access(self):
        """Test concurrent access to nested metadata from multiple threads.

        Validates that nested ModelReducerMetadata can be safely accessed
        concurrently without race conditions."""
        window_id = uuid4()
        metadata = ModelReducerMetadata(
            source="api_gateway",
            trace_id="trace123",
            correlation_id="corr456",
            window_id=window_id,
            tags=["production", "high_priority"],
        )

        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.AGGREGATE,
            processing_time_ms=15.0,
            items_processed=100,
            metadata=metadata,
        )

        metadata_results = []

        def read_metadata():
            """Read metadata fields from multiple threads."""
            for _ in range(100):
                metadata_results.append(
                    (
                        output.metadata.source,
                        output.metadata.trace_id,
                        output.metadata.correlation_id,
                        output.metadata.window_id,
                        len(output.metadata.tags),
                    )
                )

        threads = [threading.Thread(target=read_metadata) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All reads should return consistent values
        assert len(metadata_results) == 1000
        assert all(r[0] == "api_gateway" for r in metadata_results)
        assert all(r[1] == "trace123" for r in metadata_results)
        assert all(r[2] == "corr456" for r in metadata_results)
        assert all(r[3] == window_id for r in metadata_results)
        assert all(r[4] == 2 for r in metadata_results)

    def test_concurrent_intents_access(self):
        """Test concurrent access to intents tuple from multiple threads.

        Validates that the intents tuple can be safely accessed and iterated
        from multiple threads without race conditions."""
        intent1 = ModelIntent(
            intent_type="log_event",
            target="service1",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )
        intent2 = ModelIntent(
            intent_type="emit",
            target="service2",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )

        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=5,
            intents=(intent1, intent2),
        )

        intents_results = []

        def read_intents():
            """Read intents from multiple threads."""
            for _ in range(100):
                intents_results.append(
                    (
                        len(output.intents),
                        output.intents[0].target,
                        output.intents[1].target,
                    )
                )

        threads = [threading.Thread(target=read_intents) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All reads should return consistent values
        assert len(intents_results) == 1000
        assert all(r[0] == 2 for r in intents_results)
        assert all(r[1] == "service1" for r in intents_results)
        assert all(r[2] == "service2" for r in intents_results)

    def test_concurrent_model_dump_access(self):
        """Test concurrent model_dump operations from multiple threads.

        Validates that model_dump() can be called safely from multiple threads
        without race conditions or data corruption."""
        output = ModelReducerOutput[dict](
            result={"total": 100, "average": 50.0},
            operation_id=uuid4(),
            reduction_type=EnumReductionType.AGGREGATE,
            processing_time_ms=20.0,
            items_processed=200,
        )

        dump_results = []

        def dump_model():
            """Dump model from multiple threads."""
            for _ in range(50):
                data = output.model_dump()
                dump_results.append(data)

        threads = [threading.Thread(target=dump_model) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All dumps should be valid and consistent
        assert len(dump_results) == 250
        assert all(d["result"]["total"] == 100 for d in dump_results)
        assert all(d["result"]["average"] == 50.0 for d in dump_results)
        assert all(d["items_processed"] == 200 for d in dump_results)

    def test_concurrent_complex_nested_access(self):
        """Test concurrent access to complex nested result structures.

        Validates that deeply nested result data can be safely accessed from
        multiple threads without race conditions."""
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

        nested_results = []

        def read_nested():
            """Read deeply nested fields from multiple threads."""
            for _ in range(100):
                nested_results.append(
                    (
                        output.result["data"]["users"][0]["name"],
                        output.result["data"]["metadata"]["total"],
                        output.result["data"]["metadata"]["averages"]["Alice"],
                    )
                )

        threads = [threading.Thread(target=read_nested) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All reads should return consistent values
        assert len(nested_results) == 1000
        assert all(r[0] == "Alice" for r in nested_results)
        assert all(r[1] == 2 for r in nested_results)
        assert all(r[2] == 20.0 for r in nested_results)

    def test_no_race_conditions_on_frozen_fields(self):
        """Test that frozen=True prevents race conditions from modifications.

        Validates that any attempt to modify frozen fields from multiple threads
        consistently raises ValidationError without race conditions."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=100,
        )

        errors = []

        def attempt_modification():
            """Attempt to modify frozen fields from multiple threads."""
            for _ in range(50):
                try:
                    output.result = 999  # type: ignore[misc]  # Testing frozen field modification
                except ValidationError as e:
                    errors.append(e)

        threads = [threading.Thread(target=attempt_modification) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All modification attempts should fail with ValidationError
        assert len(errors) == 250
        assert all("frozen" in str(e).lower() for e in errors)

    def test_concurrent_access_with_thread_pool_executor(self):
        """Test concurrent access using ThreadPoolExecutor for realistic workload.

        Validates thread safety under real-world concurrent execution patterns
        using thread pool executor."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=100,
        )

        def read_and_serialize(iteration: int) -> tuple[int, str, float]:
            """Read fields and serialize in a single operation."""
            result = output.result
            json_str = output.model_dump_json()
            processing_time = output.processing_time_ms
            return (result, json_str, processing_time)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read_and_serialize, i) for i in range(100)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All operations should return consistent values
        assert len(results) == 100
        assert all(r[0] == 42 for r in results)
        assert all('"result":42' in r[1] or '"result": 42' in r[1] for r in results)
        assert all(r[2] == 10.0 for r in results)


@pytest.mark.unit
class TestModelReducerOutputImmutability:
    """Test immutability guarantees of ModelReducerOutput."""

    def test_frozen_prevents_result_modification(self):
        """Test that frozen=True prevents result modification.

        Validates that the result field cannot be modified after creation,
        ensuring immutability of the primary output value."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=100,
        )

        with pytest.raises(ValidationError) as exc_info:
            output.result = 999  # type: ignore[misc]  # Testing frozen field modification

        assert "frozen" in str(exc_info.value).lower()

    def test_frozen_prevents_operation_id_modification(self):
        """Test that operation_id cannot be modified after creation.

        Validates immutability of the operation correlation ID."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=100,
        )

        with pytest.raises(ValidationError) as exc_info:
            output.operation_id = uuid4()  # type: ignore[misc]  # Testing frozen field modification

        assert "frozen" in str(exc_info.value).lower()

    def test_frozen_prevents_reduction_type_modification(self):
        """Test that reduction_type cannot be modified after creation.

        Validates immutability of the reduction operation type."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=100,
        )

        with pytest.raises(ValidationError) as exc_info:
            output.reduction_type = EnumReductionType.ACCUMULATE  # type: ignore[misc]  # Testing frozen field modification

        assert "frozen" in str(exc_info.value).lower()

    def test_frozen_prevents_processing_time_ms_modification(self):
        """Test that processing_time_ms cannot be modified after creation.

        Validates immutability of the processing time metric."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=100,
        )

        with pytest.raises(ValidationError) as exc_info:
            output.processing_time_ms = 20.0  # type: ignore[misc]  # Testing frozen field modification

        assert "frozen" in str(exc_info.value).lower()

    def test_frozen_prevents_items_processed_modification(self):
        """Test that items_processed cannot be modified after creation.

        Validates immutability of the items count metric."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=100,
        )

        with pytest.raises(ValidationError) as exc_info:
            output.items_processed = 200  # type: ignore[misc]  # Testing frozen field modification

        assert "frozen" in str(exc_info.value).lower()

    def test_frozen_prevents_metadata_replacement(self):
        """Test that metadata cannot be replaced after creation.

        Validates that the metadata object reference is frozen."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=100,
        )

        new_metadata = ModelReducerMetadata(source="new_source")

        with pytest.raises(ValidationError) as exc_info:
            output.metadata = new_metadata  # type: ignore[misc]  # Testing frozen field modification

        assert "frozen" in str(exc_info.value).lower()

    def test_frozen_prevents_intents_replacement(self):
        """Test that intents tuple cannot be replaced after creation.

        Validates that the intents tuple reference is frozen."""
        intent = ModelIntent(
            intent_type="log_event",
            target="service",
            payload=ModelPayloadLogEvent(level="INFO", message="Test"),
        )
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=100,
            intents=(intent,),
        )

        new_intent = ModelIntent(
            intent_type="log_event",
            target="other_service",
            payload=ModelPayloadLogEvent(level="INFO", message="New"),
        )

        with pytest.raises(ValidationError) as exc_info:
            output.intents = (new_intent,)  # type: ignore[misc]  # Testing frozen field modification

        assert "frozen" in str(exc_info.value).lower()

    def test_frozen_prevents_timestamp_modification(self):
        """Test that timestamp cannot be modified after creation.

        Validates immutability of the creation timestamp."""
        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=100,
        )

        with pytest.raises(ValidationError) as exc_info:
            output.timestamp = datetime.now()  # type: ignore[misc]  # Testing frozen field modification

        assert "frozen" in str(exc_info.value).lower()

    def test_intents_tuple_immutability(self):
        """Test that intents tuple is immutable.

        Validates that the tuple structure prevents modification attempts."""
        intent1 = ModelIntent(
            intent_type="log_event",
            target="service1",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )
        intent2 = ModelIntent(
            intent_type="emit",
            target="service2",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )

        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=100,
            intents=(intent1, intent2),
        )

        # Tuples are immutable - assignment to index should fail
        with pytest.raises(TypeError):
            output.intents[0] = ModelIntent(  # type: ignore[index]  # Testing tuple immutability
                intent_type="log_event",
                target="new",
                payload=ModelPayloadLogEvent(level="INFO", message="new"),
            )

    def test_intent_objects_frozen_after_creation(self):
        """Test that ModelIntent objects in intents tuple are frozen.

        Validates deep immutability for intent objects."""
        intent = ModelIntent(
            intent_type="log_event",
            target="service",
            payload=ModelPayloadLogEvent(
                level="INFO",
                message="Test message",
            ),
        )

        output = ModelReducerOutput[int](
            result=42,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.FOLD,
            processing_time_ms=10.0,
            items_processed=100,
            intents=(intent,),
        )

        # Intent objects should be frozen
        with pytest.raises(ValidationError) as exc_info:
            output.intents[0].target = "new_target"  # type: ignore[misc]  # Testing nested frozen field modification

        assert "frozen" in str(exc_info.value).lower()

    def test_immutability_with_complex_nested_result(self):
        """Test immutability guarantees for complex nested result structures.

        Validates that while the model is frozen, mutable result content
        (dicts, lists) is NOT deeply frozen by Pydantic. This is expected
        behavior - frozen applies to model fields, not their contents."""
        nested_result = {"data": {"values": [1, 2, 3], "metadata": {"source": "test"}}}

        output = ModelReducerOutput[dict](
            result=nested_result,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.AGGREGATE,
            processing_time_ms=20.0,
            items_processed=15,
        )

        # Cannot replace result field (frozen)
        with pytest.raises(ValidationError):
            output.result = {}  # type: ignore[misc]  # Testing frozen field modification

        # However, result contents CAN be modified (not frozen by Pydantic)
        # This is expected behavior - users must be aware that frozen applies
        # to model fields, not the contents of those fields
        output.result["data"]["values"].append(4)
        assert output.result["data"]["values"] == [1, 2, 3, 4]
