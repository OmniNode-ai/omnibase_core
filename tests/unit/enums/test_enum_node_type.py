"""
Unit tests for EnumNodeType.

Test coverage for node type enumeration and helper methods.
"""

import pytest

from omnibase_core.enums import EnumNodeType


class TestEnumNodeType:
    """Test cases for EnumNodeType."""

    def test_enum_values(self):
        """Test core ONEX enum values are present."""
        expected_core_values = {
            "COMPUTE",
            "GATEWAY",
            "ORCHESTRATOR",
            "REDUCER",
            "EFFECT",
            "VALIDATOR",
            "TRANSFORMER",
            "AGGREGATOR",
        }
        actual_values = {node_type.value for node_type in EnumNodeType}
        # Test that all expected core values are present
        assert expected_core_values.issubset(actual_values)

    def test_string_inheritance(self):
        """Test that enum inherits from str."""
        assert isinstance(EnumNodeType.COMPUTE, str)
        assert EnumNodeType.COMPUTE == "COMPUTE"

    def test_is_processing_node(self):
        """Test processing node classification."""
        processing_nodes = {
            EnumNodeType.COMPUTE,
            EnumNodeType.TRANSFORMER,
            EnumNodeType.AGGREGATOR,
            EnumNodeType.REDUCER,
        }

        for node_type in EnumNodeType:
            expected = node_type in processing_nodes
            actual = EnumNodeType.is_processing_node(node_type)
            assert actual == expected, f"{node_type} processing classification failed"

    def test_is_control_node(self):
        """Test control node classification."""
        control_nodes = {
            EnumNodeType.ORCHESTRATOR,
            EnumNodeType.GATEWAY,
            EnumNodeType.VALIDATOR,
        }

        for node_type in EnumNodeType:
            expected = node_type in control_nodes
            actual = EnumNodeType.is_control_node(node_type)
            assert actual == expected, f"{node_type} control classification failed"

    def test_is_output_node(self):
        """Test output node classification."""
        output_nodes = {
            EnumNodeType.EFFECT,
            EnumNodeType.AGGREGATOR,
        }

        for node_type in EnumNodeType:
            expected = node_type in output_nodes
            actual = EnumNodeType.is_output_node(node_type)
            assert actual == expected, f"{node_type} output classification failed"

    def test_get_node_category(self):
        """Test node category mapping."""
        category_map = {
            EnumNodeType.COMPUTE: "processing",
            EnumNodeType.TRANSFORMER: "processing",
            EnumNodeType.AGGREGATOR: "processing",
            EnumNodeType.REDUCER: "processing",
            EnumNodeType.ORCHESTRATOR: "control",
            EnumNodeType.GATEWAY: "control",
            EnumNodeType.VALIDATOR: "control",
            EnumNodeType.EFFECT: "output",
        }

        for node_type, expected_category in category_map.items():
            actual_category = EnumNodeType.get_node_category(node_type)
            assert actual_category == expected_category

    def test_str_representation(self):
        """Test string representation."""
        for node_type in EnumNodeType:
            assert str(node_type) == node_type.value
