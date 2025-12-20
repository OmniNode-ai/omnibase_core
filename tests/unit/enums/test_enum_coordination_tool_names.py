"""
Tests for EnumCoordinationToolNames enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_coordination_tool_names import EnumCoordinationToolNames


@pytest.mark.unit
class TestEnumCoordinationToolNames:
    """Test cases for EnumCoordinationToolNames enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        assert (
            EnumCoordinationToolNames.TOOL_GENERIC_HUB_NODE == "tool_generic_hub_node"
        )
        assert (
            EnumCoordinationToolNames.TOOL_CONTRACT_EVENT_ROUTER
            == "tool_contract_event_router"
        )
        assert (
            EnumCoordinationToolNames.TOOL_COMPOSITION_COORDINATOR
            == "tool_composition_coordinator"
        )
        assert (
            EnumCoordinationToolNames.TOOL_SUBWORKFLOW_EXECUTOR
            == "tool_subworkflow_executor"
        )
        assert (
            EnumCoordinationToolNames.TOOL_COMPOSITION_ORCHESTRATOR
            == "tool_composition_orchestrator"
        )
        assert (
            EnumCoordinationToolNames.TOOL_WORKFLOW_REGISTRY == "tool_workflow_registry"
        )

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumCoordinationToolNames, str)
        assert issubclass(EnumCoordinationToolNames, Enum)

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings."""
        tool_name = EnumCoordinationToolNames.TOOL_GENERIC_HUB_NODE
        assert isinstance(tool_name, str)
        assert tool_name == "tool_generic_hub_node"
        assert len(tool_name) == 21
        assert tool_name.startswith("tool_")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumCoordinationToolNames)
        assert len(values) == 6
        assert EnumCoordinationToolNames.TOOL_GENERIC_HUB_NODE in values
        assert EnumCoordinationToolNames.TOOL_WORKFLOW_REGISTRY in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "tool_generic_hub_node" in EnumCoordinationToolNames
        assert "invalid_tool" not in EnumCoordinationToolNames

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        tool1 = EnumCoordinationToolNames.TOOL_GENERIC_HUB_NODE
        tool2 = EnumCoordinationToolNames.TOOL_CONTRACT_EVENT_ROUTER

        assert tool1 != tool2
        assert tool1 == "tool_generic_hub_node"
        assert tool2 == "tool_contract_event_router"

    def test_enum_serialization(self):
        """Test that enum values can be serialized."""
        tool_name = EnumCoordinationToolNames.TOOL_COMPOSITION_COORDINATOR
        serialized = tool_name.value
        assert serialized == "tool_composition_coordinator"

        # Test JSON serialization
        import json

        json_str = json.dumps(tool_name)
        assert json_str == '"tool_composition_coordinator"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        tool_name = EnumCoordinationToolNames("tool_subworkflow_executor")
        assert tool_name == EnumCoordinationToolNames.TOOL_SUBWORKFLOW_EXECUTOR

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumCoordinationToolNames("invalid_tool")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "tool_generic_hub_node",
            "tool_contract_event_router",
            "tool_composition_coordinator",
            "tool_subworkflow_executor",
            "tool_composition_orchestrator",
            "tool_workflow_registry",
        }

        actual_values = {member.value for member in EnumCoordinationToolNames}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert (
            "Coordination tool names following ONEX enum-backed naming standards"
            in EnumCoordinationToolNames.__doc__
        )

    def test_enum_coordination_tools(self):
        """Test that enum covers typical coordination tools."""
        # Test hub and node tools
        assert (
            EnumCoordinationToolNames.TOOL_GENERIC_HUB_NODE in EnumCoordinationToolNames
        )

        # Test event routing tools
        assert (
            EnumCoordinationToolNames.TOOL_CONTRACT_EVENT_ROUTER
            in EnumCoordinationToolNames
        )

        # Test composition tools
        assert (
            EnumCoordinationToolNames.TOOL_COMPOSITION_COORDINATOR
            in EnumCoordinationToolNames
        )
        assert (
            EnumCoordinationToolNames.TOOL_COMPOSITION_ORCHESTRATOR
            in EnumCoordinationToolNames
        )

        # Test workflow tools
        assert (
            EnumCoordinationToolNames.TOOL_SUBWORKFLOW_EXECUTOR
            in EnumCoordinationToolNames
        )
        assert (
            EnumCoordinationToolNames.TOOL_WORKFLOW_REGISTRY
            in EnumCoordinationToolNames
        )
