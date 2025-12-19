"""
Unit tests for EnumValidationSeverity.

Tests all aspects of the validation severity enum including:
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

from omnibase_core.enums.enum_validation_severity import EnumValidationSeverity


@pytest.mark.unit
class TestEnumValidationSeverity:
    """Test cases for EnumValidationSeverity."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "INFO": "info",
            "WARNING": "warning",
            "ERROR": "error",
            "CRITICAL": "critical",
        }

        for name, value in expected_values.items():
            severity = getattr(EnumValidationSeverity, name)
            assert severity.value == value

    def test_string_inheritance(self):
        """Test that enum inherits from str."""
        assert isinstance(EnumValidationSeverity.INFO, str)
        assert EnumValidationSeverity.INFO == "info"
        assert isinstance(EnumValidationSeverity.ERROR, str)
        assert EnumValidationSeverity.ERROR == "error"

    def test_string_representation(self):
        """Test string representation of enum values."""
        # Enum inherits from str, so value is accessible as string
        assert EnumValidationSeverity.INFO.value == "info"
        assert EnumValidationSeverity.WARNING.value == "warning"
        assert EnumValidationSeverity.ERROR.value == "error"
        assert EnumValidationSeverity.CRITICAL.value == "critical"

    def test_enum_equality(self):
        """Test enum equality comparison."""
        assert EnumValidationSeverity.INFO == EnumValidationSeverity.INFO
        assert EnumValidationSeverity.ERROR != EnumValidationSeverity.WARNING
        assert EnumValidationSeverity.CRITICAL == EnumValidationSeverity.CRITICAL

    def test_enum_membership(self):
        """Test enum membership checking."""
        all_severities = [
            EnumValidationSeverity.INFO,
            EnumValidationSeverity.WARNING,
            EnumValidationSeverity.ERROR,
            EnumValidationSeverity.CRITICAL,
        ]

        for severity in all_severities:
            assert severity in EnumValidationSeverity

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        severities = list(EnumValidationSeverity)
        assert len(severities) == 4

        severity_values = [s.value for s in severities]
        expected_values = ["info", "warning", "error", "critical"]

        assert set(severity_values) == set(expected_values)

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        # Test direct serialization
        severity = EnumValidationSeverity.ERROR
        json_str = json.dumps(severity, default=str)
        assert json_str == '"error"'

        # Test in dictionary
        data = {"severity": EnumValidationSeverity.WARNING}
        json_str = json.dumps(data, default=str)
        assert '"severity": "warning"' in json_str

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class ValidationResult(BaseModel):
            severity: EnumValidationSeverity

        # Test valid enum assignment
        result = ValidationResult(severity=EnumValidationSeverity.ERROR)
        assert result.severity == EnumValidationSeverity.ERROR

        # Test string assignment (should work due to str inheritance)
        result = ValidationResult(severity="warning")
        assert result.severity == EnumValidationSeverity.WARNING

        # Test invalid value should raise ValidationError
        with pytest.raises(ValidationError):
            ValidationResult(severity="invalid_severity")

    def test_pydantic_serialization(self):
        """Test Pydantic model serialization."""

        class ValidationResult(BaseModel):
            severity: EnumValidationSeverity

        result = ValidationResult(severity=EnumValidationSeverity.CRITICAL)

        # Test dict serialization
        result_dict = result.model_dump()
        assert result_dict == {"severity": "critical"}

        # Test JSON serialization
        json_str = result.model_dump_json()
        assert json_str == '{"severity":"critical"}'

    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Test case sensitivity (should be case-sensitive)
        assert EnumValidationSeverity.ERROR.value == "error"
        assert EnumValidationSeverity.ERROR.value != "ERROR"
        assert EnumValidationSeverity.ERROR.value != "Error"

        # Test that we can't create invalid enum values
        with pytest.raises((ValueError, AttributeError)):
            _ = EnumValidationSeverity("invalid_value")

    def test_severity_ordering(self):
        """Test that severity levels follow expected ordering."""
        # Define expected order from least to most severe
        expected_order = [
            EnumValidationSeverity.INFO,
            EnumValidationSeverity.WARNING,
            EnumValidationSeverity.ERROR,
            EnumValidationSeverity.CRITICAL,
        ]

        # Verify order matches declaration order
        actual_order = list(EnumValidationSeverity)
        assert actual_order == expected_order

    def test_severity_semantics(self):
        """Test semantic meaning of severity levels."""
        # INFO: informational messages
        assert EnumValidationSeverity.INFO.value == "info"

        # WARNING: potential issues
        assert EnumValidationSeverity.WARNING.value == "warning"

        # ERROR: validation failures
        assert EnumValidationSeverity.ERROR.value == "error"

        # CRITICAL: severe validation failures
        assert EnumValidationSeverity.CRITICAL.value == "critical"

    def test_all_values_unique(self):
        """Test that all enum values are unique."""
        values = [s.value for s in EnumValidationSeverity]
        assert len(values) == len(set(values))

    def test_enum_names_uppercase(self):
        """Test that all enum names follow UPPERCASE convention."""
        for severity in EnumValidationSeverity:
            assert severity.name.isupper()

    def test_enum_values_lowercase(self):
        """Test that all enum values are lowercase."""
        for severity in EnumValidationSeverity:
            assert severity.value.islower()

    def test_error_levels(self):
        """Test classification of error severity levels."""
        # Non-blocking severities
        non_blocking = [
            EnumValidationSeverity.INFO,
            EnumValidationSeverity.WARNING,
        ]
        for severity in non_blocking:
            assert severity in EnumValidationSeverity

        # Blocking severities
        blocking = [
            EnumValidationSeverity.ERROR,
            EnumValidationSeverity.CRITICAL,
        ]
        for severity in blocking:
            assert severity in EnumValidationSeverity


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
