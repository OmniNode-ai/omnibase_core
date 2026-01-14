"""Tests for ModelInvariantViolationDetail model."""

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumInvariantType, EnumSeverity
from omnibase_core.enums.enum_comparison_type import EnumComparisonType
from omnibase_core.models.invariant import ModelInvariantViolationDetail
from omnibase_core.models.invariant.model_field_value_config import (
    ModelFieldValueConfig,
)
from omnibase_core.models.invariant.model_latency_config import ModelLatencyConfig
from omnibase_core.models.invariant.model_schema_invariant_config import (
    ModelSchemaInvariantConfig,
)

# Test UUIDs for consistent testing
TEST_UUID_1 = uuid.UUID("12345678-1234-5678-1234-567812345678")
TEST_UUID_2 = uuid.UUID("87654321-4321-8765-4321-876543218765")
TEST_UUID_3 = uuid.UUID("11111111-2222-3333-4444-555555555555")
TEST_UUID_4 = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
TEST_UUID_5 = uuid.UUID("99999999-8888-7777-6666-555544443333")


@pytest.mark.unit
class TestModelInvariantViolationDetailCreation:
    """Test ModelInvariantViolationDetail creation and validation."""

    def test_detail_creation_with_required_fields(self) -> None:
        """Detail can be created with all required fields."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_1,
            invariant_name="Confidence score minimum",
            invariant_type=EnumInvariantType.FIELD_VALUE,
            severity=EnumSeverity.CRITICAL,
            message="Confidence score 0.65 is below minimum 0.8",
            explanation="The model's confidence score does not meet the threshold.",
            comparison_type=EnumComparisonType.RANGE,
        )
        assert detail.invariant_id == TEST_UUID_1
        assert detail.invariant_name == "Confidence score minimum"
        assert detail.severity == EnumSeverity.CRITICAL

    def test_detail_with_optional_fields(self) -> None:
        """Detail accepts all optional fields."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_2,
            invariant_name="Schema validation",
            invariant_type=EnumInvariantType.SCHEMA,
            severity=EnumSeverity.WARNING,
            field_path="response.choices.0.message.content",
            actual_value=None,
            expected_value="string",
            message="Field 'content' is null but string required",
            explanation="The response schema requires a non-null string.",
            comparison_type=EnumComparisonType.SCHEMA,
            operator="==",
            suggestion="Check if the model finished generating.",
            related_fields=["response.model", "response.finish_reason"],
        )
        assert detail.field_path == "response.choices.0.message.content"
        assert detail.suggestion is not None
        assert len(detail.related_fields) == 2

    def test_detail_is_frozen(self) -> None:
        """Detail is immutable after creation."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_1,
            invariant_name="Test",
            invariant_type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.WARNING,
            message="Test message",
            explanation="Test explanation",
            comparison_type=EnumComparisonType.RANGE,
        )
        with pytest.raises(ValidationError):
            detail.message = "New message"

    def test_detail_auto_generates_evaluated_at(self) -> None:
        """evaluated_at defaults to current time."""
        before = datetime.now(UTC)
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_1,
            invariant_name="Test",
            invariant_type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.WARNING,
            message="Test",
            explanation="Test",
            comparison_type=EnumComparisonType.RANGE,
        )
        after = datetime.now(UTC)
        assert before <= detail.evaluated_at <= after

    def test_creation_with_all_fields(self) -> None:
        """Model creates successfully with all optional fields populated."""
        fixed_time = datetime(2024, 6, 15, 12, 30, 45, tzinfo=UTC)
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_1,
            invariant_name="Complete test invariant",
            invariant_type=EnumInvariantType.THRESHOLD,
            severity=EnumSeverity.CRITICAL,
            field_path="metrics.accuracy",
            actual_value=0.72,
            expected_value=0.90,
            message="Accuracy below required threshold",
            explanation="The model accuracy does not meet requirements.",
            comparison_type=EnumComparisonType.RANGE,
            operator=">=",
            evaluated_at=fixed_time,
            config_snapshot=None,
            suggestion="Retrain the model with more diverse data.",
            related_fields=["metrics.precision", "metrics.recall", "metrics.f1"],
        )
        assert detail.invariant_id == TEST_UUID_1
        assert detail.invariant_name == "Complete test invariant"
        assert detail.invariant_type == EnumInvariantType.THRESHOLD
        assert detail.severity == EnumSeverity.CRITICAL
        assert detail.field_path == "metrics.accuracy"
        assert detail.actual_value == 0.72
        assert detail.expected_value == 0.90
        assert detail.message == "Accuracy below required threshold"
        assert detail.explanation == "The model accuracy does not meet requirements."
        assert detail.comparison_type == EnumComparisonType.RANGE
        assert detail.operator == ">="
        assert detail.evaluated_at == fixed_time
        assert detail.config_snapshot is None
        assert detail.suggestion == "Retrain the model with more diverse data."
        assert len(detail.related_fields) == 3
        assert "metrics.precision" in detail.related_fields


@pytest.mark.unit
class TestModelInvariantViolationDetailSerialization:
    """Test serialization and deserialization."""

    def test_serialization_roundtrip(self) -> None:
        """JSON serialization and deserialization preserves all data."""
        fixed_time = datetime(2024, 6, 15, 12, 30, 45, tzinfo=UTC)
        original = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_1,
            invariant_name="Roundtrip test invariant",
            invariant_type=EnumInvariantType.FIELD_VALUE,
            severity=EnumSeverity.WARNING,
            field_path="response.status",
            actual_value="error",
            expected_value="success",
            message="Status mismatch detected",
            explanation="Response status does not match expected value.",
            comparison_type=EnumComparisonType.EXACT,
            operator="==",
            evaluated_at=fixed_time,
            suggestion="Check the upstream service for errors.",
            related_fields=["response.error_code", "response.message"],
        )

        # Serialize to JSON string
        json_str = original.model_dump_json()

        # Deserialize back to model
        restored = ModelInvariantViolationDetail.model_validate_json(json_str)

        # Verify all fields match
        assert restored.invariant_id == original.invariant_id
        assert restored.invariant_name == original.invariant_name
        assert restored.invariant_type == original.invariant_type
        assert restored.severity == original.severity
        assert restored.field_path == original.field_path
        assert restored.actual_value == original.actual_value
        assert restored.expected_value == original.expected_value
        assert restored.message == original.message
        assert restored.explanation == original.explanation
        assert restored.comparison_type == original.comparison_type
        assert restored.operator == original.operator
        assert restored.evaluated_at == original.evaluated_at
        assert restored.suggestion == original.suggestion
        assert restored.related_fields == original.related_fields

    def test_serialization_roundtrip_with_config_snapshot(self) -> None:
        """JSON roundtrip preserves config_snapshot discriminated union."""
        config = ModelLatencyConfig(max_ms=5000)
        original = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_2,
            invariant_name="Config snapshot roundtrip",
            invariant_type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.WARNING,
            actual_value=7500,
            expected_value=5000,
            message="Latency exceeded",
            explanation="Response took too long",
            comparison_type=EnumComparisonType.RANGE,
            config_snapshot=config,
        )

        # Roundtrip through JSON
        json_str = original.model_dump_json()
        restored = ModelInvariantViolationDetail.model_validate_json(json_str)

        assert restored.config_snapshot is not None
        assert isinstance(restored.config_snapshot, ModelLatencyConfig)
        assert restored.config_snapshot.max_ms == 5000

    def test_model_dump_produces_dict(self) -> None:
        """model_dump produces dictionary with correct types."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_1,
            invariant_name="Dict dump test",
            invariant_type=EnumInvariantType.SCHEMA,
            severity=EnumSeverity.CRITICAL,
            message="Test",
            explanation="Test explanation",
            comparison_type=EnumComparisonType.SCHEMA,
        )
        data = detail.model_dump()

        assert isinstance(data, dict)
        assert data["invariant_id"] == TEST_UUID_1
        assert data["invariant_name"] == "Dict dump test"
        assert data["invariant_type"] == EnumInvariantType.SCHEMA
        assert data["severity"] == EnumSeverity.CRITICAL

    def test_to_dict_for_display_all_strings(self) -> None:
        """to_dict_for_display returns all string values."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_1,
            invariant_name="Display dict test",
            invariant_type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.WARNING,
            actual_value=1234,
            expected_value=1000,
            message="Test message",
            explanation="Test explanation",
            comparison_type=EnumComparisonType.RANGE,
            operator="<=",
            related_fields=["field1", "field2"],
        )
        display_dict = detail.to_dict_for_display()

        # All values must be strings
        for key, value in display_dict.items():
            assert isinstance(value, str), (
                f"Key '{key}' has non-string value of type {type(value).__name__}"
            )

        # Verify specific conversions
        assert display_dict["invariant_id"] == str(TEST_UUID_1)
        assert display_dict["actual_value"] == "1234"
        assert display_dict["severity"] == "warning"
        assert display_dict["related_fields"] == "field1, field2"


@pytest.mark.unit
class TestModelInvariantViolationDetailFormatters:
    """Test formatting helper methods."""

    def test_format_comparison_with_operator(self) -> None:
        """format_comparison includes operator when present."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_1,
            invariant_name="Threshold check",
            invariant_type=EnumInvariantType.THRESHOLD,
            severity=EnumSeverity.CRITICAL,
            actual_value=0.65,
            expected_value=0.8,
            message="Below threshold",
            explanation="Value is too low",
            comparison_type=EnumComparisonType.RANGE,
            operator=">=",
        )
        formatted = detail.format_comparison()

        assert "Expected:" in formatted
        assert ">=" in formatted
        assert "0.8" in formatted
        assert "Got:" in formatted
        assert "0.65" in formatted
        # Should produce: "Expected: >= 0.8, Got: 0.65"

    def test_format_comparison_without_operator(self) -> None:
        """format_comparison works without operator."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_2,
            invariant_name="Exact match check",
            invariant_type=EnumInvariantType.FIELD_VALUE,
            severity=EnumSeverity.WARNING,
            actual_value="error",
            expected_value="success",
            message="Status mismatch",
            explanation="Status does not match",
            comparison_type=EnumComparisonType.EXACT,
            operator=None,  # Explicitly no operator
        )
        formatted = detail.format_comparison()

        assert "Expected:" in formatted
        assert "success" in formatted
        assert "Got:" in formatted
        assert "error" in formatted
        # Should NOT contain any operator symbols
        assert ">=" not in formatted
        assert "<=" not in formatted
        assert "==" not in formatted

    def test_to_log_entry_format(self) -> None:
        """to_log_entry returns properly formatted log line."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_3,
            invariant_name="Latency Check",
            invariant_type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.WARNING,
            field_path="response.latency_ms",
            message="Response time exceeded limit",
            explanation="Too slow",
            comparison_type=EnumComparisonType.RANGE,
        )
        log_entry = detail.to_log_entry()

        # Should be single line
        assert "\n" not in log_entry
        # Should contain severity in uppercase
        assert "WARNING" in log_entry
        # Should contain invariant name
        assert "Latency Check" in log_entry
        # Should contain field path
        assert "response.latency_ms" in log_entry
        # Should contain message
        assert "Response time exceeded limit" in log_entry
        # Format: [SEVERITY] name at path: message
        assert log_entry.startswith("[WARNING]")

    def test_to_log_entry_without_field_path(self) -> None:
        """to_log_entry works when field_path is None."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_4,
            invariant_name="Global Check",
            invariant_type=EnumInvariantType.CUSTOM,
            severity=EnumSeverity.CRITICAL,
            field_path=None,
            message="Custom validation failed",
            explanation="Custom check did not pass",
            comparison_type=EnumComparisonType.CUSTOM,
        )
        log_entry = detail.to_log_entry()

        assert "[CRITICAL]" in log_entry
        assert "Global Check" in log_entry
        assert "Custom validation failed" in log_entry
        # Should not have " at " since no field_path
        assert " at " not in log_entry

    def test_format_explanation_for_field_value(self) -> None:
        """format_explanation generates context-aware message for FIELD_VALUE type."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_1,
            invariant_name="Status field check",
            invariant_type=EnumInvariantType.FIELD_VALUE,
            severity=EnumSeverity.WARNING,
            field_path="response.status",
            actual_value="error",
            expected_value="success",
            message="Status mismatch",
            explanation="Status is not the expected value",
            comparison_type=EnumComparisonType.EXACT,
            operator="==",
        )
        explanation = detail.format_explanation()

        # Should mention the field path
        assert "response.status" in explanation
        # Should mention the actual value
        assert "error" in explanation
        # Should mention expected value or operator + expected
        assert "success" in explanation or "==" in explanation

    def test_format_explanation_for_latency(self) -> None:
        """format_explanation generates latency-specific message."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_3,
            invariant_name="Response time",
            invariant_type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.WARNING,
            actual_value=7500,
            expected_value=5000,
            message="Latency exceeded",
            explanation="Response took too long.",
            comparison_type=EnumComparisonType.RANGE,
        )
        explanation = detail.format_explanation()

        # Should contain actual latency
        assert "7500" in explanation
        # Should contain limit
        assert "5000" in explanation
        # Should mention how much over the limit
        assert "2500" in explanation  # 7500 - 5000 = 2500ms over
        # Should contain percentage (50% over)
        assert "50" in explanation

    def test_format_explanation_for_schema(self) -> None:
        """format_explanation generates schema-specific message."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_2,
            invariant_name="Schema validation",
            invariant_type=EnumInvariantType.SCHEMA,
            severity=EnumSeverity.CRITICAL,
            field_path="response.data",
            actual_value=123,  # int instead of expected string
            expected_value="string",
            message="Type mismatch",
            explanation="Expected string type",
            comparison_type=EnumComparisonType.SCHEMA,
        )
        explanation = detail.format_explanation()

        # Should mention the field path
        assert "response.data" in explanation
        # Should mention actual type
        assert "int" in explanation
        # Should mention expected type
        assert "string" in explanation

    def test_format_explanation_for_field_presence(self) -> None:
        """format_explanation generates field presence message."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_4,
            invariant_name="Required field check",
            invariant_type=EnumInvariantType.FIELD_PRESENCE,
            severity=EnumSeverity.CRITICAL,
            field_path="response.usage.total_tokens",
            actual_value=None,
            expected_value="present",
            message="Required field missing",
            explanation="Field must be present",
            comparison_type=EnumComparisonType.PRESENCE,
        )
        explanation = detail.format_explanation()

        # Should mention the field path
        assert "response.usage.total_tokens" in explanation
        # Should indicate the field is missing or required
        assert "missing" in explanation.lower() or "required" in explanation.lower()

    def test_format_explanation_for_threshold(self) -> None:
        """format_explanation generates threshold-specific message."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_5,
            invariant_name="Accuracy threshold",
            invariant_type=EnumInvariantType.THRESHOLD,
            severity=EnumSeverity.CRITICAL,
            actual_value=0.75,
            expected_value=0.90,
            message="Below threshold",
            explanation="Accuracy is too low",
            comparison_type=EnumComparisonType.RANGE,
            operator=">=",
        )
        explanation = detail.format_explanation()

        # Should mention the metric value
        assert "0.75" in explanation
        # Should mention threshold
        assert "threshold" in explanation.lower()

    def test_format_explanation_fallback_for_custom(self) -> None:
        """format_explanation falls back to explanation field for CUSTOM type."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_1,
            invariant_name="Custom validator",
            invariant_type=EnumInvariantType.CUSTOM,
            severity=EnumSeverity.INFO,
            message="Custom check failed",
            explanation="This is a custom explanation that should be returned as-is.",
            comparison_type=EnumComparisonType.CUSTOM,
        )
        explanation = detail.format_explanation()

        # Should return the original explanation for CUSTOM type
        assert (
            explanation == "This is a custom explanation that should be returned as-is."
        )


@pytest.mark.unit
class TestDetailGeneration:
    """Test Suite 1: Detail generation for different failure types."""

    def test_detail_from_field_value_failure(self) -> None:
        """Field value failure produces correct detail."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_1,
            invariant_name="Confidence score minimum",
            invariant_type=EnumInvariantType.FIELD_VALUE,
            severity=EnumSeverity.CRITICAL,
            field_path="response.confidence",
            actual_value=0.65,
            expected_value=0.8,
            message="Confidence score 0.65 is below minimum 0.8",
            explanation="The confidence score does not meet threshold.",
            comparison_type=EnumComparisonType.RANGE,
            operator=">=",
        )
        assert detail.field_path == "response.confidence"
        assert detail.actual_value == 0.65
        assert detail.expected_value == 0.8
        assert detail.operator == ">="

    def test_detail_from_schema_failure(self) -> None:
        """Schema failure produces correct detail with path."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_2,
            invariant_name="Response matches OpenAI schema",
            invariant_type=EnumInvariantType.SCHEMA,
            severity=EnumSeverity.CRITICAL,
            field_path="response.choices.0.message.content",
            actual_value=None,
            expected_value="string",
            message="Field 'content' is null but string required",
            explanation="The response schema requires a non-null string.",
            comparison_type=EnumComparisonType.SCHEMA,
        )
        assert detail.invariant_type == EnumInvariantType.SCHEMA
        assert detail.field_path == "response.choices.0.message.content"
        assert detail.actual_value is None

    def test_detail_from_latency_failure(self) -> None:
        """Latency failure includes actual vs expected ms."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_3,
            invariant_name="Response under 5 seconds",
            invariant_type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.WARNING,
            field_path="latency_ms",
            actual_value=7250,
            expected_value=5000,
            message="Latency 7.25s exceeds limit of 5s",
            explanation="The model took too long to respond.",
            comparison_type=EnumComparisonType.RANGE,
            operator="<=",
        )
        assert detail.actual_value == 7250
        assert detail.expected_value == 5000

    def test_detail_captures_config_snapshot(self) -> None:
        """Original invariant config preserved in detail."""
        config = ModelLatencyConfig(max_ms=5000)
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_3,
            invariant_name="Latency check",
            invariant_type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.WARNING,
            message="Latency exceeded",
            explanation="Too slow",
            comparison_type=EnumComparisonType.RANGE,
            config_snapshot=config,
        )
        assert detail.config_snapshot == config
        assert isinstance(detail.config_snapshot, ModelLatencyConfig)
        assert detail.config_snapshot.max_ms == 5000

    def test_detail_with_schema_config_snapshot(self) -> None:
        """Schema config type works with config_snapshot."""
        config = ModelSchemaInvariantConfig(
            json_schema={"type": "object", "properties": {"name": {"type": "string"}}}
        )
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_2,
            invariant_name="Schema validation",
            invariant_type=EnumInvariantType.SCHEMA,
            severity=EnumSeverity.CRITICAL,
            message="Schema violation",
            explanation="Response does not match expected schema",
            comparison_type=EnumComparisonType.SCHEMA,
            config_snapshot=config,
        )
        assert isinstance(detail.config_snapshot, ModelSchemaInvariantConfig)
        assert detail.config_snapshot.json_schema["type"] == "object"

    def test_detail_with_field_value_config_snapshot(self) -> None:
        """Field value config type works with config_snapshot."""
        config = ModelFieldValueConfig(
            field_path="response.status",
            expected_value="success",
        )
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_1,
            invariant_name="Status check",
            invariant_type=EnumInvariantType.FIELD_VALUE,
            severity=EnumSeverity.WARNING,
            message="Status mismatch",
            explanation="Expected success status",
            comparison_type=EnumComparisonType.EXACT,
            config_snapshot=config,
        )
        assert isinstance(detail.config_snapshot, ModelFieldValueConfig)
        assert detail.config_snapshot.field_path == "response.status"
        assert detail.config_snapshot.expected_value == "success"

    def test_detail_with_none_config_snapshot(self) -> None:
        """config_snapshot can be None."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_1,
            invariant_name="Simple check",
            invariant_type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.INFO,
            message="Latency info",
            explanation="For informational purposes",
            comparison_type=EnumComparisonType.RANGE,
            config_snapshot=None,
        )
        assert detail.config_snapshot is None


@pytest.mark.unit
class TestExplanationFormatting:
    """Test Suite 2: Explanation formatting."""

    def test_explanation_for_numeric_comparison(self) -> None:
        """Numeric comparisons explain the difference."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_1,
            invariant_name="Accuracy threshold",
            invariant_type=EnumInvariantType.THRESHOLD,
            severity=EnumSeverity.CRITICAL,
            field_path="metrics.accuracy",
            actual_value=0.75,
            expected_value=0.90,
            message="Accuracy below threshold",
            explanation="Accuracy 0.75 is below the 0.90 threshold.",
            comparison_type=EnumComparisonType.RANGE,
            operator=">=",
        )
        explanation = detail.format_explanation()
        assert "0.75" in explanation or "threshold" in explanation.lower()

    def test_explanation_for_missing_field(self) -> None:
        """Missing field explains what was expected."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_4,
            invariant_name="Required field check",
            invariant_type=EnumInvariantType.FIELD_PRESENCE,
            severity=EnumSeverity.CRITICAL,
            field_path="response.usage.total_tokens",
            actual_value=None,
            expected_value="present",
            message="Required field missing",
            explanation="The field response.usage.total_tokens is required.",
            comparison_type=EnumComparisonType.PRESENCE,
        )
        explanation = detail.format_explanation()
        assert "missing" in explanation.lower() or "required" in explanation.lower()

    def test_explanation_for_type_mismatch(self) -> None:
        """Type mismatch shows expected and actual types."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_5,
            invariant_name="Content type check",
            invariant_type=EnumInvariantType.SCHEMA,
            severity=EnumSeverity.CRITICAL,
            field_path="response.content",
            actual_value=123,
            expected_value="string",
            message="Type mismatch",
            explanation="Expected string, got int.",
            comparison_type=EnumComparisonType.SCHEMA,
        )
        explanation = detail.format_explanation()
        assert "int" in explanation or "string" in explanation

    def test_format_explanation_for_latency(self) -> None:
        """Latency explanation includes percentage over limit."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_3,
            invariant_name="Response time",
            invariant_type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.WARNING,
            actual_value=7500,
            expected_value=5000,
            message="Too slow",
            explanation="Response exceeded time limit.",
            comparison_type=EnumComparisonType.RANGE,
        )
        explanation = detail.format_explanation()
        assert "7500" in explanation or "5000" in explanation


@pytest.mark.unit
class TestActualVsExpectedDisplay:
    """Test Suite 3: Actual vs expected display formatting."""

    def test_format_comparison_range(self) -> None:
        """Range comparison shows 'Expected: >= X, Got: Y'."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_1,
            invariant_name="Min threshold",
            invariant_type=EnumInvariantType.THRESHOLD,
            severity=EnumSeverity.CRITICAL,
            actual_value=0.65,
            expected_value=0.8,
            message="Below threshold",
            explanation="Value too low",
            comparison_type=EnumComparisonType.RANGE,
            operator=">=",
        )
        formatted = detail.format_comparison()
        assert "Expected:" in formatted
        assert ">=" in formatted
        assert "0.8" in formatted
        assert "Got:" in formatted
        assert "0.65" in formatted

    def test_format_comparison_exact(self) -> None:
        """Exact comparison shows 'Expected: X, Got: Y'."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_2,
            invariant_name="Status check",
            invariant_type=EnumInvariantType.FIELD_VALUE,
            severity=EnumSeverity.CRITICAL,
            actual_value="error",
            expected_value="success",
            message="Wrong status",
            explanation="Expected success",
            comparison_type=EnumComparisonType.EXACT,
        )
        formatted = detail.format_comparison()
        assert "Expected:" in formatted
        assert "success" in formatted
        assert "Got:" in formatted
        assert "error" in formatted

    def test_format_comparison_pattern(self) -> None:
        """Pattern shows expected pattern and actual value."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_3,
            invariant_name="ID format",
            invariant_type=EnumInvariantType.FIELD_VALUE,
            severity=EnumSeverity.WARNING,
            actual_value="abc123",
            expected_value=r"^[A-Z]{3}-\d{4}$",
            message="Invalid ID format",
            explanation="ID must match pattern",
            comparison_type=EnumComparisonType.PATTERN,
        )
        formatted = detail.format_comparison()
        assert "abc123" in formatted

    def test_format_truncates_long_values(self) -> None:
        """Long values truncated for display."""
        long_value = "x" * 200
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_4,
            invariant_name="Content check",
            invariant_type=EnumInvariantType.FIELD_VALUE,
            severity=EnumSeverity.INFO,
            actual_value=long_value,
            expected_value="short",
            message="Content mismatch",
            explanation="Values differ",
            comparison_type=EnumComparisonType.EXACT,
        )
        formatted = detail.format_comparison()
        assert "..." in formatted
        assert len(formatted) < 250  # Reasonable display length


@pytest.mark.unit
class TestUtilityMethods:
    """Test Suite 4: Utility methods."""

    def test_to_log_entry_single_line(self) -> None:
        """Log entry is single line with key info."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_1,
            invariant_name="Latency Check",
            invariant_type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.WARNING,
            field_path="latency_ms",
            message="Response too slow",
            explanation="Exceeded limit",
            comparison_type=EnumComparisonType.RANGE,
        )
        log_entry = detail.to_log_entry()
        assert "\n" not in log_entry
        assert "WARNING" in log_entry
        assert "Latency Check" in log_entry
        assert "latency_ms" in log_entry

    def test_to_log_entry_critical_severity(self) -> None:
        """Log entry shows CRITICAL for critical severity."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_1,
            invariant_name="Critical Check",
            invariant_type=EnumInvariantType.SCHEMA,
            severity=EnumSeverity.CRITICAL,
            message="Schema violation",
            explanation="Invalid schema",
            comparison_type=EnumComparisonType.SCHEMA,
        )
        log_entry = detail.to_log_entry()
        assert "CRITICAL" in log_entry

    def test_to_dict_for_display_all_strings(self) -> None:
        """Display dict has all string values."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_1,
            invariant_name="Test",
            invariant_type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.WARNING,
            actual_value=1234,
            expected_value=1000,
            message="Test message",
            explanation="Test explanation",
            comparison_type=EnumComparisonType.RANGE,
            operator="<=",
            related_fields=["field1", "field2"],
        )
        display_dict = detail.to_dict_for_display()

        # All values should be strings
        for key, value in display_dict.items():
            assert isinstance(value, str), (
                f"Key '{key}' has non-string value: {type(value)}"
            )

        # Check specific conversions
        assert display_dict["actual_value"] == "1234"
        assert display_dict["severity"] == "warning"
        assert display_dict["related_fields"] == "field1, field2"

    def test_to_dict_for_display_handles_none_values(self) -> None:
        """Display dict handles None values gracefully."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_1,
            invariant_name="Test",
            invariant_type=EnumInvariantType.LATENCY,
            severity=EnumSeverity.WARNING,
            message="Test",
            explanation="Test",
            comparison_type=EnumComparisonType.RANGE,
        )
        display_dict = detail.to_dict_for_display()
        assert display_dict["field_path"] == ""
        assert display_dict["operator"] == ""
        assert display_dict["suggestion"] == ""

    def test_serialization_preserves_any_type(self) -> None:
        """actual_value of any type serializes correctly."""
        # Test with different types
        test_cases: list[dict[str, object]] = [
            {"value": 123, "expected": "123"},
            {"value": 45.67, "expected": "45.67"},
            {"value": "string", "expected": "string"},
            {"value": None, "expected": "null"},
            {"value": [1, 2, 3], "expected": "[1, 2, 3]"},
            {"value": {"key": "value"}, "expected": "{'key': 'value'}"},
        ]

        for case in test_cases:
            value = case["value"]
            expected = str(case["expected"])
            detail = ModelInvariantViolationDetail(
                invariant_id=TEST_UUID_1,
                invariant_name="Test",
                invariant_type=EnumInvariantType.FIELD_VALUE,
                severity=EnumSeverity.WARNING,
                actual_value=value,
                message="Test",
                explanation="Test",
                comparison_type=EnumComparisonType.EXACT,
            )
            display = detail.to_dict_for_display()
            assert display["actual_value"] == expected


@pytest.mark.unit
class TestComparisonTypeUsage:
    """Test all comparison types work correctly."""

    @pytest.mark.parametrize("comparison_type", list(EnumComparisonType))
    def test_all_comparison_types_accepted(
        self, comparison_type: EnumComparisonType
    ) -> None:
        """All comparison types should be valid."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_1,
            invariant_name="Test",
            invariant_type=EnumInvariantType.FIELD_VALUE,
            severity=EnumSeverity.WARNING,
            message="Test",
            explanation="Test",
            comparison_type=comparison_type,
        )
        assert detail.comparison_type == comparison_type


@pytest.mark.unit
class TestInvariantTypeUsage:
    """Test all invariant types work correctly."""

    @pytest.mark.parametrize("invariant_type", list(EnumInvariantType))
    def test_all_invariant_types_accepted(
        self, invariant_type: EnumInvariantType
    ) -> None:
        """All invariant types should be valid."""
        detail = ModelInvariantViolationDetail(
            invariant_id=TEST_UUID_1,
            invariant_name="Test",
            invariant_type=invariant_type,
            severity=EnumSeverity.WARNING,
            message="Test",
            explanation="Test",
            comparison_type=EnumComparisonType.EXACT,
        )
        assert detail.invariant_type == invariant_type
