"""Tests for enum_issue_type.py"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_issue_type import EnumIssueTypeEnum


class TestEnumIssueTypeEnum:
    """Test cases for EnumIssueTypeEnum"""

    def test_enum_values(self):
        """Test that all enum values are correct"""
        assert EnumIssueTypeEnum.TEMPLATE_ARTIFACT == "template_artifact"
        assert EnumIssueTypeEnum.INCORRECT_NODE_NAME == "incorrect_node_name"
        assert EnumIssueTypeEnum.PARSE_ERROR == "parse_error"
        assert EnumIssueTypeEnum.TODO_FOUND == "todo_found"
        assert EnumIssueTypeEnum.INCORRECT_CLASS_NAME == "incorrect_class_name"
        assert EnumIssueTypeEnum.INCORRECT_ENUM_NAME == "incorrect_enum_name"
        assert EnumIssueTypeEnum.INCORRECT_MODEL_NAME == "incorrect_model_name"
        assert EnumIssueTypeEnum.INCORRECT_TITLE == "incorrect_title"
        assert EnumIssueTypeEnum.MISSING_DIRECTORY == "missing_directory"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum"""
        assert issubclass(EnumIssueTypeEnum, str)
        assert issubclass(EnumIssueTypeEnum, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values"""
        assert EnumIssueTypeEnum.TEMPLATE_ARTIFACT == "template_artifact"
        assert EnumIssueTypeEnum.PARSE_ERROR == "parse_error"
        assert EnumIssueTypeEnum.TODO_FOUND == "todo_found"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values"""
        values = list(EnumIssueTypeEnum)
        assert len(values) == 9
        assert EnumIssueTypeEnum.TEMPLATE_ARTIFACT in values
        assert EnumIssueTypeEnum.MISSING_DIRECTORY in values

    def test_enum_membership(self):
        """Test membership testing"""
        assert EnumIssueTypeEnum.TEMPLATE_ARTIFACT in EnumIssueTypeEnum
        assert "template_artifact" in EnumIssueTypeEnum
        assert "invalid_value" not in EnumIssueTypeEnum

    def test_enum_comparison(self):
        """Test enum comparison"""
        assert (
            EnumIssueTypeEnum.TEMPLATE_ARTIFACT == EnumIssueTypeEnum.TEMPLATE_ARTIFACT
        )
        assert EnumIssueTypeEnum.PARSE_ERROR != EnumIssueTypeEnum.TODO_FOUND
        assert EnumIssueTypeEnum.TEMPLATE_ARTIFACT == "template_artifact"

    def test_enum_serialization(self):
        """Test enum serialization"""
        assert EnumIssueTypeEnum.TEMPLATE_ARTIFACT.value == "template_artifact"
        assert EnumIssueTypeEnum.PARSE_ERROR.value == "parse_error"

    def test_enum_deserialization(self):
        """Test enum deserialization"""
        assert (
            EnumIssueTypeEnum("template_artifact")
            == EnumIssueTypeEnum.TEMPLATE_ARTIFACT
        )
        assert EnumIssueTypeEnum("parse_error") == EnumIssueTypeEnum.PARSE_ERROR

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError"""
        with pytest.raises(ValueError):
            EnumIssueTypeEnum("invalid_value")

        with pytest.raises(ValueError):
            EnumIssueTypeEnum("")

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
        actual_values = {member.value for member in EnumIssueTypeEnum}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring"""
        assert "Template validation issue types" in EnumIssueTypeEnum.__doc__

    def test_enum_issue_categories(self):
        """Test specific issue type categories"""
        # Template-related issues
        assert EnumIssueTypeEnum.TEMPLATE_ARTIFACT.value == "template_artifact"

        # Naming-related issues
        assert EnumIssueTypeEnum.INCORRECT_NODE_NAME.value == "incorrect_node_name"
        assert EnumIssueTypeEnum.INCORRECT_CLASS_NAME.value == "incorrect_class_name"
        assert EnumIssueTypeEnum.INCORRECT_ENUM_NAME.value == "incorrect_enum_name"
        assert EnumIssueTypeEnum.INCORRECT_MODEL_NAME.value == "incorrect_model_name"
        assert EnumIssueTypeEnum.INCORRECT_TITLE.value == "incorrect_title"

        # Error-related issues
        assert EnumIssueTypeEnum.PARSE_ERROR.value == "parse_error"

        # Development-related issues
        assert EnumIssueTypeEnum.TODO_FOUND.value == "todo_found"

        # Structure-related issues
        assert EnumIssueTypeEnum.MISSING_DIRECTORY.value == "missing_directory"
