"""
Tests for EnumCliDiscoveryAction enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_cli_discovery_action import EnumCliDiscoveryAction


@pytest.mark.unit
class TestEnumCliDiscoveryAction:
    """Test cases for EnumCliDiscoveryAction enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        assert (
            EnumCliDiscoveryAction.DISCOVER_AVAILABLE_TOOLS
            == "discover_available_tools"
        )
        assert (
            EnumCliDiscoveryAction.RESOLVE_TOOL_IMPLEMENTATION
            == "resolve_tool_implementation"
        )
        assert EnumCliDiscoveryAction.VALIDATE_TOOL_HEALTH == "validate_tool_health"
        assert EnumCliDiscoveryAction.GET_TOOL_METADATA == "get_tool_metadata"
        assert EnumCliDiscoveryAction.REFRESH_TOOL_REGISTRY == "refresh_tool_registry"
        assert EnumCliDiscoveryAction.GET_DISCOVERY_STATS == "get_discovery_stats"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumCliDiscoveryAction, str)
        assert issubclass(EnumCliDiscoveryAction, Enum)

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings."""
        action = EnumCliDiscoveryAction.DISCOVER_AVAILABLE_TOOLS
        assert isinstance(action, str)
        assert action == "discover_available_tools"
        assert len(action) == 24
        assert action.startswith("discover")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumCliDiscoveryAction)
        assert len(values) == 6
        assert EnumCliDiscoveryAction.DISCOVER_AVAILABLE_TOOLS in values
        assert EnumCliDiscoveryAction.GET_DISCOVERY_STATS in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "discover_available_tools" in EnumCliDiscoveryAction
        assert "invalid_action" not in EnumCliDiscoveryAction

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        action1 = EnumCliDiscoveryAction.DISCOVER_AVAILABLE_TOOLS
        action2 = EnumCliDiscoveryAction.VALIDATE_TOOL_HEALTH

        assert action1 != action2
        assert action1 == "discover_available_tools"
        assert action2 == "validate_tool_health"

    def test_enum_serialization(self):
        """Test that enum values can be serialized."""
        action = EnumCliDiscoveryAction.GET_TOOL_METADATA
        serialized = action.value
        assert serialized == "get_tool_metadata"

        # Test JSON serialization
        import json

        json_str = json.dumps(action)
        assert json_str == '"get_tool_metadata"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        action = EnumCliDiscoveryAction("refresh_tool_registry")
        assert action == EnumCliDiscoveryAction.REFRESH_TOOL_REGISTRY

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumCliDiscoveryAction("invalid_action")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "discover_available_tools",
            "resolve_tool_implementation",
            "validate_tool_health",
            "get_tool_metadata",
            "refresh_tool_registry",
            "get_discovery_stats",
        }

        actual_values = {member.value for member in EnumCliDiscoveryAction}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert (
            "Enumeration of valid CLI tool discovery actions"
            in EnumCliDiscoveryAction.__doc__
        )

    def test_enum_discovery_actions(self):
        """Test that enum covers typical CLI discovery actions."""
        # Test core discovery operations
        assert EnumCliDiscoveryAction.DISCOVER_AVAILABLE_TOOLS in EnumCliDiscoveryAction
        assert (
            EnumCliDiscoveryAction.RESOLVE_TOOL_IMPLEMENTATION in EnumCliDiscoveryAction
        )

        # Test validation operations
        assert EnumCliDiscoveryAction.VALIDATE_TOOL_HEALTH in EnumCliDiscoveryAction

        # Test metadata operations
        assert EnumCliDiscoveryAction.GET_TOOL_METADATA in EnumCliDiscoveryAction

        # Test registry operations
        assert EnumCliDiscoveryAction.REFRESH_TOOL_REGISTRY in EnumCliDiscoveryAction

        # Test stats operations
        assert EnumCliDiscoveryAction.GET_DISCOVERY_STATS in EnumCliDiscoveryAction
