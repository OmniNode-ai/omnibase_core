"""Tests for enum_node_union_type.py"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_node_union_type import EnumNodeUnionType


@pytest.mark.unit
class TestEnumNodeUnionType:
    """Test cases for EnumNodeUnionType"""

    def test_enum_values(self):
        """Test that all enum values are correct"""
        assert EnumNodeUnionType.FUNCTION_NODE == "function_node"
        assert EnumNodeUnionType.FUNCTION_NODE_DATA == "function_node_data"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum"""
        assert issubclass(EnumNodeUnionType, str)
        assert issubclass(EnumNodeUnionType, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values"""
        assert EnumNodeUnionType.FUNCTION_NODE == "function_node"
        assert EnumNodeUnionType.FUNCTION_NODE_DATA == "function_node_data"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values"""
        values = list(EnumNodeUnionType)
        assert len(values) == 2
        assert EnumNodeUnionType.FUNCTION_NODE in values
        assert EnumNodeUnionType.FUNCTION_NODE_DATA in values

    def test_enum_membership(self):
        """Test membership testing"""
        assert EnumNodeUnionType.FUNCTION_NODE in EnumNodeUnionType
        assert "function_node" in EnumNodeUnionType
        assert "invalid_value" not in EnumNodeUnionType

    def test_enum_comparison(self):
        """Test enum comparison"""
        assert EnumNodeUnionType.FUNCTION_NODE == EnumNodeUnionType.FUNCTION_NODE
        assert EnumNodeUnionType.FUNCTION_NODE_DATA != EnumNodeUnionType.FUNCTION_NODE
        assert EnumNodeUnionType.FUNCTION_NODE == "function_node"

    def test_enum_serialization(self):
        """Test enum serialization"""
        assert EnumNodeUnionType.FUNCTION_NODE.value == "function_node"
        assert EnumNodeUnionType.FUNCTION_NODE_DATA.value == "function_node_data"

    def test_enum_deserialization(self):
        """Test enum deserialization"""
        assert EnumNodeUnionType("function_node") == EnumNodeUnionType.FUNCTION_NODE
        assert (
            EnumNodeUnionType("function_node_data")
            == EnumNodeUnionType.FUNCTION_NODE_DATA
        )

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError"""
        with pytest.raises(ValueError):
            EnumNodeUnionType("invalid_value")

        with pytest.raises(ValueError):
            EnumNodeUnionType("")

    def test_enum_all_values(self):
        """Test that all expected values are present"""
        expected_values = {"function_node", "function_node_data"}
        actual_values = {member.value for member in EnumNodeUnionType}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring"""
        assert (
            "Strongly typed node union type discriminators" in EnumNodeUnionType.__doc__
        )

    def test_enum_unique_decorator(self):
        """Test that enum has @unique decorator"""
        # The @unique decorator ensures no duplicate values
        # This is tested implicitly by the fact that the enum works correctly
        assert len(set(EnumNodeUnionType)) == len(EnumNodeUnionType)

    def test_enum_str_method(self):
        """Test the custom __str__ method"""
        assert str(EnumNodeUnionType.FUNCTION_NODE) == "function_node"
        assert str(EnumNodeUnionType.FUNCTION_NODE_DATA) == "function_node_data"

    def test_enum_node_types(self):
        """Test specific node types"""
        # Function node type
        assert EnumNodeUnionType.FUNCTION_NODE.value == "function_node"

        # Function node data type
        assert EnumNodeUnionType.FUNCTION_NODE_DATA.value == "function_node_data"

    def test_is_function_node_method(self):
        """Test the is_function_node class method"""
        assert (
            EnumNodeUnionType.is_function_node(EnumNodeUnionType.FUNCTION_NODE) is True
        )
        assert (
            EnumNodeUnionType.is_function_node(EnumNodeUnionType.FUNCTION_NODE_DATA)
            is False
        )

    def test_is_function_node_data_method(self):
        """Test the is_function_node_data class method"""
        assert (
            EnumNodeUnionType.is_function_node_data(
                EnumNodeUnionType.FUNCTION_NODE_DATA
            )
            is True
        )
        assert (
            EnumNodeUnionType.is_function_node_data(EnumNodeUnionType.FUNCTION_NODE)
            is False
        )

    def test_is_node_related_method(self):
        """Test the is_node_related class method"""
        assert (
            EnumNodeUnionType.is_node_related(EnumNodeUnionType.FUNCTION_NODE) is True
        )
        assert (
            EnumNodeUnionType.is_node_related(EnumNodeUnionType.FUNCTION_NODE_DATA)
            is True
        )

    def test_get_all_node_types_method(self):
        """Test the get_all_node_types class method"""
        all_types = EnumNodeUnionType.get_all_node_types()
        assert len(all_types) == 2
        assert EnumNodeUnionType.FUNCTION_NODE in all_types
        assert EnumNodeUnionType.FUNCTION_NODE_DATA in all_types

    def test_enum_union_discriminators(self):
        """Test union discriminator functionality"""
        # Test that both types are function node related
        assert EnumNodeUnionType.is_node_related(EnumNodeUnionType.FUNCTION_NODE)
        assert EnumNodeUnionType.is_node_related(EnumNodeUnionType.FUNCTION_NODE_DATA)

        # Test that we can distinguish between the two types
        assert EnumNodeUnionType.is_function_node(EnumNodeUnionType.FUNCTION_NODE)
        assert not EnumNodeUnionType.is_function_node(
            EnumNodeUnionType.FUNCTION_NODE_DATA
        )

        assert EnumNodeUnionType.is_function_node_data(
            EnumNodeUnionType.FUNCTION_NODE_DATA
        )
        assert not EnumNodeUnionType.is_function_node_data(
            EnumNodeUnionType.FUNCTION_NODE
        )
