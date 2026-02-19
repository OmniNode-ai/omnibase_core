# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for enum_onex_tree_node_type.py"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_onex_tree_node_type import EnumOnexTreeNodeType


@pytest.mark.unit
class TestEnumOnexTreeNodeType:
    """Test cases for EnumOnexTreeNodeType"""

    def test_enum_values(self):
        """Test that all enum values are correct"""
        assert EnumOnexTreeNodeType.FILE == "file"
        assert EnumOnexTreeNodeType.DIRECTORY == "directory"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum"""
        assert issubclass(EnumOnexTreeNodeType, str)
        assert issubclass(EnumOnexTreeNodeType, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values"""
        assert EnumOnexTreeNodeType.FILE == "file"
        assert EnumOnexTreeNodeType.DIRECTORY == "directory"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values"""
        values = list(EnumOnexTreeNodeType)
        assert len(values) == 2
        assert EnumOnexTreeNodeType.FILE in values
        assert EnumOnexTreeNodeType.DIRECTORY in values

    def test_enum_membership(self):
        """Test membership testing"""
        assert EnumOnexTreeNodeType.FILE in EnumOnexTreeNodeType
        assert "file" in EnumOnexTreeNodeType
        assert "invalid_value" not in EnumOnexTreeNodeType

    def test_enum_comparison(self):
        """Test enum comparison"""
        assert EnumOnexTreeNodeType.FILE == EnumOnexTreeNodeType.FILE
        assert EnumOnexTreeNodeType.DIRECTORY != EnumOnexTreeNodeType.FILE
        assert EnumOnexTreeNodeType.FILE == "file"

    def test_enum_serialization(self):
        """Test enum serialization"""
        assert EnumOnexTreeNodeType.FILE.value == "file"
        assert EnumOnexTreeNodeType.DIRECTORY.value == "directory"

    def test_enum_deserialization(self):
        """Test enum deserialization"""
        assert EnumOnexTreeNodeType("file") == EnumOnexTreeNodeType.FILE
        assert EnumOnexTreeNodeType("directory") == EnumOnexTreeNodeType.DIRECTORY

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError"""
        with pytest.raises(ValueError):
            EnumOnexTreeNodeType("invalid_value")

        with pytest.raises(ValueError):
            EnumOnexTreeNodeType("")

    def test_enum_all_values(self):
        """Test that all expected values are present"""
        expected_values = {"file", "directory"}
        actual_values = {member.value for member in EnumOnexTreeNodeType}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring"""
        assert "Type of an OnexTreeNode" in EnumOnexTreeNodeType.__doc__

    def test_enum_node_types(self):
        """Test specific node types"""
        # File node type
        assert EnumOnexTreeNodeType.FILE.value == "file"

        # Directory node type
        assert EnumOnexTreeNodeType.DIRECTORY.value == "directory"

    def test_enum_node_categories(self):
        """Test node categories"""
        # File nodes
        file_nodes = {EnumOnexTreeNodeType.FILE}

        # Directory nodes
        directory_nodes = {EnumOnexTreeNodeType.DIRECTORY}

        all_nodes = set(EnumOnexTreeNodeType)
        assert file_nodes.union(directory_nodes) == all_nodes

    def test_enum_filesystem_types(self):
        """Test filesystem type categorization"""
        # File system entities
        filesystem_entities = {
            EnumOnexTreeNodeType.FILE,
            EnumOnexTreeNodeType.DIRECTORY,
        }

        assert filesystem_entities == set(EnumOnexTreeNodeType)
