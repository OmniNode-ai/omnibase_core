"""
Tests for EnumDiscoveryStatus enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_discovery_status import EnumDiscoveryStatus


class TestEnumDiscoveryStatus:
    """Test cases for EnumDiscoveryStatus enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        assert EnumDiscoveryStatus.SUCCESS == "success"
        assert EnumDiscoveryStatus.FAILED == "failed"
        assert EnumDiscoveryStatus.TIMEOUT == "timeout"
        assert EnumDiscoveryStatus.PARTIAL == "partial"
        assert EnumDiscoveryStatus.CACHED == "cached"
        assert EnumDiscoveryStatus.ACTIVE == "active"
        assert EnumDiscoveryStatus.INACTIVE == "inactive"
        assert EnumDiscoveryStatus.PENDING == "pending"
        assert EnumDiscoveryStatus.COMPLETED == "completed"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumDiscoveryStatus, str)
        assert issubclass(EnumDiscoveryStatus, Enum)

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings."""
        status = EnumDiscoveryStatus.SUCCESS
        assert isinstance(status, str)
        assert status == "success"
        assert len(status) == 7
        assert status.startswith("suc")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumDiscoveryStatus)
        assert len(values) == 9
        assert EnumDiscoveryStatus.SUCCESS in values
        assert EnumDiscoveryStatus.COMPLETED in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "success" in EnumDiscoveryStatus
        assert "invalid_status" not in EnumDiscoveryStatus

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        status1 = EnumDiscoveryStatus.SUCCESS
        status2 = EnumDiscoveryStatus.FAILED

        assert status1 != status2
        assert status1 == "success"
        assert status2 == "failed"

    def test_enum_serialization(self):
        """Test that enum values can be serialized."""
        status = EnumDiscoveryStatus.TIMEOUT
        serialized = status.value
        assert serialized == "timeout"

        # Test JSON serialization
        import json

        json_str = json.dumps(status)
        assert json_str == '"timeout"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        status = EnumDiscoveryStatus("partial")
        assert status == EnumDiscoveryStatus.PARTIAL

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumDiscoveryStatus("invalid_status")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "success",
            "failed",
            "timeout",
            "partial",
            "cached",
            "active",
            "inactive",
            "pending",
            "completed",
        }

        actual_values = {member.value for member in EnumDiscoveryStatus}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert (
            "Discovery status values for tool discovery operations"
            in EnumDiscoveryStatus.__doc__
        )

    def test_enum_discovery_statuses(self):
        """Test that enum covers typical discovery statuses."""
        # Test success states
        assert EnumDiscoveryStatus.SUCCESS in EnumDiscoveryStatus
        assert EnumDiscoveryStatus.COMPLETED in EnumDiscoveryStatus

        # Test failure states
        assert EnumDiscoveryStatus.FAILED in EnumDiscoveryStatus
        assert EnumDiscoveryStatus.TIMEOUT in EnumDiscoveryStatus

        # Test partial states
        assert EnumDiscoveryStatus.PARTIAL in EnumDiscoveryStatus

        # Test cache states
        assert EnumDiscoveryStatus.CACHED in EnumDiscoveryStatus

        # Test activity states
        assert EnumDiscoveryStatus.ACTIVE in EnumDiscoveryStatus
        assert EnumDiscoveryStatus.INACTIVE in EnumDiscoveryStatus

        # Test pending state
        assert EnumDiscoveryStatus.PENDING in EnumDiscoveryStatus
