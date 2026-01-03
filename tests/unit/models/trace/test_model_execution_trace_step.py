"""
Unit tests for ModelExecutionTraceStep.

Tests comprehensive execution trace step functionality including:
- Model instantiation and validation
- Step kind and status literal validation
- Error summary bounded length (max 500 chars with truncation)
- Duration validation (non-negative values)
- Optional reference fields
- Utility methods (is_successful, is_failure, etc.)
- Serialization and deserialization
- Edge cases and error conditions
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from omnibase_core.models.trace import (
    ModelExecutionTraceStep,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def minimal_step_data() -> dict:
    """Minimal required data for creating a trace step."""
    return {
        "step_id": "step-001",
        "step_kind": "handler",
        "name": "fetch_data",
        "start_ts": datetime.now(UTC),
        "end_ts": datetime.now(UTC),
        "duration_ms": 100.0,
        "status": "success",
    }


@pytest.fixture
def full_step_data() -> dict:
    """Complete data for creating a trace step with all fields."""
    return {
        "step_id": "step-002",
        "step_kind": "effect_call",
        "name": "transform_data",
        "start_ts": datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        "end_ts": datetime(2025, 1, 1, 12, 0, 5, tzinfo=UTC),
        "duration_ms": 5000.0,
        "status": "success",
        "error_summary": None,
        "manifest_ref": uuid4(),
        "effect_record_ref": uuid4(),
        "invariant_result_ref": uuid4(),
    }


@pytest.fixture
def failed_step_data() -> dict:
    """Data for a failed trace step with error summary."""
    return {
        "step_id": "step-fail-001",
        "step_kind": "effect_call",
        "name": "write_database",
        "start_ts": datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        "end_ts": datetime(2025, 1, 1, 12, 0, 1, tzinfo=UTC),
        "duration_ms": 1000.0,
        "status": "failure",
        "error_summary": "Connection refused: database unavailable",
    }


# ============================================================================
# Test: Step Creation with Required Fields
# ============================================================================


@pytest.mark.unit
class TestModelExecutionTraceStepInstantiation:
    """Test cases for ModelExecutionTraceStep instantiation."""

    def test_step_creation_with_required_fields(self, minimal_step_data: dict) -> None:
        """Test step creation with only required fields."""
        step = ModelExecutionTraceStep(**minimal_step_data)

        assert step.step_id == "step-001"
        assert step.step_kind == "handler"
        assert step.name == "fetch_data"
        assert step.status == "success"
        assert step.start_ts is not None
        assert step.end_ts is not None
        assert step.duration_ms == 100.0
        # Optional fields should have default values
        assert step.error_summary is None
        assert step.manifest_ref is None
        assert step.effect_record_ref is None
        assert step.invariant_result_ref is None

    def test_step_creation_with_all_fields(self, full_step_data: dict) -> None:
        """Test step creation with all fields populated."""
        step = ModelExecutionTraceStep(**full_step_data)

        assert step.step_id == "step-002"
        assert step.step_kind == "effect_call"
        assert step.name == "transform_data"
        assert step.status == "success"
        assert step.start_ts == datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        assert step.end_ts == datetime(2025, 1, 1, 12, 0, 5, tzinfo=UTC)
        assert step.duration_ms == 5000.0
        assert isinstance(step.manifest_ref, UUID)
        assert isinstance(step.effect_record_ref, UUID)
        assert isinstance(step.invariant_result_ref, UUID)
        assert step.error_summary is None

    def test_step_creation_with_failed_status(self, failed_step_data: dict) -> None:
        """Test step creation with failure status and error summary."""
        step = ModelExecutionTraceStep(**failed_step_data)

        assert step.status == "failure"
        assert step.error_summary == "Connection refused: database unavailable"


# ============================================================================
# Test: Step Kind Validation
# ============================================================================


@pytest.mark.unit
class TestModelExecutionTraceStepKindValidation:
    """Test step_kind literal validation."""

    def test_step_kind_hook_valid(self, minimal_step_data: dict) -> None:
        """Test that 'hook' is a valid step kind."""
        minimal_step_data["step_kind"] = "hook"
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.step_kind == "hook"

    def test_step_kind_handler_valid(self, minimal_step_data: dict) -> None:
        """Test that 'handler' is a valid step kind."""
        minimal_step_data["step_kind"] = "handler"
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.step_kind == "handler"

    def test_step_kind_effect_call_valid(self, minimal_step_data: dict) -> None:
        """Test that 'effect_call' is a valid step kind."""
        minimal_step_data["step_kind"] = "effect_call"
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.step_kind == "effect_call"

    def test_step_kind_invariant_eval_valid(self, minimal_step_data: dict) -> None:
        """Test that 'invariant_eval' is a valid step kind."""
        minimal_step_data["step_kind"] = "invariant_eval"
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.step_kind == "invariant_eval"

    def test_step_kind_invalid_raises_validation_error(
        self, minimal_step_data: dict
    ) -> None:
        """Test that invalid step_kind raises ValidationError."""
        minimal_step_data["step_kind"] = "invalid_kind"
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionTraceStep(**minimal_step_data)
        assert "step_kind" in str(exc_info.value)

    def test_step_kind_empty_string_raises_validation_error(
        self, minimal_step_data: dict
    ) -> None:
        """Test that empty string step_kind raises ValidationError."""
        minimal_step_data["step_kind"] = ""
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionTraceStep(**minimal_step_data)
        assert "step_kind" in str(exc_info.value)


# ============================================================================
# Test: Status Validation
# ============================================================================


@pytest.mark.unit
class TestModelExecutionTraceStepStatusValidation:
    """Test status literal validation."""

    def test_status_success_valid(self, minimal_step_data: dict) -> None:
        """Test that 'success' is a valid status."""
        minimal_step_data["status"] = "success"
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.status == "success"

    def test_status_failure_valid(self, minimal_step_data: dict) -> None:
        """Test that 'failure' is a valid status."""
        minimal_step_data["status"] = "failure"
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.status == "failure"

    def test_status_skipped_valid(self, minimal_step_data: dict) -> None:
        """Test that 'skipped' is a valid status."""
        minimal_step_data["status"] = "skipped"
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.status == "skipped"

    def test_status_invalid_raises_validation_error(
        self, minimal_step_data: dict
    ) -> None:
        """Test that invalid status raises ValidationError."""
        minimal_step_data["status"] = "invalid_status"
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionTraceStep(**minimal_step_data)
        assert "status" in str(exc_info.value)

    def test_status_empty_string_raises_validation_error(
        self, minimal_step_data: dict
    ) -> None:
        """Test that empty string status raises ValidationError."""
        minimal_step_data["status"] = ""
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionTraceStep(**minimal_step_data)
        assert "status" in str(exc_info.value)


# ============================================================================
# Test: Error Summary Bounded Length
# ============================================================================


@pytest.mark.unit
class TestModelExecutionTraceStepErrorSummaryBounded:
    """Test error_summary bounded length (max 500 chars with truncation)."""

    def test_error_summary_within_limit(self, failed_step_data: dict) -> None:
        """Test error summary within 500 char limit is preserved."""
        error_msg = "Short error message"
        failed_step_data["error_summary"] = error_msg
        step = ModelExecutionTraceStep(**failed_step_data)
        assert step.error_summary == error_msg
        assert len(step.error_summary) == len(error_msg)

    def test_error_summary_exactly_500_chars(self, failed_step_data: dict) -> None:
        """Test error summary exactly at 500 char limit."""
        error_msg = "x" * 500
        failed_step_data["error_summary"] = error_msg
        step = ModelExecutionTraceStep(**failed_step_data)
        assert step.error_summary == error_msg
        assert len(step.error_summary) == 500

    def test_error_summary_truncated_when_exceeds_limit(
        self, failed_step_data: dict
    ) -> None:
        """Test error summary exceeding 500 chars is truncated."""
        error_msg = "x" * 600  # 600 chars, should be truncated to 500
        failed_step_data["error_summary"] = error_msg
        step = ModelExecutionTraceStep(**failed_step_data)
        # Should be truncated to max 500 chars with "..." suffix
        assert len(step.error_summary) == 500
        assert step.error_summary.endswith("...")

    def test_error_summary_very_long_truncated(self, failed_step_data: dict) -> None:
        """Test very long error summary (10000 chars) is truncated."""
        error_msg = "error: " + "y" * 10000
        failed_step_data["error_summary"] = error_msg
        step = ModelExecutionTraceStep(**failed_step_data)
        assert len(step.error_summary) == 500
        assert step.error_summary.startswith("error: ")
        assert step.error_summary.endswith("...")

    def test_error_summary_none_allowed(self, minimal_step_data: dict) -> None:
        """Test error_summary can be None."""
        minimal_step_data["error_summary"] = None
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.error_summary is None

    def test_error_summary_empty_string_allowed(self, minimal_step_data: dict) -> None:
        """Test error_summary can be empty string."""
        minimal_step_data["error_summary"] = ""
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.error_summary == ""


# ============================================================================
# Test: Duration Validation
# ============================================================================


@pytest.mark.unit
class TestModelExecutionTraceStepDurationValidation:
    """Test duration_ms validation (non-negative values only)."""

    def test_duration_ms_positive(self, minimal_step_data: dict) -> None:
        """Test positive duration_ms is accepted."""
        minimal_step_data["duration_ms"] = 1000.0
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.duration_ms == 1000.0

    def test_duration_ms_zero_valid(self, minimal_step_data: dict) -> None:
        """Test zero duration_ms is valid (instant execution)."""
        minimal_step_data["duration_ms"] = 0.0
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.duration_ms == 0.0

    def test_duration_ms_large_value(self, minimal_step_data: dict) -> None:
        """Test large duration_ms is accepted."""
        minimal_step_data["duration_ms"] = 86400000.0  # 24 hours in ms
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.duration_ms == 86400000.0

    def test_duration_ms_float_precision(self, minimal_step_data: dict) -> None:
        """Test duration_ms handles float precision."""
        minimal_step_data["duration_ms"] = 45.678
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.duration_ms == 45.678

    def test_duration_ms_negative_raises_validation_error(
        self, minimal_step_data: dict
    ) -> None:
        """Test negative duration_ms raises ValidationError."""
        minimal_step_data["duration_ms"] = -1.0
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionTraceStep(**minimal_step_data)
        assert "duration_ms" in str(exc_info.value)


# ============================================================================
# Test: Time Ordering Validation (end_ts >= start_ts)
# ============================================================================


@pytest.mark.unit
class TestModelExecutionTraceStepTimeOrdering:
    """Test time ordering validation (end_ts must be >= start_ts)."""

    def test_end_ts_equal_to_start_ts_valid(self, minimal_step_data: dict) -> None:
        """Test that end_ts == start_ts is valid (instant execution)."""
        same_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        minimal_step_data["start_ts"] = same_time
        minimal_step_data["end_ts"] = same_time
        minimal_step_data["duration_ms"] = 0.0
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.start_ts == step.end_ts

    def test_end_ts_after_start_ts_valid(self, minimal_step_data: dict) -> None:
        """Test that end_ts > start_ts is valid (normal case)."""
        start = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        end = datetime(2025, 1, 1, 12, 0, 5, tzinfo=UTC)
        minimal_step_data["start_ts"] = start
        minimal_step_data["end_ts"] = end
        minimal_step_data["duration_ms"] = 5000.0
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.end_ts > step.start_ts

    def test_end_ts_before_start_ts_raises_validation_error(
        self, minimal_step_data: dict
    ) -> None:
        """Test that end_ts < start_ts raises ValidationError."""
        start = datetime(2025, 1, 1, 12, 0, 5, tzinfo=UTC)
        end = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)  # Before start
        minimal_step_data["start_ts"] = start
        minimal_step_data["end_ts"] = end
        minimal_step_data["duration_ms"] = 0.0
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionTraceStep(**minimal_step_data)
        error_str = str(exc_info.value)
        assert "end_ts" in error_str
        assert "start_ts" in error_str

    def test_end_ts_before_start_ts_error_message_contains_timestamps(
        self, minimal_step_data: dict
    ) -> None:
        """Test that the error message includes the actual timestamps."""
        start = datetime(2025, 1, 1, 12, 0, 10, tzinfo=UTC)
        end = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)  # 10 seconds before
        minimal_step_data["start_ts"] = start
        minimal_step_data["end_ts"] = end
        minimal_step_data["duration_ms"] = 0.0
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionTraceStep(**minimal_step_data)
        error_str = str(exc_info.value)
        assert "cannot be before" in error_str


# ============================================================================
# Test: Optional Reference Fields Default to None
# ============================================================================


@pytest.mark.unit
class TestModelExecutionTraceStepOptionalRefs:
    """Test optional reference fields default to None."""

    def test_optional_refs_default_none(self, minimal_step_data: dict) -> None:
        """Test all optional ref fields default to None."""
        step = ModelExecutionTraceStep(**minimal_step_data)

        assert step.manifest_ref is None
        assert step.effect_record_ref is None
        assert step.invariant_result_ref is None

    def test_manifest_ref_accepts_uuid(self, minimal_step_data: dict) -> None:
        """Test manifest_ref accepts UUID value."""
        manifest_ref = uuid4()
        minimal_step_data["manifest_ref"] = manifest_ref
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.manifest_ref == manifest_ref

    def test_effect_record_ref_accepts_uuid(self, minimal_step_data: dict) -> None:
        """Test effect_record_ref accepts UUID value."""
        effect_record_ref = uuid4()
        minimal_step_data["effect_record_ref"] = effect_record_ref
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.effect_record_ref == effect_record_ref

    def test_invariant_result_ref_accepts_uuid(self, minimal_step_data: dict) -> None:
        """Test invariant_result_ref accepts UUID value."""
        invariant_result_ref = uuid4()
        minimal_step_data["invariant_result_ref"] = invariant_result_ref
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.invariant_result_ref == invariant_result_ref


# ============================================================================
# Test: Utility Methods
# ============================================================================


@pytest.mark.unit
class TestModelExecutionTraceStepUtilityMethods:
    """Test utility methods on ModelExecutionTraceStep."""

    def test_is_successful(self, minimal_step_data: dict) -> None:
        """Test is_successful() returns True for success status."""
        minimal_step_data["status"] = "success"
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.is_successful() is True

    def test_is_successful_false_for_failure(self, minimal_step_data: dict) -> None:
        """Test is_successful() returns False for failure status."""
        minimal_step_data["status"] = "failure"
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.is_successful() is False

    def test_is_failure(self, failed_step_data: dict) -> None:
        """Test is_failure() returns True for failure status."""
        step = ModelExecutionTraceStep(**failed_step_data)
        assert step.is_failure() is True

    def test_is_failure_false_for_success(self, minimal_step_data: dict) -> None:
        """Test is_failure() returns False for success status."""
        minimal_step_data["status"] = "success"
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.is_failure() is False

    def test_is_skipped(self, minimal_step_data: dict) -> None:
        """Test is_skipped() returns True for skipped status."""
        minimal_step_data["status"] = "skipped"
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.is_skipped() is True

    def test_is_skipped_false_for_success(self, minimal_step_data: dict) -> None:
        """Test is_skipped() returns False for success status."""
        minimal_step_data["status"] = "success"
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.is_skipped() is False

    def test_has_error(self, failed_step_data: dict) -> None:
        """Test has_error() returns True when error_summary is set."""
        step = ModelExecutionTraceStep(**failed_step_data)
        assert step.has_error() is True

    def test_has_error_false_when_no_error(self, minimal_step_data: dict) -> None:
        """Test has_error() returns False when no error_summary."""
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.has_error() is False

    def test_has_manifest_ref(self, minimal_step_data: dict) -> None:
        """Test has_manifest_ref() returns True when set."""
        minimal_step_data["manifest_ref"] = uuid4()
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.has_manifest_ref() is True

    def test_has_manifest_ref_false(self, minimal_step_data: dict) -> None:
        """Test has_manifest_ref() returns False when not set."""
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.has_manifest_ref() is False

    def test_has_effect_record_ref(self, minimal_step_data: dict) -> None:
        """Test has_effect_record_ref() returns True when set."""
        minimal_step_data["effect_record_ref"] = uuid4()
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.has_effect_record_ref() is True

    def test_has_invariant_result_ref(self, minimal_step_data: dict) -> None:
        """Test has_invariant_result_ref() returns True when set."""
        minimal_step_data["invariant_result_ref"] = uuid4()
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.has_invariant_result_ref() is True


# ============================================================================
# Test: JSON Serialization Roundtrip
# ============================================================================


@pytest.mark.unit
class TestModelExecutionTraceStepSerialization:
    """Test JSON serialization and deserialization."""

    def test_step_json_serialization_roundtrip(self, full_step_data: dict) -> None:
        """Test full JSON serialization and deserialization roundtrip."""
        step = ModelExecutionTraceStep(**full_step_data)

        # Serialize to JSON
        json_str = step.model_dump_json()
        assert isinstance(json_str, str)

        # Deserialize from JSON
        restored = ModelExecutionTraceStep.model_validate_json(json_str)

        # Verify all fields match
        assert restored.step_id == step.step_id
        assert restored.step_kind == step.step_kind
        assert restored.name == step.name
        assert restored.status == step.status
        assert restored.start_ts == step.start_ts
        assert restored.end_ts == step.end_ts
        assert restored.duration_ms == step.duration_ms
        assert restored.manifest_ref == step.manifest_ref
        assert restored.effect_record_ref == step.effect_record_ref
        assert restored.invariant_result_ref == step.invariant_result_ref
        assert restored.error_summary == step.error_summary

    def test_step_json_serialization_minimal(self, minimal_step_data: dict) -> None:
        """Test JSON roundtrip with minimal data."""
        step = ModelExecutionTraceStep(**minimal_step_data)

        json_str = step.model_dump_json()
        restored = ModelExecutionTraceStep.model_validate_json(json_str)

        assert restored.step_id == step.step_id
        assert restored.step_kind == step.step_kind
        assert restored.name == step.name
        assert restored.status == step.status

    def test_step_model_dump_contains_all_fields(self, full_step_data: dict) -> None:
        """Test model_dump contains all expected fields."""
        step = ModelExecutionTraceStep(**full_step_data)
        data = step.model_dump()

        assert "step_id" in data
        assert "step_kind" in data
        assert "name" in data
        assert "status" in data
        assert "start_ts" in data
        assert "end_ts" in data
        assert "duration_ms" in data
        assert "manifest_ref" in data
        assert "effect_record_ref" in data
        assert "invariant_result_ref" in data
        assert "error_summary" in data

    def test_step_model_validate_from_dict(self, full_step_data: dict) -> None:
        """Test model validation from dictionary."""
        step = ModelExecutionTraceStep.model_validate(full_step_data)
        assert step.step_id == full_step_data["step_id"]
        assert step.step_kind == full_step_data["step_kind"]


# ============================================================================
# Test: Edge Cases and Error Conditions
# ============================================================================


@pytest.mark.unit
class TestModelExecutionTraceStepEdgeCases:
    """Test edge cases for ModelExecutionTraceStep."""

    def test_step_id_min_length(self, minimal_step_data: dict) -> None:
        """Test step_id must have minimum length of 1."""
        minimal_step_data["step_id"] = "x"  # Single char is valid
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.step_id == "x"

    def test_step_id_empty_raises_validation_error(
        self, minimal_step_data: dict
    ) -> None:
        """Test empty step_id raises ValidationError."""
        minimal_step_data["step_id"] = ""
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionTraceStep(**minimal_step_data)
        assert "step_id" in str(exc_info.value)

    def test_name_min_length(self, minimal_step_data: dict) -> None:
        """Test name must have minimum length of 1."""
        minimal_step_data["name"] = "x"  # Single char is valid
        step = ModelExecutionTraceStep(**minimal_step_data)
        assert step.name == "x"

    def test_name_empty_raises_validation_error(self, minimal_step_data: dict) -> None:
        """Test empty name raises ValidationError."""
        minimal_step_data["name"] = ""
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionTraceStep(**minimal_step_data)
        assert "name" in str(exc_info.value)

    def test_name_with_special_characters(self, minimal_step_data: dict) -> None:
        """Test name with special characters."""
        special_names = [
            "step-with-dashes",
            "step_with_underscores",
            "step.with.dots",
            "step:with:colons",
            "step with spaces",
        ]
        for name in special_names:
            minimal_step_data["name"] = name
            step = ModelExecutionTraceStep(**minimal_step_data)
            assert step.name == name

    def test_model_equality(self, minimal_step_data: dict) -> None:
        """Test model equality comparison."""
        step1 = ModelExecutionTraceStep(**minimal_step_data)
        step2 = ModelExecutionTraceStep(**minimal_step_data)
        # Same data should produce equal models
        assert step1 == step2

    def test_model_inequality(self, minimal_step_data: dict) -> None:
        """Test model inequality when fields differ."""
        step1 = ModelExecutionTraceStep(**minimal_step_data)
        minimal_step_data["name"] = "different_name"
        step2 = ModelExecutionTraceStep(**minimal_step_data)
        assert step1 != step2

    def test_frozen_model_immutability(self, minimal_step_data: dict) -> None:
        """Test that the model is frozen (immutable)."""
        step = ModelExecutionTraceStep(**minimal_step_data)
        with pytest.raises(ValidationError):
            step.name = "new_name"  # type: ignore[misc]

    def test_extra_fields_forbidden(self, minimal_step_data: dict) -> None:
        """Test that extra fields are rejected."""
        minimal_step_data["extra_field"] = "should_fail"
        with pytest.raises(ValidationError) as exc_info:
            ModelExecutionTraceStep(**minimal_step_data)
        assert "extra" in str(exc_info.value).lower()

    def test_str_representation(self, minimal_step_data: dict) -> None:
        """Test __str__ method."""
        step = ModelExecutionTraceStep(**minimal_step_data)
        str_repr = str(step)
        assert "fetch_data" in str_repr
        assert "handler" in str_repr
        assert "success" in str_repr

    def test_repr_representation(self, minimal_step_data: dict) -> None:
        """Test __repr__ method."""
        step = ModelExecutionTraceStep(**minimal_step_data)
        repr_str = repr(step)
        assert "ModelExecutionTraceStep" in repr_str
        assert "step-001" in repr_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
