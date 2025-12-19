"""
Tests for EnumConversationStatus enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_conversation_status import EnumConversationStatus


@pytest.mark.unit
class TestEnumConversationStatus:
    """Test cases for EnumConversationStatus enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        # Active states
        assert EnumConversationStatus.ACTIVE == "active"
        assert EnumConversationStatus.ONGOING == "ongoing"
        assert EnumConversationStatus.PAUSED == "paused"

        # Completion states
        assert EnumConversationStatus.COMPLETED == "completed"
        assert EnumConversationStatus.TERMINATED == "terminated"
        assert EnumConversationStatus.EXPIRED == "expired"

        # Error states
        assert EnumConversationStatus.ERROR == "error"
        assert EnumConversationStatus.FAILED == "failed"
        assert EnumConversationStatus.TIMEOUT == "timeout"

        # Initialization states
        assert EnumConversationStatus.INITIALIZED == "initialized"
        assert EnumConversationStatus.STARTING == "starting"
        assert EnumConversationStatus.READY == "ready"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumConversationStatus, str)
        assert issubclass(EnumConversationStatus, Enum)

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings."""
        status = EnumConversationStatus.ACTIVE
        assert isinstance(status, str)
        assert status == "active"
        assert len(status) == 6
        assert status.startswith("act")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumConversationStatus)
        assert len(values) == 12
        assert EnumConversationStatus.ACTIVE in values
        assert EnumConversationStatus.READY in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "active" in EnumConversationStatus
        assert "invalid_status" not in EnumConversationStatus

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        status1 = EnumConversationStatus.ACTIVE
        status2 = EnumConversationStatus.PAUSED

        assert status1 != status2
        assert status1 == "active"
        assert status2 == "paused"

    def test_enum_serialization(self):
        """Test that enum values can be serialized."""
        status = EnumConversationStatus.COMPLETED
        serialized = status.value
        assert serialized == "completed"

        # Test JSON serialization
        import json

        json_str = json.dumps(status)
        assert json_str == '"completed"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        status = EnumConversationStatus("terminated")
        assert status == EnumConversationStatus.TERMINATED

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumConversationStatus("invalid_status")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "active",
            "ongoing",
            "paused",
            "completed",
            "terminated",
            "expired",
            "error",
            "failed",
            "timeout",
            "initialized",
            "starting",
            "ready",
        }

        actual_values = {member.value for member in EnumConversationStatus}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert (
            "Conversation status enumeration for session state management"
            in EnumConversationStatus.__doc__
        )

    def test_enum_conversation_lifecycle(self):
        """Test that enum covers typical conversation lifecycle states."""
        # Test initialization states
        assert EnumConversationStatus.INITIALIZED in EnumConversationStatus
        assert EnumConversationStatus.STARTING in EnumConversationStatus
        assert EnumConversationStatus.READY in EnumConversationStatus

        # Test active states
        assert EnumConversationStatus.ACTIVE in EnumConversationStatus
        assert EnumConversationStatus.ONGOING in EnumConversationStatus
        assert EnumConversationStatus.PAUSED in EnumConversationStatus

        # Test completion states
        assert EnumConversationStatus.COMPLETED in EnumConversationStatus
        assert EnumConversationStatus.TERMINATED in EnumConversationStatus
        assert EnumConversationStatus.EXPIRED in EnumConversationStatus

        # Test error states
        assert EnumConversationStatus.ERROR in EnumConversationStatus
        assert EnumConversationStatus.FAILED in EnumConversationStatus
        assert EnumConversationStatus.TIMEOUT in EnumConversationStatus
