# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for EnumRegistryAction."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.enum_registry_action import EnumRegistryAction


@pytest.mark.unit
class TestEnumRegistryAction:
    """Test suite for EnumRegistryAction."""

    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert EnumRegistryAction.GET_ACTIVE_NODES == "get_active_nodes"
        assert EnumRegistryAction.GET_NODE == "get_node"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumRegistryAction, str)
        assert issubclass(EnumRegistryAction, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        action = EnumRegistryAction.GET_ACTIVE_NODES
        assert isinstance(action, str)
        assert action == "get_active_nodes"
        assert len(action) == 16

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumRegistryAction)
        assert len(values) == 2
        assert EnumRegistryAction.GET_ACTIVE_NODES in values
        assert EnumRegistryAction.GET_NODE in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumRegistryAction.GET_NODE in EnumRegistryAction
        assert "get_node" in [e.value for e in EnumRegistryAction]

    def test_enum_comparison(self):
        """Test enum comparison."""
        action1 = EnumRegistryAction.GET_ACTIVE_NODES
        action2 = EnumRegistryAction.GET_ACTIVE_NODES
        action3 = EnumRegistryAction.GET_NODE

        assert action1 == action2
        assert action1 != action3
        assert action1 == "get_active_nodes"

    def test_enum_serialization(self):
        """Test enum serialization."""
        action = EnumRegistryAction.GET_NODE
        serialized = action.value
        assert serialized == "get_node"
        json_str = json.dumps(action)
        assert json_str == '"get_node"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        action = EnumRegistryAction("get_active_nodes")
        assert action == EnumRegistryAction.GET_ACTIVE_NODES

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumRegistryAction("invalid_action")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {"get_active_nodes", "get_node"}
        actual_values = {e.value for e in EnumRegistryAction}
        assert actual_values == expected_values

    def test_registry_action_naming(self):
        """Test that all actions follow naming convention."""
        for action in EnumRegistryAction:
            # Should start with "get_"
            assert action.value.startswith("get_")
            # Should be lowercase with underscores
            assert action.value == action.value.lower()
            assert " " not in action.value

    def test_action_semantic_grouping(self):
        """Test semantic grouping of registry actions."""
        # All current actions are query actions
        query_actions = {
            EnumRegistryAction.GET_ACTIVE_NODES,
            EnumRegistryAction.GET_NODE,
        }
        assert query_actions == set(EnumRegistryAction)
