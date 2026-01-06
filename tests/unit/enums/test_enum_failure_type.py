"""Unit tests for EnumFailureType.

Tests serialization/deserialization and basic enum behavior
for the failure classification type enum.
"""

import json

import pytest

from omnibase_core.enums.enum_failure_type import EnumFailureType


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
        ("member", "expected_value"),
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
    def test_serialization(self, member: EnumFailureType, expected_value: str) -> None:
        """Test enum serializes to expected string value."""
        assert member.value == expected_value
        assert str(member.value) == expected_value

    @pytest.mark.parametrize(
        "value",
        [
            "invariant_violation",
            "timeout",
            "model_error",
            "cost_exceeded",
            "validation_error",
            "external_service",
            "rate_limit",
            "unknown",
        ],
    )
    def test_deserialization(self, value: str) -> None:
        """Test enum deserializes from string value."""
        result = EnumFailureType(value)
        assert result.value == value

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
