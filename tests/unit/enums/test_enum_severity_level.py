"""
Unit tests for EnumSeverityLevel.

Tests all aspects of the severity level enum including:
- Enum value validation
- String conversion and alias handling
- Numeric level comparison
- Level categorization methods
- String representation
- JSON serialization compatibility
- Pydantic integration
- RFC 5424 compliance
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_severity_level import EnumSeverityLevel


class TestEnumSeverityLevel:
    """Test cases for EnumSeverityLevel."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            # Standard severity levels
            "EMERGENCY": "emergency",
            "ALERT": "alert",
            "CRITICAL": "critical",
            "ERROR": "error",
            "WARNING": "warning",
            "NOTICE": "notice",
            "INFO": "info",
            "DEBUG": "debug",
            # Additional common levels
            "TRACE": "trace",
            "FATAL": "fatal",
            "WARN": "warn",
        }

        for name, value in expected_values.items():
            level = getattr(EnumSeverityLevel, name)
            assert level.value == value
            assert str(level) == value

    def test_string_representation(self):
        """Test string representation of enum values."""
        assert str(EnumSeverityLevel.ERROR) == "error"
        assert str(EnumSeverityLevel.WARNING) == "warning"
        assert str(EnumSeverityLevel.INFO) == "info"
        assert str(EnumSeverityLevel.DEBUG) == "debug"

    def test_from_string_direct_mapping(self):
        """Test from_string method with direct value mapping."""
        # Direct mappings should work
        assert EnumSeverityLevel.from_string("error") == EnumSeverityLevel.ERROR
        assert EnumSeverityLevel.from_string("warning") == EnumSeverityLevel.WARNING
        assert EnumSeverityLevel.from_string("info") == EnumSeverityLevel.INFO
        assert EnumSeverityLevel.from_string("debug") == EnumSeverityLevel.DEBUG

        # Case insensitive
        assert EnumSeverityLevel.from_string("ERROR") == EnumSeverityLevel.ERROR
        assert EnumSeverityLevel.from_string("Warning") == EnumSeverityLevel.WARNING
        assert EnumSeverityLevel.from_string("INFO") == EnumSeverityLevel.INFO

        # With whitespace
        assert EnumSeverityLevel.from_string("  error  ") == EnumSeverityLevel.ERROR
        assert EnumSeverityLevel.from_string("\twarning\n") == EnumSeverityLevel.WARNING

    def test_from_string_aliases(self):
        """Test from_string method with alias mapping."""
        # Test aliases - note that "warn" maps to WARN enum (direct match), not WARNING
        aliases = {
            "err": EnumSeverityLevel.ERROR,
            "warn": EnumSeverityLevel.WARN,  # Direct enum match takes precedence
            "information": EnumSeverityLevel.INFO,
            "informational": EnumSeverityLevel.INFO,
            "verbose": EnumSeverityLevel.DEBUG,
            "low": EnumSeverityLevel.INFO,
            "medium": EnumSeverityLevel.WARNING,  # Alias mapping
            "high": EnumSeverityLevel.ERROR,
            "severe": EnumSeverityLevel.CRITICAL,
        }

        for alias, expected_level in aliases.items():
            actual_level = EnumSeverityLevel.from_string(alias)
            assert (
                actual_level == expected_level
            ), f"Expected {alias} -> {expected_level}, got {actual_level}"
            # Test case insensitive
            actual_upper = EnumSeverityLevel.from_string(alias.upper())
            assert (
                actual_upper == expected_level
            ), f"Expected {alias.upper()} -> {expected_level}, got {actual_upper}"

    def test_from_string_fallback(self):
        """Test from_string method fallback behavior."""
        # Invalid strings should fall back to INFO
        assert EnumSeverityLevel.from_string("invalid") == EnumSeverityLevel.INFO
        assert EnumSeverityLevel.from_string("unknown") == EnumSeverityLevel.INFO
        assert EnumSeverityLevel.from_string("") == EnumSeverityLevel.INFO

    def test_numeric_level_property(self):
        """Test the numeric_level property."""
        expected_levels = {
            EnumSeverityLevel.TRACE: 10,
            EnumSeverityLevel.DEBUG: 20,
            EnumSeverityLevel.INFO: 30,
            EnumSeverityLevel.NOTICE: 35,
            EnumSeverityLevel.WARNING: 40,
            EnumSeverityLevel.WARN: 40,
            EnumSeverityLevel.ERROR: 50,
            EnumSeverityLevel.CRITICAL: 60,
            EnumSeverityLevel.ALERT: 70,
            EnumSeverityLevel.EMERGENCY: 80,
            EnumSeverityLevel.FATAL: 80,
        }

        for level, expected_numeric in expected_levels.items():
            assert level.numeric_level == expected_numeric

    def test_numeric_level_ordering(self):
        """Test that numeric levels provide correct ordering."""
        # Test ascending order of severity
        severity_order = [
            EnumSeverityLevel.TRACE,
            EnumSeverityLevel.DEBUG,
            EnumSeverityLevel.INFO,
            EnumSeverityLevel.NOTICE,
            EnumSeverityLevel.WARNING,
            EnumSeverityLevel.ERROR,
            EnumSeverityLevel.CRITICAL,
            EnumSeverityLevel.ALERT,
            EnumSeverityLevel.EMERGENCY,
        ]

        for i in range(len(severity_order) - 1):
            current = severity_order[i]
            next_level = severity_order[i + 1]
            assert current.numeric_level < next_level.numeric_level

        # Test that WARN and WARNING have same level
        assert (
            EnumSeverityLevel.WARN.numeric_level
            == EnumSeverityLevel.WARNING.numeric_level
        )

        # Test that FATAL and EMERGENCY have same level
        assert (
            EnumSeverityLevel.FATAL.numeric_level
            == EnumSeverityLevel.EMERGENCY.numeric_level
        )

    def test_is_error_level(self):
        """Test the is_error_level method."""
        # Error levels (numeric_level >= 50)
        error_levels = [
            EnumSeverityLevel.ERROR,
            EnumSeverityLevel.CRITICAL,
            EnumSeverityLevel.ALERT,
            EnumSeverityLevel.EMERGENCY,
            EnumSeverityLevel.FATAL,
        ]

        for level in error_levels:
            assert level.is_error_level() is True

        # Non-error levels (numeric_level < 50)
        non_error_levels = [
            EnumSeverityLevel.TRACE,
            EnumSeverityLevel.DEBUG,
            EnumSeverityLevel.INFO,
            EnumSeverityLevel.NOTICE,
            EnumSeverityLevel.WARNING,
            EnumSeverityLevel.WARN,
        ]

        for level in non_error_levels:
            assert level.is_error_level() is False

    def test_is_warning_level(self):
        """Test the is_warning_level method."""
        # Warning levels (numeric_level >= 40)
        warning_levels = [
            EnumSeverityLevel.WARNING,
            EnumSeverityLevel.WARN,
            EnumSeverityLevel.ERROR,
            EnumSeverityLevel.CRITICAL,
            EnumSeverityLevel.ALERT,
            EnumSeverityLevel.EMERGENCY,
            EnumSeverityLevel.FATAL,
        ]

        for level in warning_levels:
            assert level.is_warning_level() is True

        # Non-warning levels (numeric_level < 40)
        non_warning_levels = [
            EnumSeverityLevel.TRACE,
            EnumSeverityLevel.DEBUG,
            EnumSeverityLevel.INFO,
            EnumSeverityLevel.NOTICE,
        ]

        for level in non_warning_levels:
            assert level.is_warning_level() is False

    def test_is_info_level(self):
        """Test the is_info_level method."""
        # Info levels (numeric_level >= 30)
        info_levels = [
            EnumSeverityLevel.INFO,
            EnumSeverityLevel.NOTICE,
            EnumSeverityLevel.WARNING,
            EnumSeverityLevel.WARN,
            EnumSeverityLevel.ERROR,
            EnumSeverityLevel.CRITICAL,
            EnumSeverityLevel.ALERT,
            EnumSeverityLevel.EMERGENCY,
            EnumSeverityLevel.FATAL,
        ]

        for level in info_levels:
            assert level.is_info_level() is True

        # Non-info levels (numeric_level < 30)
        non_info_levels = [
            EnumSeverityLevel.TRACE,
            EnumSeverityLevel.DEBUG,
        ]

        for level in non_info_levels:
            assert level.is_info_level() is False

    def test_level_categorization_consistency(self):
        """Test that level categorization methods are consistent."""
        for level in EnumSeverityLevel:
            numeric = level.numeric_level

            # Test consistency with numeric thresholds
            assert level.is_error_level() == (numeric >= 50)
            assert level.is_warning_level() == (numeric >= 40)
            assert level.is_info_level() == (numeric >= 30)

    def test_enum_equality(self):
        """Test enum equality comparison."""
        assert EnumSeverityLevel.ERROR == EnumSeverityLevel.ERROR
        assert EnumSeverityLevel.WARNING != EnumSeverityLevel.ERROR
        assert (
            EnumSeverityLevel.WARN != EnumSeverityLevel.WARNING
        )  # Different enum values

    def test_enum_membership(self):
        """Test enum membership checking."""
        all_levels = list(EnumSeverityLevel)
        for level in all_levels:
            assert level in EnumSeverityLevel

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        levels = list(EnumSeverityLevel)
        assert len(levels) == 11

        level_values = [level.value for level in levels]
        expected_values = [
            "emergency",
            "alert",
            "critical",
            "error",
            "warning",
            "notice",
            "info",
            "debug",
            "trace",
            "fatal",
            "warn",
        ]

        assert set(level_values) == set(expected_values)

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        # Test direct serialization
        level = EnumSeverityLevel.CRITICAL
        json_str = json.dumps(level, default=str)
        assert json_str == '"critical"'

        # Test in dictionary
        data = {"severity": EnumSeverityLevel.WARNING}
        json_str = json.dumps(data, default=str)
        assert '"severity": "warning"' in json_str

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class LogMessage(BaseModel):
            severity: EnumSeverityLevel
            message: str

        # Test valid enum assignment
        log = LogMessage(severity=EnumSeverityLevel.ERROR, message="Test error")
        assert log.severity == EnumSeverityLevel.ERROR

        # Test string assignment (should work due to str inheritance)
        log = LogMessage(severity="warning", message="Test warning")
        assert log.severity == EnumSeverityLevel.WARNING

        # Test invalid value should raise ValidationError
        with pytest.raises(ValidationError):
            LogMessage(severity="invalid_level", message="Test")

    def test_pydantic_serialization(self):
        """Test Pydantic model serialization."""

        class LogMessage(BaseModel):
            severity: EnumSeverityLevel
            message: str

        log = LogMessage(severity=EnumSeverityLevel.ALERT, message="System alert")

        # Test dict serialization
        log_dict = log.model_dump()
        assert log_dict == {"severity": "alert", "message": "System alert"}

        # Test JSON serialization
        json_str = log.model_dump_json()
        assert '"severity":"alert"' in json_str

    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Test case sensitivity
        assert EnumSeverityLevel.ERROR.value == "error"
        assert EnumSeverityLevel.ERROR.value != "ERROR"

        # Test that we can't create invalid enum values
        with pytest.raises((ValueError, AttributeError)):
            _ = EnumSeverityLevel("invalid_level")

    def test_rfc5424_compliance(self):
        """Test RFC 5424 severity level compliance."""
        # Test that standard RFC 5424 levels are present
        rfc_levels = [
            "emergency",  # 0 - System is unusable
            "alert",  # 1 - Action must be taken immediately
            "critical",  # 2 - Critical conditions
            "error",  # 3 - Error conditions
            "warning",  # 4 - Warning conditions
            "notice",  # 5 - Normal but significant condition
            "info",  # 6 - Informational messages
            "debug",  # 7 - Debug-level messages
        ]

        for rfc_level in rfc_levels:
            # Should be able to get the level by value
            levels_with_value = [
                level for level in EnumSeverityLevel if level.value == rfc_level
            ]
            assert len(levels_with_value) >= 1, f"RFC level {rfc_level} not found"

    def test_level_comparison_scenarios(self):
        """Test practical level comparison scenarios."""
        # Test filtering by severity level
        critical_error = EnumSeverityLevel.CRITICAL
        warning = EnumSeverityLevel.WARNING
        info = EnumSeverityLevel.INFO

        # Critical error should be higher than warning
        assert critical_error.numeric_level > warning.numeric_level
        # Warning should be higher than info
        assert warning.numeric_level > info.numeric_level

        # Test threshold filtering scenarios
        all_levels = list(EnumSeverityLevel)
        error_and_above = [level for level in all_levels if level.is_error_level()]
        warning_and_above = [level for level in all_levels if level.is_warning_level()]
        info_and_above = [level for level in all_levels if level.is_info_level()]

        # Error levels should be subset of warning levels
        assert set(error_and_above).issubset(set(warning_and_above))
        # Warning levels should be subset of info levels
        assert set(warning_and_above).issubset(set(info_and_above))

    def test_yaml_serialization_compatibility(self):
        """Test YAML serialization compatibility."""
        import yaml

        # Test that enum values are YAML serializable (as string values)
        data = {"log_level": str(EnumSeverityLevel.EMERGENCY)}
        yaml_str = yaml.dump(data, default_flow_style=False)
        assert "log_level: emergency" in yaml_str

        # Test that we can load it back
        loaded_data = yaml.safe_load(yaml_str)
        assert loaded_data["log_level"] == "emergency"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
