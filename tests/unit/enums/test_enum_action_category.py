"""
Unit tests for EnumActionCategory.

Tests all aspects of the action category enum including:
- Enum value validation
- Helper methods
- String representation
- Categorization logic
"""

import pytest

from omnibase_core.enums.enum_action_category import EnumActionCategory


class TestEnumActionCategory:
    """Test cases for EnumActionCategory."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "LIFECYCLE": "lifecycle",
            "VALIDATION": "validation",
            "INTROSPECTION": "introspection",
            "CONFIGURATION": "configuration",
            "EXECUTION": "execution",
            "REGISTRY": "registry",
            "WORKFLOW": "workflow",
            "SYSTEM": "system",
        }

        for name, value in expected_values.items():
            category = getattr(EnumActionCategory, name)
            assert category.value == value
            assert str(category) == value

    def test_string_representation(self):
        """Test string representation of enum values."""
        assert str(EnumActionCategory.LIFECYCLE) == "lifecycle"
        assert str(EnumActionCategory.VALIDATION) == "validation"
        assert str(EnumActionCategory.CONFIGURATION) == "configuration"

    def test_is_management_category(self):
        """Test the is_management_category helper method."""
        # Management categories
        management_categories = [
            EnumActionCategory.LIFECYCLE,
            EnumActionCategory.CONFIGURATION,
            EnumActionCategory.REGISTRY,
        ]

        for category in management_categories:
            assert category.is_management_category() is True

        # Non-management categories
        non_management_categories = [
            EnumActionCategory.VALIDATION,
            EnumActionCategory.INTROSPECTION,
            EnumActionCategory.EXECUTION,
            EnumActionCategory.WORKFLOW,
            EnumActionCategory.SYSTEM,
        ]

        for category in non_management_categories:
            assert category.is_management_category() is False

    def test_is_execution_category(self):
        """Test the is_execution_category helper method."""
        # Execution categories
        execution_categories = [
            EnumActionCategory.EXECUTION,
            EnumActionCategory.WORKFLOW,
            EnumActionCategory.SYSTEM,
        ]

        for category in execution_categories:
            assert category.is_execution_category() is True

        # Non-execution categories
        non_execution_categories = [
            EnumActionCategory.LIFECYCLE,
            EnumActionCategory.VALIDATION,
            EnumActionCategory.INTROSPECTION,
            EnumActionCategory.CONFIGURATION,
            EnumActionCategory.REGISTRY,
        ]

        for category in non_execution_categories:
            assert category.is_execution_category() is False

    def test_is_inspection_category(self):
        """Test the is_inspection_category helper method."""
        # Inspection categories
        inspection_categories = [
            EnumActionCategory.VALIDATION,
            EnumActionCategory.INTROSPECTION,
        ]

        for category in inspection_categories:
            assert category.is_inspection_category() is True

        # Non-inspection categories
        non_inspection_categories = [
            EnumActionCategory.LIFECYCLE,
            EnumActionCategory.CONFIGURATION,
            EnumActionCategory.EXECUTION,
            EnumActionCategory.REGISTRY,
            EnumActionCategory.WORKFLOW,
            EnumActionCategory.SYSTEM,
        ]

        for category in non_inspection_categories:
            assert category.is_inspection_category() is False

    def test_enum_equality(self):
        """Test enum equality comparison."""
        assert EnumActionCategory.LIFECYCLE == EnumActionCategory.LIFECYCLE
        assert EnumActionCategory.VALIDATION != EnumActionCategory.EXECUTION

    def test_enum_membership(self):
        """Test enum membership checking."""
        all_categories = [
            EnumActionCategory.LIFECYCLE,
            EnumActionCategory.VALIDATION,
            EnumActionCategory.INTROSPECTION,
            EnumActionCategory.CONFIGURATION,
            EnumActionCategory.EXECUTION,
            EnumActionCategory.REGISTRY,
            EnumActionCategory.WORKFLOW,
            EnumActionCategory.SYSTEM,
        ]

        for category in all_categories:
            assert category in EnumActionCategory

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        categories = list(EnumActionCategory)
        assert len(categories) == 8

        category_values = [cat.value for cat in categories]
        expected_values = [
            "lifecycle",
            "validation",
            "introspection",
            "configuration",
            "execution",
            "registry",
            "workflow",
            "system",
        ]

        assert set(category_values) == set(expected_values)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
