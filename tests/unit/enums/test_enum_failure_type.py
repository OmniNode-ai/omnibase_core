"""Unit tests for EnumFailureType.

Tests serialization/deserialization and basic enum behavior
for the failure classification type enum.
"""

import json

import pytest

from omnibase_core.enums.enum_failure_type import EnumFailureType


@pytest.mark.unit
class TestEnumFailureType:
    """Tests for EnumFailureType enum."""

    def test_all_values_defined(self) -> None:
        """Verify all 8 expected failure types are defined."""
        expected_values = {
            "invariant_violation",
            "timeout",
            "model_error",
            "cost_exceeded",
            "validation_error",
            "external_service",
            "rate_limit",
            "unknown",
        }
        actual_values = {member.value for member in EnumFailureType}
        assert actual_values == expected_values
        assert len(EnumFailureType) == 8

    def test_string_enum_inheritance(self) -> None:
        """Verify enum inherits from str for JSON serialization."""
        assert isinstance(EnumFailureType.TIMEOUT, str)
        assert EnumFailureType.TIMEOUT == "timeout"

    @pytest.mark.parametrize(
        ("member", "value"),
        [
            (EnumFailureType.INVARIANT_VIOLATION, "invariant_violation"),
            (EnumFailureType.TIMEOUT, "timeout"),
            (EnumFailureType.MODEL_ERROR, "model_error"),
            (EnumFailureType.COST_EXCEEDED, "cost_exceeded"),
            (EnumFailureType.VALIDATION_ERROR, "validation_error"),
            (EnumFailureType.EXTERNAL_SERVICE, "external_service"),
            (EnumFailureType.RATE_LIMIT, "rate_limit"),
            (EnumFailureType.UNKNOWN, "unknown"),
        ],
    )
    def test_serialization_roundtrip(self, member: EnumFailureType, value: str) -> None:
        """Test enum serialization/deserialization round-trip."""
        # Serialization: member.value equals expected string
        assert member.value == value
        # Direct string comparison (str subclass)
        assert member == value
        # Deserialization: string value constructs back to member
        assert EnumFailureType(value) == member

    def test_invalid_value_raises(self) -> None:
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumFailureType("invalid_failure")

    def test_json_serialization(self) -> None:
        """Test JSON serialization/deserialization."""
        data = {"failure_type": EnumFailureType.TIMEOUT}
        json_str = json.dumps(data)
        assert '"timeout"' in json_str

        # Deserialize
        parsed = json.loads(json_str)
        result = EnumFailureType(parsed["failure_type"])
        assert result == EnumFailureType.TIMEOUT

    def test_unknown_escape_hatch(self) -> None:
        """Test UNKNOWN value exists as escape hatch for unclassified failures."""
        assert EnumFailureType.UNKNOWN.value == "unknown"
        # Can be used directly
        unknown = EnumFailureType("unknown")
        assert unknown == EnumFailureType.UNKNOWN

    def test_hashable(self) -> None:
        """Test enum values are hashable for use in sets/dicts."""
        failure_set = {EnumFailureType.TIMEOUT, EnumFailureType.RATE_LIMIT}
        assert len(failure_set) == 2
        assert EnumFailureType.TIMEOUT in failure_set

    def test_equality(self) -> None:
        """Test enum equality comparisons."""
        assert EnumFailureType.TIMEOUT == EnumFailureType.TIMEOUT
        assert EnumFailureType.TIMEOUT == "timeout"
        assert EnumFailureType.TIMEOUT != EnumFailureType.RATE_LIMIT

    def test_is_valid_with_valid_values(self) -> None:
        """Test is_valid returns True for valid enum values."""
        assert EnumFailureType.is_valid("timeout") is True
        assert EnumFailureType.is_valid("rate_limit") is True
        assert EnumFailureType.is_valid("unknown") is True

    def test_is_valid_with_invalid_values(self) -> None:
        """Test is_valid returns False for invalid values."""
        assert EnumFailureType.is_valid("invalid_type") is False
        assert EnumFailureType.is_valid("") is False
        assert EnumFailureType.is_valid("TIMEOUT") is False  # Case-sensitive

    def test_is_retryable(self) -> None:
        """Test is_retryable identifies failures that may succeed on retry."""
        # Retryable failures
        assert EnumFailureType.TIMEOUT.is_retryable() is True
        assert EnumFailureType.RATE_LIMIT.is_retryable() is True
        assert EnumFailureType.EXTERNAL_SERVICE.is_retryable() is True
        assert EnumFailureType.MODEL_ERROR.is_retryable() is True
        # Non-retryable failures
        assert EnumFailureType.INVARIANT_VIOLATION.is_retryable() is False
        assert EnumFailureType.VALIDATION_ERROR.is_retryable() is False
        assert EnumFailureType.COST_EXCEEDED.is_retryable() is False

    def test_is_resource_related(self) -> None:
        """Test is_resource_related identifies resource constraint failures."""
        # Resource-related failures
        assert EnumFailureType.COST_EXCEEDED.is_resource_related() is True
        assert EnumFailureType.RATE_LIMIT.is_resource_related() is True
        assert EnumFailureType.TIMEOUT.is_resource_related() is True
        # Non-resource failures
        assert EnumFailureType.INVARIANT_VIOLATION.is_resource_related() is False
        assert EnumFailureType.VALIDATION_ERROR.is_resource_related() is False
        assert EnumFailureType.MODEL_ERROR.is_resource_related() is False
