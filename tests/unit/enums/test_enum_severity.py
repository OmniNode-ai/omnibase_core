# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for EnumSeverity.

Tests the canonical severity enum including string serialization via StrValueHelper,
enum member validation, uniqueness, and integration with Pydantic and JSON.
"""

import json

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from omnibase_core.enums import EnumSeverity


@pytest.mark.unit
class TestEnumSeverity:
    """Test cases for EnumSeverity canonical severity enum."""

    def test_enum_values_exist(self) -> None:
        """Verify all expected enum members are present with correct values."""
        expected_values = {
            "DEBUG": "debug",
            "INFO": "info",
            "WARNING": "warning",
            "ERROR": "error",
            "CRITICAL": "critical",
            "FATAL": "fatal",
        }

        for name, value in expected_values.items():
            level = getattr(EnumSeverity, name)
            assert level.value == value

    def test_enum_member_count(self) -> None:
        """Verify enum has exactly 6 members."""
        members = list(EnumSeverity)
        assert len(members) == 6

    def test_string_serialization_via_str_value_helper(self) -> None:
        """Test StrValueHelper provides __str__ returning the value."""
        assert str(EnumSeverity.DEBUG) == "debug"
        assert str(EnumSeverity.INFO) == "info"
        assert str(EnumSeverity.WARNING) == "warning"
        assert str(EnumSeverity.ERROR) == "error"
        assert str(EnumSeverity.CRITICAL) == "critical"
        assert str(EnumSeverity.FATAL) == "fatal"

    def test_str_value_helper_consistency(self) -> None:
        """Verify str() returns value for all enum members."""
        for member in EnumSeverity:
            assert str(member) == member.value

    def test_enum_uniqueness(self) -> None:
        """Verify no duplicate values exist via @unique decorator."""
        values = [member.value for member in EnumSeverity]
        assert len(values) == len(set(values))

    def test_enum_is_str_subclass(self) -> None:
        """Verify enum inherits from str for string compatibility."""
        for member in EnumSeverity:
            assert isinstance(member, str)
            assert isinstance(member.value, str)

    def test_enum_equality(self) -> None:
        """Test enum equality comparison."""
        assert EnumSeverity.ERROR == EnumSeverity.ERROR
        assert EnumSeverity.WARNING != EnumSeverity.ERROR
        assert EnumSeverity.CRITICAL != EnumSeverity.FATAL

    def test_enum_membership(self) -> None:
        """Test enum membership checking."""
        all_levels = list(EnumSeverity)
        for level in all_levels:
            assert level in EnumSeverity

    def test_enum_iteration_completeness(self) -> None:
        """Test that iterating over enum returns all 6 expected members.

        This verifies completeness (all values present), not ordering.
        For ordering tests, see test_severity_ordering_by_value.
        """
        levels = list(EnumSeverity)
        level_values = {level.value for level in levels}
        expected_values = {"debug", "info", "warning", "error", "critical", "fatal"}
        assert level_values == expected_values
        assert len(levels) == 6  # Explicit count check

    def test_json_serialization(self) -> None:
        """Test JSON serialization compatibility."""
        level = EnumSeverity.CRITICAL
        json_str = json.dumps(level, default=str)
        assert json_str == '"critical"'

        data = {"severity": EnumSeverity.WARNING}
        json_str = json.dumps(data, default=str)
        assert '"severity": "warning"' in json_str

    def test_pydantic_integration(self) -> None:
        """Test integration with Pydantic models."""

        class SeverityMessage(BaseModel):
            model_config = ConfigDict(extra="forbid")

            severity: EnumSeverity
            message: str

        msg = SeverityMessage(severity=EnumSeverity.ERROR, message="Test error")
        assert msg.severity == EnumSeverity.ERROR

        msg = SeverityMessage(severity="warning", message="Test warning")
        assert msg.severity == EnumSeverity.WARNING

        with pytest.raises(ValidationError):
            SeverityMessage(severity="invalid_level", message="Test")

    def test_pydantic_serialization(self) -> None:
        """Test Pydantic model serialization."""

        class SeverityMessage(BaseModel):
            model_config = ConfigDict(extra="forbid")

            severity: EnumSeverity
            message: str

        msg = SeverityMessage(severity=EnumSeverity.FATAL, message="System crash")

        msg_dict = msg.model_dump()
        assert msg_dict == {"severity": "fatal", "message": "System crash"}

        json_str = msg.model_dump_json()
        assert '"severity":"fatal"' in json_str

    def test_enum_value_case_sensitivity(self) -> None:
        """Test that enum values are lowercase."""
        for member in EnumSeverity:
            assert member.value == member.value.lower()
            assert member.value != member.value.upper()

    def test_invalid_enum_creation(self) -> None:
        """Test that invalid enum values raise errors."""
        with pytest.raises((ValueError, AttributeError)):
            _ = EnumSeverity("invalid_level")

    def test_string_comparison(self) -> None:
        """Test string comparison due to str inheritance."""
        assert EnumSeverity.ERROR == "error"
        assert EnumSeverity.WARNING == "warning"
        assert EnumSeverity.FATAL != "critical"

    def test_yaml_serialization_compatibility(self) -> None:
        """Test YAML serialization compatibility."""
        import yaml

        data = {"severity": str(EnumSeverity.FATAL)}
        yaml_str = yaml.dump(data, default_flow_style=False)
        assert "severity: fatal" in yaml_str

        loaded_data = yaml.safe_load(yaml_str)
        assert loaded_data["severity"] == "fatal"

    def test_severity_ordering_by_value(self) -> None:
        """Test that severity levels can be compared by conventional ordering.

        The ordering from lowest to highest is: DEBUG < INFO < WARNING < ERROR < CRITICAL < FATAL
        """
        severity_order = ["debug", "info", "warning", "error", "critical", "fatal"]
        enum_order = [
            EnumSeverity.DEBUG,
            EnumSeverity.INFO,
            EnumSeverity.WARNING,
            EnumSeverity.ERROR,
            EnumSeverity.CRITICAL,
            EnumSeverity.FATAL,
        ]

        for i, severity in enumerate(enum_order):
            assert severity.value == severity_order[i]

    def test_numeric_level_property(self) -> None:
        """Test numeric_level property returns correct values."""
        assert EnumSeverity.DEBUG.numeric_level == 10
        assert EnumSeverity.INFO.numeric_level == 20
        assert EnumSeverity.WARNING.numeric_level == 30
        assert EnumSeverity.ERROR.numeric_level == 40
        assert EnumSeverity.CRITICAL.numeric_level == 50
        assert EnumSeverity.FATAL.numeric_level == 60

    def test_numeric_level_ordering(self) -> None:
        """Test that numeric levels are ordered correctly."""
        levels = list(EnumSeverity)
        numeric_values = [level.numeric_level for level in levels]

        # Verify ordering: DEBUG < INFO < WARNING < ERROR < CRITICAL < FATAL
        assert EnumSeverity.DEBUG.numeric_level < EnumSeverity.INFO.numeric_level
        assert EnumSeverity.INFO.numeric_level < EnumSeverity.WARNING.numeric_level
        assert EnumSeverity.WARNING.numeric_level < EnumSeverity.ERROR.numeric_level
        assert EnumSeverity.ERROR.numeric_level < EnumSeverity.CRITICAL.numeric_level
        assert EnumSeverity.CRITICAL.numeric_level < EnumSeverity.FATAL.numeric_level

    def test_is_error_or_above(self) -> None:
        """Test is_error_or_above helper method."""
        # Not error or above
        assert not EnumSeverity.DEBUG.is_error_or_above()
        assert not EnumSeverity.INFO.is_error_or_above()
        assert not EnumSeverity.WARNING.is_error_or_above()

        # Error or above
        assert EnumSeverity.ERROR.is_error_or_above()
        assert EnumSeverity.CRITICAL.is_error_or_above()
        assert EnumSeverity.FATAL.is_error_or_above()

    def test_is_warning_or_above(self) -> None:
        """Test is_warning_or_above helper method."""
        # Not warning or above
        assert not EnumSeverity.DEBUG.is_warning_or_above()
        assert not EnumSeverity.INFO.is_warning_or_above()

        # Warning or above
        assert EnumSeverity.WARNING.is_warning_or_above()
        assert EnumSeverity.ERROR.is_warning_or_above()
        assert EnumSeverity.CRITICAL.is_warning_or_above()
        assert EnumSeverity.FATAL.is_warning_or_above()

    def test_severity_comparison_with_numeric_levels(self) -> None:
        """Test comparing severities using numeric levels."""
        # Example use case: filtering messages by minimum severity
        min_severity = EnumSeverity.WARNING

        below_threshold = [EnumSeverity.DEBUG, EnumSeverity.INFO]
        at_or_above_threshold = [
            EnumSeverity.WARNING,
            EnumSeverity.ERROR,
            EnumSeverity.CRITICAL,
            EnumSeverity.FATAL,
        ]

        for severity in below_threshold:
            assert severity.numeric_level < min_severity.numeric_level

        for severity in at_or_above_threshold:
            assert severity.numeric_level >= min_severity.numeric_level


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
