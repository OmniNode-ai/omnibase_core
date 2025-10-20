"""
Test cases for EnumStatusMessage.

Tests the status message enumeration.
"""

from omnibase_core.enums.enum_status_message import EnumStatusMessage


class TestEnumStatusMessage:
    """Test EnumStatusMessage enumeration."""

    def test_enum_values(self) -> None:
        """Test all enum values are accessible."""
        assert EnumStatusMessage.ACTIVE == "active"
        assert EnumStatusMessage.INACTIVE == "inactive"
        assert EnumStatusMessage.PENDING == "pending"
        assert EnumStatusMessage.PROCESSING == "processing"
        assert EnumStatusMessage.COMPLETED == "completed"
        assert EnumStatusMessage.FAILED == "failed"

    def test_enum_string_values(self) -> None:
        """Test that enum values have correct string representations."""
        expected_mappings = {
            EnumStatusMessage.ACTIVE: "active",
            EnumStatusMessage.INACTIVE: "inactive",
            EnumStatusMessage.PENDING: "pending",
            EnumStatusMessage.PROCESSING: "processing",
            EnumStatusMessage.COMPLETED: "completed",
            EnumStatusMessage.FAILED: "failed",
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
        assert "active" in EnumStatusMessage._value2member_map_
        assert "inactive" in EnumStatusMessage._value2member_map_
        assert "pending" in EnumStatusMessage._value2member_map_
        assert "processing" in EnumStatusMessage._value2member_map_
        assert "completed" in EnumStatusMessage._value2member_map_
        assert "failed" in EnumStatusMessage._value2member_map_
        assert "invalid" not in EnumStatusMessage._value2member_map_
