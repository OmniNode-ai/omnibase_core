"""
Tests for EnumDaemonActionType enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_daemon_action_type import EnumDaemonActionType


@pytest.mark.unit
class TestEnumDaemonActionType:
    """Test cases for EnumDaemonActionType enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        assert EnumDaemonActionType.LIFECYCLE == "lifecycle"
        assert EnumDaemonActionType.HEALTH == "health"
        assert EnumDaemonActionType.STATUS == "status"
        assert EnumDaemonActionType.CONFIGURATION == "configuration"
        assert EnumDaemonActionType.SERVICE_MANAGEMENT == "service_management"
        assert EnumDaemonActionType.MONITORING == "monitoring"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumDaemonActionType, str)
        assert issubclass(EnumDaemonActionType, Enum)

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings."""
        action_type = EnumDaemonActionType.LIFECYCLE
        assert isinstance(action_type, str)
        assert action_type == "lifecycle"
        assert len(action_type) == 9
        assert action_type.startswith("life")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumDaemonActionType)
        assert len(values) == 6
        assert EnumDaemonActionType.LIFECYCLE in values
        assert EnumDaemonActionType.MONITORING in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "lifecycle" in EnumDaemonActionType
        assert "invalid_action" not in EnumDaemonActionType

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        action1 = EnumDaemonActionType.LIFECYCLE
        action2 = EnumDaemonActionType.HEALTH

        assert action1 != action2
        assert action1 == "lifecycle"
        assert action2 == "health"

    def test_enum_serialization(self):
        """Test that enum values can be serialized."""
        action_type = EnumDaemonActionType.STATUS
        serialized = action_type.value
        assert serialized == "status"

        # Test JSON serialization
        import json

        json_str = json.dumps(action_type)
        assert json_str == '"status"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        action_type = EnumDaemonActionType("configuration")
        assert action_type == EnumDaemonActionType.CONFIGURATION

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumDaemonActionType("invalid_action")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "lifecycle",
            "health",
            "status",
            "configuration",
            "service_management",
            "monitoring",
        }

        actual_values = {member.value for member in EnumDaemonActionType}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert (
            "Action types for daemon management operations"
            in EnumDaemonActionType.__doc__
        )

    def test_enum_str_method(self):
        """Test the __str__ method."""
        action_type = EnumDaemonActionType.LIFECYCLE
        assert str(action_type) == "lifecycle"
        assert str(EnumDaemonActionType.MONITORING) == "monitoring"

    def test_is_destructive(self):
        """Test the is_destructive method."""
        # Test destructive actions
        assert EnumDaemonActionType.LIFECYCLE.is_destructive()
        assert EnumDaemonActionType.SERVICE_MANAGEMENT.is_destructive()
        assert EnumDaemonActionType.CONFIGURATION.is_destructive()

        # Test non-destructive actions
        assert not EnumDaemonActionType.HEALTH.is_destructive()
        assert not EnumDaemonActionType.STATUS.is_destructive()
        assert not EnumDaemonActionType.MONITORING.is_destructive()

    def test_requires_confirmation(self):
        """Test the requires_confirmation method."""
        # Test actions that require confirmation
        assert EnumDaemonActionType.LIFECYCLE.requires_confirmation()
        assert EnumDaemonActionType.SERVICE_MANAGEMENT.requires_confirmation()

        # Test actions that don't require confirmation
        assert not EnumDaemonActionType.HEALTH.requires_confirmation()
        assert not EnumDaemonActionType.STATUS.requires_confirmation()
        assert not EnumDaemonActionType.CONFIGURATION.requires_confirmation()
        assert not EnumDaemonActionType.MONITORING.requires_confirmation()

    def test_enum_daemon_action_types(self):
        """Test that enum covers typical daemon action types."""
        # Test lifecycle actions
        assert EnumDaemonActionType.LIFECYCLE in EnumDaemonActionType

        # Test health and status actions
        assert EnumDaemonActionType.HEALTH in EnumDaemonActionType
        assert EnumDaemonActionType.STATUS in EnumDaemonActionType

        # Test configuration actions
        assert EnumDaemonActionType.CONFIGURATION in EnumDaemonActionType

        # Test service management actions
        assert EnumDaemonActionType.SERVICE_MANAGEMENT in EnumDaemonActionType

        # Test monitoring actions
        assert EnumDaemonActionType.MONITORING in EnumDaemonActionType
