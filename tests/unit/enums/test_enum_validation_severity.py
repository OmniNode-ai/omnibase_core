"""
Unit tests for EnumSeverity.

EnumSeverity provides 5 severity levels:
DEBUG, INFO, WARNING, ERROR, CRITICAL

Tests all aspects of the severity enum including:
- Enum value validation
- String representation
- JSON serialization compatibility
- Pydantic integration
- Enum iteration and membership
- Severity level ordering
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums import EnumSeverity


@pytest.mark.unit
class TestEnumSeverity:
    """Test cases for EnumSeverity."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "DEBUG": "debug",
            "INFO": "info",
            "WARNING": "warning",
            "ERROR": "error",
            "CRITICAL": "critical",
        }

        for name, value in expected_values.items():
            severity = getattr(EnumSeverity, name)
            assert severity.value == value

    def test_string_inheritance(self):
        """Test that enum inherits from str."""
        assert isinstance(EnumSeverity.INFO, str)
        assert EnumSeverity.INFO == "info"
        assert isinstance(EnumSeverity.ERROR, str)
        assert EnumSeverity.ERROR == "error"

    def test_string_representation(self):
        """Test string representation of enum values."""
        # Enum inherits from str, so value is accessible as string
        assert EnumSeverity.DEBUG.value == "debug"
        assert EnumSeverity.INFO.value == "info"
        assert EnumSeverity.WARNING.value == "warning"
        assert EnumSeverity.ERROR.value == "error"
        assert EnumSeverity.CRITICAL.value == "critical"

    def test_enum_equality(self):
        """Test enum equality comparison."""
        assert EnumSeverity.INFO == EnumSeverity.INFO
        assert EnumSeverity.ERROR != EnumSeverity.WARNING
        assert EnumSeverity.CRITICAL == EnumSeverity.CRITICAL

    def test_enum_membership(self):
        """Test enum membership checking."""
        all_severities = [
            EnumSeverity.DEBUG,
            EnumSeverity.INFO,
            EnumSeverity.WARNING,
            EnumSeverity.ERROR,
            EnumSeverity.CRITICAL,
        ]

        for severity in all_severities:
            assert severity in EnumSeverity

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        severities = list(EnumSeverity)
        assert len(severities) == 5

        severity_values = [s.value for s in severities]
        expected_values = ["debug", "info", "warning", "error", "critical"]

        assert set(severity_values) == set(expected_values)

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        # Test direct serialization
        severity = EnumSeverity.ERROR
        json_str = json.dumps(severity, default=str)
        assert json_str == '"error"'

        # Test in dictionary
        data = {"severity": EnumSeverity.WARNING}
        json_str = json.dumps(data, default=str)
        assert '"severity": "warning"' in json_str

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class ValidationResult(BaseModel):
            severity: EnumSeverity

        # Test valid enum assignment
        result = ValidationResult(severity=EnumSeverity.ERROR)
        assert result.severity == EnumSeverity.ERROR

        # Test string assignment (should work due to str inheritance)
        result = ValidationResult(severity="warning")
        assert result.severity == EnumSeverity.WARNING

        # Test invalid value should raise ValidationError
        with pytest.raises(ValidationError):
            ValidationResult(severity="invalid_severity")

    def test_pydantic_serialization(self):
        """Test Pydantic model serialization."""

        class ValidationResult(BaseModel):
            severity: EnumSeverity

        result = ValidationResult(severity=EnumSeverity.CRITICAL)

        # Test dict serialization
        result_dict = result.model_dump()
        assert result_dict == {"severity": "critical"}

        # Test JSON serialization
        json_str = result.model_dump_json()
        assert json_str == '{"severity":"critical"}'

    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Test case sensitivity (should be case-sensitive)
        assert EnumSeverity.ERROR.value == "error"
        assert EnumSeverity.ERROR.value != "ERROR"
        assert EnumSeverity.ERROR.value != "Error"

        # Test that we can't create invalid enum values
        with pytest.raises((AttributeError, ValueError)):
            _ = EnumSeverity("invalid_value")

    def test_severity_ordering(self):
        """Test that severity levels follow expected ordering."""
        # Define expected order from least to most severe
        expected_order = [
            EnumSeverity.DEBUG,
            EnumSeverity.INFO,
            EnumSeverity.WARNING,
            EnumSeverity.ERROR,
            EnumSeverity.CRITICAL,
        ]

        # Verify order matches declaration order
        actual_order = list(EnumSeverity)
        assert actual_order == expected_order

    def test_severity_semantics(self):
        """Test semantic meaning of severity levels."""
        # DEBUG: debug-level messages
        assert EnumSeverity.DEBUG.value == "debug"

        # INFO: informational messages
        assert EnumSeverity.INFO.value == "info"

        # WARNING: potential issues
        assert EnumSeverity.WARNING.value == "warning"

        # ERROR: validation failures
        assert EnumSeverity.ERROR.value == "error"

        # CRITICAL: severe/unrecoverable failures
        assert EnumSeverity.CRITICAL.value == "critical"

    def test_all_values_unique(self):
        """Test that all enum values are unique."""
        values = [s.value for s in EnumSeverity]
        assert len(values) == len(set(values))

    def test_enum_names_uppercase(self):
        """Test that all enum names follow UPPERCASE convention."""
        for severity in EnumSeverity:
            assert severity.name.isupper()

    def test_enum_values_lowercase(self):
        """Test that all enum values are lowercase."""
        for severity in EnumSeverity:
            assert severity.value.islower()

    def test_error_levels(self):
        """Test classification of error severity levels."""
        # Non-blocking severities
        non_blocking = [
            EnumSeverity.DEBUG,
            EnumSeverity.INFO,
            EnumSeverity.WARNING,
        ]
        for severity in non_blocking:
            assert severity in EnumSeverity

        # Blocking severities
        blocking = [
            EnumSeverity.ERROR,
            EnumSeverity.CRITICAL,
        ]
        for severity in blocking:
            assert severity in EnumSeverity

    def test_numeric_level(self):
        """Test numeric level property for severity comparison."""
        # Verify levels are compatible with Python logging (10, 20, 30, 40, 50)
        assert EnumSeverity.DEBUG.numeric_level == 10
        assert EnumSeverity.INFO.numeric_level == 20
        assert EnumSeverity.WARNING.numeric_level == 30
        assert EnumSeverity.ERROR.numeric_level == 40
        assert EnumSeverity.CRITICAL.numeric_level == 50

        # Verify ordering
        assert EnumSeverity.DEBUG.numeric_level < EnumSeverity.INFO.numeric_level
        assert EnumSeverity.INFO.numeric_level < EnumSeverity.WARNING.numeric_level
        assert EnumSeverity.WARNING.numeric_level < EnumSeverity.ERROR.numeric_level
        assert EnumSeverity.ERROR.numeric_level < EnumSeverity.CRITICAL.numeric_level

    def test_is_error_or_above(self):
        """Test is_error_or_above() helper method."""
        # Below error level
        assert not EnumSeverity.DEBUG.is_error_or_above()
        assert not EnumSeverity.INFO.is_error_or_above()
        assert not EnumSeverity.WARNING.is_error_or_above()

        # Error level and above
        assert EnumSeverity.ERROR.is_error_or_above()
        assert EnumSeverity.CRITICAL.is_error_or_above()

    def test_is_warning_or_above(self):
        """Test is_warning_or_above() helper method."""
        # Below warning level
        assert not EnumSeverity.DEBUG.is_warning_or_above()
        assert not EnumSeverity.INFO.is_warning_or_above()

        # Warning level and above
        assert EnumSeverity.WARNING.is_warning_or_above()
        assert EnumSeverity.ERROR.is_warning_or_above()
        assert EnumSeverity.CRITICAL.is_warning_or_above()

    def test_from_string(self):
        """Test from_string() class method for case-insensitive conversion."""
        # Test lowercase (exact match)
        assert EnumSeverity.from_string("debug") == EnumSeverity.DEBUG
        assert EnumSeverity.from_string("info") == EnumSeverity.INFO
        assert EnumSeverity.from_string("warning") == EnumSeverity.WARNING
        assert EnumSeverity.from_string("error") == EnumSeverity.ERROR
        assert EnumSeverity.from_string("critical") == EnumSeverity.CRITICAL

        # Test uppercase (case-insensitive)
        assert EnumSeverity.from_string("DEBUG") == EnumSeverity.DEBUG
        assert EnumSeverity.from_string("INFO") == EnumSeverity.INFO
        assert EnumSeverity.from_string("WARNING") == EnumSeverity.WARNING
        assert EnumSeverity.from_string("ERROR") == EnumSeverity.ERROR
        assert EnumSeverity.from_string("CRITICAL") == EnumSeverity.CRITICAL

        # Test mixed case
        assert EnumSeverity.from_string("Warning") == EnumSeverity.WARNING
        assert EnumSeverity.from_string("Error") == EnumSeverity.ERROR

        # Test with whitespace
        assert EnumSeverity.from_string("  error  ") == EnumSeverity.ERROR
        assert EnumSeverity.from_string("\twarning\n") == EnumSeverity.WARNING

    def test_from_string_invalid(self):
        """Test from_string() raises ValueError for invalid input."""
        with pytest.raises(ValueError, match="Unknown severity level"):
            EnumSeverity.from_string("invalid")

        with pytest.raises(ValueError, match="Unknown severity level"):
            EnumSeverity.from_string("fatal")  # Not a valid EnumSeverity value

        with pytest.raises(ValueError, match="Unknown severity level"):
            EnumSeverity.from_string("")
