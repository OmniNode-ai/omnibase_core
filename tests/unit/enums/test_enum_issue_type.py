# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for enum_issue_type.py"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_issue_type import EnumIssueType


@pytest.mark.unit
class TestEnumIssueType:
    """Test cases for EnumIssueType"""

    def test_enum_values(self):
        """Test that all enum values are correct"""
        assert EnumIssueType.TEMPLATE_ARTIFACT == "template_artifact"
        assert EnumIssueType.INCORRECT_NODE_NAME == "incorrect_node_name"
        assert EnumIssueType.PARSE_ERROR == "parse_error"
        assert EnumIssueType.TODO_FOUND == "todo_found"
        assert EnumIssueType.INCORRECT_CLASS_NAME == "incorrect_class_name"
        assert EnumIssueType.INCORRECT_ENUM_NAME == "incorrect_enum_name"
        assert EnumIssueType.INCORRECT_MODEL_NAME == "incorrect_model_name"
        assert EnumIssueType.INCORRECT_TITLE == "incorrect_title"
        assert EnumIssueType.MISSING_DIRECTORY == "missing_directory"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum"""
        assert issubclass(EnumIssueType, str)
        assert issubclass(EnumIssueType, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values"""
        assert EnumIssueType.TEMPLATE_ARTIFACT == "template_artifact"
        assert EnumIssueType.PARSE_ERROR == "parse_error"
        assert EnumIssueType.TODO_FOUND == "todo_found"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values"""
        values = list(EnumIssueType)
        assert len(values) == 9
        assert EnumIssueType.TEMPLATE_ARTIFACT in values
        assert EnumIssueType.MISSING_DIRECTORY in values

    def test_enum_membership(self):
        """Test membership testing"""
        assert EnumIssueType.TEMPLATE_ARTIFACT in EnumIssueType
        assert "template_artifact" in EnumIssueType
        assert "invalid_value" not in EnumIssueType

    def test_enum_comparison(self):
        """Test enum comparison"""
        assert EnumIssueType.TEMPLATE_ARTIFACT == EnumIssueType.TEMPLATE_ARTIFACT
        assert EnumIssueType.PARSE_ERROR != EnumIssueType.TODO_FOUND
        assert EnumIssueType.TEMPLATE_ARTIFACT == "template_artifact"

    def test_enum_serialization(self):
        """Test enum serialization"""
        assert EnumIssueType.TEMPLATE_ARTIFACT.value == "template_artifact"
        assert EnumIssueType.PARSE_ERROR.value == "parse_error"

    def test_enum_deserialization(self):
        """Test enum deserialization"""
        assert EnumIssueType("template_artifact") == EnumIssueType.TEMPLATE_ARTIFACT
        assert EnumIssueType("parse_error") == EnumIssueType.PARSE_ERROR

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError"""
        with pytest.raises(ValueError):
            EnumIssueType("invalid_value")

        with pytest.raises(ValueError):
            EnumIssueType("")

    def test_enum_all_values(self):
        """Test that all expected values are present"""
        expected_values = {
            "template_artifact",
            "incorrect_node_name",
            "parse_error",
            "todo_found",
            "incorrect_class_name",
            "incorrect_enum_name",
            "incorrect_model_name",
            "incorrect_title",
            "missing_directory",
        }
        actual_values = {member.value for member in EnumIssueType}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring"""
        assert "Template validation issue types" in EnumIssueType.__doc__

    def test_enum_issue_categories(self):
        """Test specific issue type categories"""
        # Template-related issues
        assert EnumIssueType.TEMPLATE_ARTIFACT.value == "template_artifact"

        # Naming-related issues
        assert EnumIssueType.INCORRECT_NODE_NAME.value == "incorrect_node_name"
        assert EnumIssueType.INCORRECT_CLASS_NAME.value == "incorrect_class_name"
        assert EnumIssueType.INCORRECT_ENUM_NAME.value == "incorrect_enum_name"
        assert EnumIssueType.INCORRECT_MODEL_NAME.value == "incorrect_model_name"
        assert EnumIssueType.INCORRECT_TITLE.value == "incorrect_title"

        # Error-related issues
        assert EnumIssueType.PARSE_ERROR.value == "parse_error"

        # Development-related issues
        assert EnumIssueType.TODO_FOUND.value == "todo_found"

        # Structure-related issues
        assert EnumIssueType.MISSING_DIRECTORY.value == "missing_directory"
