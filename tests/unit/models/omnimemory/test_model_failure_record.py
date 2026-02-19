# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""
Unit tests for ModelFailureRecord.

Tests comprehensive failure record functionality including:
- Model instantiation and validation
- Immutability (frozen model)
- Auto-generated failure_id
- Timezone-aware timestamp validation
- Non-empty string field validation
- Retry attempt non-negative constraint
- Recovery outcome literal values
- Serialization and deserialization
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

pytestmark = pytest.mark.unit

from omnibase_core.enums.enum_failure_type import EnumFailureType
from omnibase_core.models.omnimemory.model_failure_record import ModelFailureRecord

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def minimal_record_data() -> dict:
    """Minimal required data for creating a failure record."""
    return {
        "timestamp": datetime.now(UTC),
        "failure_type": EnumFailureType.TIMEOUT,
        "step_context": "code_generation",
        "error_code": "TIMEOUT_001",
        "error_message": "Operation exceeded 30s timeout",
    }


@pytest.fixture
def full_record_data() -> dict:
    """Complete data including all optional fields."""
    return {
        "failure_id": uuid4(),
        "timestamp": datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        "failure_type": EnumFailureType.MODEL_ERROR,
        "step_context": "code_review",
        "error_code": "MODEL_001",
        "error_message": "Model returned invalid JSON response",
        "model_used": "gpt-4",
        "retry_attempt": 2,
        "recovery_action": "Retry with simplified prompt",
        "recovery_outcome": "success",
        "should_remember": True,
    }


# ============================================================================
# Test: Model Instantiation
# ============================================================================


class TestModelFailureRecordInstantiation:
    """Tests for model instantiation and basic functionality."""

    def test_create_with_minimal_data(self, minimal_record_data: dict) -> None:
        """Test creating record with only required fields."""
        record = ModelFailureRecord(**minimal_record_data)

        assert record.failure_type == EnumFailureType.TIMEOUT
        assert record.step_context == "code_generation"
        assert record.error_code == "TIMEOUT_001"
        assert record.error_message == "Operation exceeded 30s timeout"
        assert isinstance(record.failure_id, UUID)

    def test_create_with_full_data(self, full_record_data: dict) -> None:
        """Test creating record with all fields explicitly set."""
        record = ModelFailureRecord(**full_record_data)

        assert record.failure_id == full_record_data["failure_id"]
        assert record.failure_type == EnumFailureType.MODEL_ERROR
        assert record.step_context == "code_review"
        assert record.model_used == "gpt-4"
        assert record.retry_attempt == 2
        assert record.recovery_action == "Retry with simplified prompt"
        assert record.recovery_outcome == "success"

    def test_auto_generated_failure_id(self, minimal_record_data: dict) -> None:
        """Test that failure_id is auto-generated when not provided."""
        record1 = ModelFailureRecord(**minimal_record_data)
        record2 = ModelFailureRecord(**minimal_record_data)

        assert isinstance(record1.failure_id, UUID)
        assert isinstance(record2.failure_id, UUID)
        assert record1.failure_id != record2.failure_id  # Each gets unique ID

    def test_timestamp_preserved(self, minimal_record_data: dict) -> None:
        """Test that timestamp is properly stored."""
        record = ModelFailureRecord(**minimal_record_data)

        assert record.timestamp == minimal_record_data["timestamp"]
        assert isinstance(record.timestamp, datetime)

    def test_default_values(self, minimal_record_data: dict) -> None:
        """Test default values for optional fields."""
        record = ModelFailureRecord(**minimal_record_data)

        assert record.model_used is None
        assert record.retry_attempt == 0
        assert record.recovery_action is None
        assert record.recovery_outcome is None
        assert record.should_remember is True

    def test_various_failure_types(self, minimal_record_data: dict) -> None:
        """Test all failure type enum values."""
        failure_types = list(EnumFailureType)
        for failure_type in failure_types:
            minimal_record_data["failure_type"] = failure_type
            record = ModelFailureRecord(**minimal_record_data)
            assert record.failure_type == failure_type

    def test_failure_type_from_string(self, minimal_record_data: dict) -> None:
        """Test that failure_type accepts string coercion."""
        minimal_record_data["failure_type"] = "validation_error"
        record = ModelFailureRecord(**minimal_record_data)
        assert record.failure_type == EnumFailureType.VALIDATION_ERROR


# ============================================================================
# Test: Immutability (Frozen Model)
# ============================================================================


class TestModelFailureRecordImmutability:
    """Tests for frozen model behavior."""

    def test_model_is_frozen(self, minimal_record_data: dict) -> None:
        """Test that the model is immutable."""
        record = ModelFailureRecord(**minimal_record_data)

        with pytest.raises(ValidationError):
            # NOTE: Intentionally testing frozen model mutation - mypy correctly flags assignment to frozen attr
            record.error_code = "DIFFERENT_001"  # type: ignore[misc]

    def test_cannot_modify_failure_id(self, minimal_record_data: dict) -> None:
        """Test that failure_id cannot be modified."""
        record = ModelFailureRecord(**minimal_record_data)

        with pytest.raises(ValidationError):
            # NOTE: Intentionally testing frozen model mutation - mypy correctly flags assignment to frozen attr
            record.failure_id = uuid4()  # type: ignore[misc]

    def test_cannot_modify_failure_type(self, minimal_record_data: dict) -> None:
        """Test that failure_type cannot be modified."""
        record = ModelFailureRecord(**minimal_record_data)

        with pytest.raises(ValidationError):
            # NOTE: Intentionally testing frozen model mutation - mypy correctly flags assignment to frozen attr
            record.failure_type = EnumFailureType.RATE_LIMIT  # type: ignore[misc]

    def test_cannot_modify_step_context(self, minimal_record_data: dict) -> None:
        """Test that step_context cannot be modified."""
        record = ModelFailureRecord(**minimal_record_data)

        with pytest.raises(ValidationError):
            # NOTE: Intentionally testing frozen model mutation - mypy correctly flags assignment to frozen attr
            record.step_context = "modified_context"  # type: ignore[misc]

    def test_cannot_modify_error_message(self, minimal_record_data: dict) -> None:
        """Test that error_message cannot be modified."""
        record = ModelFailureRecord(**minimal_record_data)

        with pytest.raises(ValidationError):
            # NOTE: Intentionally testing frozen model mutation - mypy correctly flags assignment to frozen attr
            record.error_message = "Modified message"  # type: ignore[misc]

    def test_cannot_modify_retry_attempt(self, minimal_record_data: dict) -> None:
        """Test that retry_attempt cannot be modified."""
        record = ModelFailureRecord(**minimal_record_data)

        with pytest.raises(ValidationError):
            # NOTE: Intentionally testing frozen model mutation - mypy correctly flags assignment to frozen attr
            record.retry_attempt = 99  # type: ignore[misc]

    def test_cannot_modify_should_remember(self, minimal_record_data: dict) -> None:
        """Test that should_remember cannot be modified."""
        record = ModelFailureRecord(**minimal_record_data)

        with pytest.raises(ValidationError):
            # NOTE: Intentionally testing frozen model mutation - mypy correctly flags assignment to frozen attr
            record.should_remember = False  # type: ignore[misc]


# ============================================================================
# Test: Field Validation
# ============================================================================


class TestModelFailureRecordValidation:
    """Tests for field validation constraints."""

    def test_naive_timestamp_rejected(self, minimal_record_data: dict) -> None:
        """Test that naive datetime (without tzinfo) is rejected."""
        minimal_record_data["timestamp"] = datetime(2025, 1, 1, 12, 0, 0)  # No tzinfo

        with pytest.raises(ValidationError) as exc_info:
            ModelFailureRecord(**minimal_record_data)

        assert "timestamp" in str(exc_info.value)
        assert "timezone-aware" in str(exc_info.value)

    def test_timezone_aware_timestamp_accepted(self, minimal_record_data: dict) -> None:
        """Test that timezone-aware datetime is accepted."""
        minimal_record_data["timestamp"] = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        record = ModelFailureRecord(**minimal_record_data)
        assert record.timestamp.tzinfo is not None

    def test_empty_step_context_rejected(self, minimal_record_data: dict) -> None:
        """Test that empty step_context is rejected."""
        minimal_record_data["step_context"] = ""

        with pytest.raises(ValidationError) as exc_info:
            ModelFailureRecord(**minimal_record_data)

        assert "step_context" in str(exc_info.value)

    def test_empty_error_code_rejected(self, minimal_record_data: dict) -> None:
        """Test that empty error_code is rejected."""
        minimal_record_data["error_code"] = ""

        with pytest.raises(ValidationError) as exc_info:
            ModelFailureRecord(**minimal_record_data)

        assert "error_code" in str(exc_info.value)

    def test_empty_error_message_rejected(self, minimal_record_data: dict) -> None:
        """Test that empty error_message is rejected."""
        minimal_record_data["error_message"] = ""

        with pytest.raises(ValidationError) as exc_info:
            ModelFailureRecord(**minimal_record_data)

        assert "error_message" in str(exc_info.value)

    def test_retry_attempt_must_be_non_negative(
        self, minimal_record_data: dict
    ) -> None:
        """Test that retry_attempt rejects negative values."""
        minimal_record_data["retry_attempt"] = -1

        with pytest.raises(ValidationError) as exc_info:
            ModelFailureRecord(**minimal_record_data)

        assert "retry_attempt" in str(exc_info.value)

    def test_retry_attempt_zero_accepted(self, minimal_record_data: dict) -> None:
        """Test that retry_attempt accepts zero (first attempt)."""
        minimal_record_data["retry_attempt"] = 0

        record = ModelFailureRecord(**minimal_record_data)

        assert record.retry_attempt == 0

    def test_large_retry_attempt_accepted(self, minimal_record_data: dict) -> None:
        """Test that large retry_attempt values are accepted."""
        minimal_record_data["retry_attempt"] = 100

        record = ModelFailureRecord(**minimal_record_data)

        assert record.retry_attempt == 100

    def test_missing_required_field_timestamp(self) -> None:
        """Test that missing timestamp raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelFailureRecord(
                failure_type=EnumFailureType.TIMEOUT,
                step_context="test",
                error_code="ERR_001",
                error_message="Test error",
            )
        assert "timestamp" in str(exc_info.value)

    def test_missing_required_field_failure_type(
        self, minimal_record_data: dict
    ) -> None:
        """Test that missing failure_type raises ValidationError."""
        del minimal_record_data["failure_type"]
        with pytest.raises(ValidationError) as exc_info:
            ModelFailureRecord(**minimal_record_data)
        assert "failure_type" in str(exc_info.value)

    def test_missing_required_field_step_context(
        self, minimal_record_data: dict
    ) -> None:
        """Test that missing step_context raises ValidationError."""
        del minimal_record_data["step_context"]
        with pytest.raises(ValidationError) as exc_info:
            ModelFailureRecord(**minimal_record_data)
        assert "step_context" in str(exc_info.value)

    def test_missing_required_field_error_code(self, minimal_record_data: dict) -> None:
        """Test that missing error_code raises ValidationError."""
        del minimal_record_data["error_code"]
        with pytest.raises(ValidationError) as exc_info:
            ModelFailureRecord(**minimal_record_data)
        assert "error_code" in str(exc_info.value)

    def test_missing_required_field_error_message(
        self, minimal_record_data: dict
    ) -> None:
        """Test that missing error_message raises ValidationError."""
        del minimal_record_data["error_message"]
        with pytest.raises(ValidationError) as exc_info:
            ModelFailureRecord(**minimal_record_data)
        assert "error_message" in str(exc_info.value)

    def test_invalid_recovery_outcome_rejected(self, minimal_record_data: dict) -> None:
        """Test that invalid recovery_outcome literal is rejected."""
        minimal_record_data["recovery_outcome"] = "invalid_outcome"

        with pytest.raises(ValidationError) as exc_info:
            ModelFailureRecord(**minimal_record_data)

        assert "recovery_outcome" in str(exc_info.value)


# ============================================================================
# Test: Recovery Outcome Literals
# ============================================================================


class TestModelFailureRecordRecoveryOutcome:
    """Tests for recovery_outcome literal values."""

    def test_recovery_outcome_success(self, minimal_record_data: dict) -> None:
        """Test that 'success' is accepted."""
        minimal_record_data["recovery_outcome"] = "success"
        record = ModelFailureRecord(**minimal_record_data)
        assert record.recovery_outcome == "success"

    def test_recovery_outcome_failure(self, minimal_record_data: dict) -> None:
        """Test that 'failure' is accepted."""
        minimal_record_data["recovery_outcome"] = "failure"
        record = ModelFailureRecord(**minimal_record_data)
        assert record.recovery_outcome == "failure"

    def test_recovery_outcome_pending(self, minimal_record_data: dict) -> None:
        """Test that 'pending' is accepted."""
        minimal_record_data["recovery_outcome"] = "pending"
        record = ModelFailureRecord(**minimal_record_data)
        assert record.recovery_outcome == "pending"

    def test_recovery_outcome_none(self, minimal_record_data: dict) -> None:
        """Test that None is accepted (default)."""
        record = ModelFailureRecord(**minimal_record_data)
        assert record.recovery_outcome is None


# ============================================================================
# Test: Should Remember Flag
# ============================================================================


class TestModelFailureRecordShouldRemember:
    """Tests for should_remember flag."""

    def test_should_remember_default_true(self, minimal_record_data: dict) -> None:
        """Test that should_remember defaults to True."""
        record = ModelFailureRecord(**minimal_record_data)
        assert record.should_remember is True

    def test_should_remember_explicit_true(self, minimal_record_data: dict) -> None:
        """Test setting should_remember to True explicitly."""
        minimal_record_data["should_remember"] = True
        record = ModelFailureRecord(**minimal_record_data)
        assert record.should_remember is True

    def test_should_remember_explicit_false(self, minimal_record_data: dict) -> None:
        """Test setting should_remember to False."""
        minimal_record_data["should_remember"] = False
        record = ModelFailureRecord(**minimal_record_data)
        assert record.should_remember is False


# ============================================================================
# Test: Serialization
# ============================================================================


class TestModelFailureRecordSerialization:
    """Tests for serialization and deserialization."""

    def test_model_dump(self, minimal_record_data: dict) -> None:
        """Test serialization to dictionary."""
        record = ModelFailureRecord(**minimal_record_data)
        data = record.model_dump()

        assert "failure_id" in data
        assert "timestamp" in data
        assert "failure_type" in data
        assert data["step_context"] == "code_generation"
        assert data["error_code"] == "TIMEOUT_001"

    def test_model_dump_json(self, minimal_record_data: dict) -> None:
        """Test serialization to JSON string."""
        record = ModelFailureRecord(**minimal_record_data)
        json_str = record.model_dump_json()

        assert isinstance(json_str, str)
        assert "code_generation" in json_str
        assert "TIMEOUT_001" in json_str

    def test_round_trip_serialization(self, full_record_data: dict) -> None:
        """Test that model survives serialization round-trip."""
        original = ModelFailureRecord(**full_record_data)
        data = original.model_dump()
        restored = ModelFailureRecord(**data)

        assert original.failure_id == restored.failure_id
        assert original.failure_type == restored.failure_type
        assert original.step_context == restored.step_context
        assert original.error_code == restored.error_code
        assert original.retry_attempt == restored.retry_attempt

    def test_json_round_trip_serialization(self, full_record_data: dict) -> None:
        """Test JSON serialization and deserialization roundtrip."""
        original = ModelFailureRecord(**full_record_data)

        json_str = original.model_dump_json()
        restored = ModelFailureRecord.model_validate_json(json_str)

        assert original.failure_id == restored.failure_id
        assert original.timestamp == restored.timestamp
        assert original.failure_type == restored.failure_type
        assert original.step_context == restored.step_context
        assert original.error_code == restored.error_code
        assert original.error_message == restored.error_message
        assert original.model_used == restored.model_used
        assert original.retry_attempt == restored.retry_attempt
        assert original.recovery_action == restored.recovery_action
        assert original.recovery_outcome == restored.recovery_outcome
        assert original.should_remember == restored.should_remember

    def test_model_dump_contains_all_fields(self, full_record_data: dict) -> None:
        """Test model_dump contains all expected fields."""
        record = ModelFailureRecord(**full_record_data)
        data = record.model_dump()

        expected_fields = [
            "failure_id",
            "timestamp",
            "failure_type",
            "step_context",
            "error_code",
            "error_message",
            "model_used",
            "retry_attempt",
            "recovery_action",
            "recovery_outcome",
            "should_remember",
        ]
        for field in expected_fields:
            assert field in data

    def test_model_validate_from_dict(self, full_record_data: dict) -> None:
        """Test model validation from dictionary."""
        record = ModelFailureRecord.model_validate(full_record_data)

        assert record.failure_id == full_record_data["failure_id"]
        assert record.step_context == full_record_data["step_context"]


# ============================================================================
# Test: Edge Cases
# ============================================================================


class TestModelFailureRecordEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_step_context_with_special_characters(
        self, minimal_record_data: dict
    ) -> None:
        """Test step_context with special characters."""
        special_contexts = [
            "code-generation",
            "code_generation",
            "code.generation",
            "code:generation",
            "code generation",
            "step/with/slashes",
        ]
        for context in special_contexts:
            minimal_record_data["step_context"] = context
            record = ModelFailureRecord(**minimal_record_data)
            assert record.step_context == context

    def test_error_code_with_special_characters(
        self, minimal_record_data: dict
    ) -> None:
        """Test error_code with special characters."""
        special_codes = [
            "ERR-001",
            "ERR_001",
            "ERR.001",
            "ERR:001",
            "ERROR_TIMEOUT_123",
        ]
        for code in special_codes:
            minimal_record_data["error_code"] = code
            record = ModelFailureRecord(**minimal_record_data)
            assert record.error_code == code

    def test_long_error_message(self, minimal_record_data: dict) -> None:
        """Test handling of long error messages."""
        long_message = "Error: " + "x" * 10000
        minimal_record_data["error_message"] = long_message

        record = ModelFailureRecord(**minimal_record_data)

        assert record.error_message == long_message

    def test_model_equality(self, minimal_record_data: dict) -> None:
        """Test model equality comparison with same failure_id."""
        failure_id = uuid4()
        minimal_record_data["failure_id"] = failure_id
        record1 = ModelFailureRecord(**minimal_record_data)
        record2 = ModelFailureRecord(**minimal_record_data)

        assert record1 == record2

    def test_model_inequality_different_failure_id(
        self, minimal_record_data: dict
    ) -> None:
        """Test model inequality when failure_ids differ."""
        record1 = ModelFailureRecord(**minimal_record_data)
        record2 = ModelFailureRecord(**minimal_record_data)

        # Different auto-generated failure_ids
        assert record1 != record2

    def test_str_representation(self, minimal_record_data: dict) -> None:
        """Test __str__ method returns meaningful string."""
        record = ModelFailureRecord(**minimal_record_data)
        str_repr = str(record)

        assert isinstance(str_repr, str)
        assert "timeout" in str_repr or "FailureRecord" in str_repr

    def test_repr_representation(self, minimal_record_data: dict) -> None:
        """Test __repr__ method returns string with class name."""
        record = ModelFailureRecord(**minimal_record_data)
        repr_str = repr(record)

        assert isinstance(repr_str, str)
        assert "ModelFailureRecord" in repr_str

    def test_hash_consistency_for_same_data(self, minimal_record_data: dict) -> None:
        """Test that frozen model is hashable and consistent."""
        failure_id = uuid4()
        minimal_record_data["failure_id"] = failure_id

        record1 = ModelFailureRecord(**minimal_record_data)
        record2 = ModelFailureRecord(**minimal_record_data)

        # Frozen models should be hashable
        assert hash(record1) == hash(record2)

    def test_can_use_as_dict_key(self, minimal_record_data: dict) -> None:
        """Test that frozen model can be used as dictionary key."""
        failure_id = uuid4()
        minimal_record_data["failure_id"] = failure_id

        record = ModelFailureRecord(**minimal_record_data)

        # Should be usable as dict key
        test_dict = {record: "value"}
        assert test_dict[record] == "value"

    def test_can_add_to_set(self, minimal_record_data: dict) -> None:
        """Test that frozen model can be added to set."""
        failure_id = uuid4()
        minimal_record_data["failure_id"] = failure_id

        record1 = ModelFailureRecord(**minimal_record_data)
        record2 = ModelFailureRecord(**minimal_record_data)

        # Should be usable in sets
        test_set = {record1, record2}
        assert len(test_set) == 1  # Same failure_id, same hash

    def test_failure_type_is_retryable_integration(
        self, minimal_record_data: dict
    ) -> None:
        """Test integration with EnumFailureType.is_retryable()."""
        minimal_record_data["failure_type"] = EnumFailureType.TIMEOUT
        record = ModelFailureRecord(**minimal_record_data)
        assert record.failure_type.is_retryable() is True

        minimal_record_data["failure_type"] = EnumFailureType.INVARIANT_VIOLATION
        record = ModelFailureRecord(**minimal_record_data)
        assert record.failure_type.is_retryable() is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
