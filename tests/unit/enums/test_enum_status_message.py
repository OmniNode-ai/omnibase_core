"""
Test cases for EnumStatusMessage.

Tests the status message enumeration.
"""

import pytest

from omnibase_core.enums.enum_status_message import EnumStatusMessage


class TestEnumStatusMessage:
    """Test EnumStatusMessage enumeration."""

    def test_enum_values(self) -> None:
        """Test all enum values are accessible."""
        assert EnumStatusMessage.ACTIVE == "ACTIVE"
        assert EnumStatusMessage.INACTIVE == "INACTIVE"
        assert EnumStatusMessage.PENDING == "PENDING"
        assert EnumStatusMessage.PROCESSING == "PROCESSING"
        assert EnumStatusMessage.COMPLETED == "COMPLETED"
        assert EnumStatusMessage.FAILED == "FAILED"

    def test_enum_string_values(self) -> None:
        """Test that enum values have correct string representations."""
        expected_mappings = {
            EnumStatusMessage.ACTIVE: "ACTIVE",
            EnumStatusMessage.INACTIVE: "INACTIVE",
            EnumStatusMessage.PENDING: "PENDING",
            EnumStatusMessage.PROCESSING: "PROCESSING",
            EnumStatusMessage.COMPLETED: "COMPLETED",
            EnumStatusMessage.FAILED: "FAILED",
        }

        for enum_member, expected_str in expected_mappings.items():
            assert enum_member.value == expected_str
            assert enum_member == expected_str  # Test equality with string

    def test_enum_iteration(self) -> None:
        """Test enum iteration."""
        values = list(EnumStatusMessage)
        assert len(values) == 6
        assert EnumStatusMessage.ACTIVE in values
        assert EnumStatusMessage.INACTIVE in values
        assert EnumStatusMessage.PENDING in values
        assert EnumStatusMessage.PROCESSING in values
        assert EnumStatusMessage.COMPLETED in values
        assert EnumStatusMessage.FAILED in values

    def test_enum_membership(self) -> None:
        """Test enum membership testing."""
        assert "ACTIVE" in EnumStatusMessage._value2member_map_
        assert "INACTIVE" in EnumStatusMessage._value2member_map_
        assert "PENDING" in EnumStatusMessage._value2member_map_
        assert "PROCESSING" in EnumStatusMessage._value2member_map_
        assert "COMPLETED" in EnumStatusMessage._value2member_map_
        assert "FAILED" in EnumStatusMessage._value2member_map_
        assert "INVALID" not in EnumStatusMessage._value2member_map_