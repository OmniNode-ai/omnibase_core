"""
Tests for EnumCheckpointStatus enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_checkpoint_status import EnumCheckpointStatus


class TestEnumCheckpointStatus:
    """Test cases for EnumCheckpointStatus enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        assert EnumCheckpointStatus.ACTIVE == "active"
        assert EnumCheckpointStatus.COMPLETED == "completed"
        assert EnumCheckpointStatus.RESTORED == "restored"
        assert EnumCheckpointStatus.EXPIRED == "expired"
        assert EnumCheckpointStatus.CORRUPTED == "corrupted"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumCheckpointStatus, str)
        assert issubclass(EnumCheckpointStatus, Enum)

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings."""
        status = EnumCheckpointStatus.ACTIVE
        assert isinstance(status, str)
        assert status == "active"
        assert len(status) == 6
        assert status.startswith("act")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumCheckpointStatus)
        assert len(values) == 5
        assert EnumCheckpointStatus.ACTIVE in values
        assert EnumCheckpointStatus.CORRUPTED in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "active" in EnumCheckpointStatus
        assert "invalid_status" not in EnumCheckpointStatus

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        status1 = EnumCheckpointStatus.ACTIVE
        status2 = EnumCheckpointStatus.COMPLETED

        assert status1 != status2
        assert status1 == "active"
        assert status2 == "completed"

    def test_enum_serialization(self):
        """Test that enum values can be serialized."""
        status = EnumCheckpointStatus.RESTORED
        serialized = status.value
        assert serialized == "restored"

        # Test JSON serialization
        import json

        json_str = json.dumps(status)
        assert json_str == '"restored"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        status = EnumCheckpointStatus("expired")
        assert status == EnumCheckpointStatus.EXPIRED

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumCheckpointStatus("invalid_status")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {"active", "completed", "restored", "expired", "corrupted"}

        actual_values = {member.value for member in EnumCheckpointStatus}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert "Status of workflow checkpoints" in EnumCheckpointStatus.__doc__

    def test_enum_checkpoint_lifecycle(self):
        """Test that enum covers typical checkpoint lifecycle states."""
        # Test active state
        assert EnumCheckpointStatus.ACTIVE in EnumCheckpointStatus

        # Test completion states
        assert EnumCheckpointStatus.COMPLETED in EnumCheckpointStatus
        assert EnumCheckpointStatus.RESTORED in EnumCheckpointStatus

        # Test error states
        assert EnumCheckpointStatus.EXPIRED in EnumCheckpointStatus
        assert EnumCheckpointStatus.CORRUPTED in EnumCheckpointStatus
