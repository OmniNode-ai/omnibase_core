"""
Tests for EnumChainValidationStatus enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_chain_validation_status import EnumChainValidationStatus


class TestEnumChainValidationStatus:
    """Test cases for EnumChainValidationStatus enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        assert EnumChainValidationStatus.VALID == "valid"
        assert EnumChainValidationStatus.PARTIAL == "partial"
        assert EnumChainValidationStatus.INVALID == "invalid"
        assert EnumChainValidationStatus.INCOMPLETE == "incomplete"
        assert EnumChainValidationStatus.TAMPERED == "tampered"
        assert EnumChainValidationStatus.EXPIRED == "expired"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumChainValidationStatus, str)
        assert issubclass(EnumChainValidationStatus, Enum)

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings."""
        status = EnumChainValidationStatus.VALID
        assert isinstance(status, str)
        assert status == "valid"
        assert len(status) == 5
        assert status.startswith("val")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumChainValidationStatus)
        assert len(values) == 6
        assert EnumChainValidationStatus.VALID in values
        assert EnumChainValidationStatus.EXPIRED in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "valid" in EnumChainValidationStatus
        assert "invalid_status" not in EnumChainValidationStatus

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        status1 = EnumChainValidationStatus.VALID
        status2 = EnumChainValidationStatus.INVALID

        assert status1 != status2
        assert status1 == "valid"
        assert status2 == "invalid"

    def test_enum_serialization(self):
        """Test that enum values can be serialized."""
        status = EnumChainValidationStatus.PARTIAL
        serialized = status.value
        assert serialized == "partial"

        # Test JSON serialization
        import json

        json_str = json.dumps(status)
        assert json_str == '"partial"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        status = EnumChainValidationStatus("tampered")
        assert status == EnumChainValidationStatus.TAMPERED

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumChainValidationStatus("invalid_status")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "valid",
            "partial",
            "invalid",
            "incomplete",
            "tampered",
            "expired",
        }

        actual_values = {member.value for member in EnumChainValidationStatus}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert (
            "Status of signature chain validation" in EnumChainValidationStatus.__doc__
        )

    def test_enum_validation_states(self):
        """Test that enum covers typical validation states."""
        # Test success states
        assert EnumChainValidationStatus.VALID in EnumChainValidationStatus

        # Test partial states
        assert EnumChainValidationStatus.PARTIAL in EnumChainValidationStatus

        # Test failure states
        assert EnumChainValidationStatus.INVALID in EnumChainValidationStatus
        assert EnumChainValidationStatus.INCOMPLETE in EnumChainValidationStatus
        assert EnumChainValidationStatus.TAMPERED in EnumChainValidationStatus
        assert EnumChainValidationStatus.EXPIRED in EnumChainValidationStatus
