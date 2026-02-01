"""Unit tests for ModelLabelViolation."""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_label_violation_type import EnumLabelViolationType
from omnibase_core.models.observability.model_label_violation import ModelLabelViolation


class TestModelLabelViolation:
    """Tests for ModelLabelViolation model."""

    def test_create_forbidden_key_violation(self) -> None:
        """Test creating a forbidden key violation."""
        violation = ModelLabelViolation(
            violation_type=EnumLabelViolationType.FORBIDDEN_KEY,
            key="envelope_id",
            value="abc123",
            message="Label key 'envelope_id' is forbidden",
        )
        assert violation.violation_type == EnumLabelViolationType.FORBIDDEN_KEY
        assert violation.key == "envelope_id"
        assert violation.value == "abc123"
        assert "forbidden" in violation.message

    def test_create_key_not_allowed_violation(self) -> None:
        """Test creating a key not allowed violation."""
        violation = ModelLabelViolation(
            violation_type=EnumLabelViolationType.KEY_NOT_ALLOWED,
            key="unknown_key",
            message="Label key 'unknown_key' is not in allowed list",
        )
        assert violation.violation_type == EnumLabelViolationType.KEY_NOT_ALLOWED
        assert violation.key == "unknown_key"
        assert violation.value is None

    def test_create_value_too_long_violation(self) -> None:
        """Test creating a value too long violation."""
        long_value = "x" * 200
        violation = ModelLabelViolation(
            violation_type=EnumLabelViolationType.VALUE_TOO_LONG,
            key="description",
            value=long_value,
            message="Value exceeds max length",
        )
        assert violation.violation_type == EnumLabelViolationType.VALUE_TOO_LONG
        assert violation.value == long_value

    def test_required_fields(self) -> None:
        """Test that required fields are enforced."""
        with pytest.raises(ValidationError):
            ModelLabelViolation(key="test", message="test")  # type: ignore[call-arg]

        with pytest.raises(ValidationError):
            ModelLabelViolation(  # type: ignore[call-arg]
                violation_type=EnumLabelViolationType.FORBIDDEN_KEY, message="test"
            )

        with pytest.raises(ValidationError):
            ModelLabelViolation(  # type: ignore[call-arg]
                violation_type=EnumLabelViolationType.FORBIDDEN_KEY, key="test"
            )

    def test_model_is_frozen(self) -> None:
        """Test that model is immutable."""
        violation = ModelLabelViolation(
            violation_type=EnumLabelViolationType.FORBIDDEN_KEY,
            key="test",
            message="test",
        )
        with pytest.raises(ValidationError):
            violation.key = "changed"  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelLabelViolation(
                violation_type=EnumLabelViolationType.FORBIDDEN_KEY,
                key="test",
                message="test",
                extra="value",  # type: ignore[call-arg]
            )
        assert "extra" in str(exc_info.value).lower()
