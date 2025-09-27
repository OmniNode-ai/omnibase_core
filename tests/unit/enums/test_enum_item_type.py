"""
Unit tests for EnumItemType.

Tests the item type enumeration for consistency, completeness, and functionality.
"""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_item_type import EnumItemType


class TestEnumItemType:
    """Test suite for EnumItemType enumeration."""

    def test_enum_values_exist(self) -> None:
        """Test that all expected enum values exist."""
        expected_values = {
            "COLLECTION_ITEM",
            "DATA_ITEM",
            "CONFIG_ITEM",
            "METADATA_ITEM",
            "DOCUMENT",
            "TEMPLATE",
            "EXAMPLE",
            "REFERENCE",
            "CODE",
            "FUNCTION",
            "CLASS",
            "MODULE",
            "TEST",
            "SETTING",
            "PARAMETER",
            "PROPERTY",
            "VARIABLE",
            "IMAGE",
            "FILE",
            "RESOURCE",
            "ARTIFACT",
            "SYSTEM",
            "COMPONENT",
            "SERVICE",
            "WORKFLOW",
            "UNKNOWN",
            "OTHER",
        }

        actual_values = {item.name for item in EnumItemType}
        assert actual_values == expected_values

    def test_enum_string_values(self) -> None:
        """Test that enum values map to expected strings."""
        assert EnumItemType.COLLECTION_ITEM.value == "collection_item"
        assert EnumItemType.DATA_ITEM.value == "data_item"
        assert EnumItemType.CONFIG_ITEM.value == "config_item"
        assert EnumItemType.METADATA_ITEM.value == "metadata_item"
        assert EnumItemType.DOCUMENT.value == "document"
        assert EnumItemType.TEMPLATE.value == "template"
        assert EnumItemType.EXAMPLE.value == "example"
        assert EnumItemType.REFERENCE.value == "reference"
        assert EnumItemType.CODE.value == "code"
        assert EnumItemType.FUNCTION.value == "function"
        assert EnumItemType.CLASS.value == "class"
        assert EnumItemType.MODULE.value == "module"
        assert EnumItemType.TEST.value == "test"
        assert EnumItemType.SETTING.value == "setting"
        assert EnumItemType.PARAMETER.value == "parameter"
        assert EnumItemType.PROPERTY.value == "property"
        assert EnumItemType.VARIABLE.value == "variable"
        assert EnumItemType.IMAGE.value == "image"
        assert EnumItemType.FILE.value == "file"
        assert EnumItemType.RESOURCE.value == "resource"
        assert EnumItemType.ARTIFACT.value == "artifact"
        assert EnumItemType.SYSTEM.value == "system"
        assert EnumItemType.COMPONENT.value == "component"
        assert EnumItemType.SERVICE.value == "service"
        assert EnumItemType.WORKFLOW.value == "workflow"
        assert EnumItemType.UNKNOWN.value == "unknown"
        assert EnumItemType.OTHER.value == "other"

    def test_enum_string_behavior(self) -> None:
        """Test that enum can be used as string."""
        assert str(EnumItemType.DATA_ITEM) == "data_item"
        assert EnumItemType.FUNCTION == "function"
        assert f"{EnumItemType.CODE}" == "code"

    def test_enum_creation_from_string(self) -> None:
        """Test creating enum instances from string values."""
        assert EnumItemType("collection_item") == EnumItemType.COLLECTION_ITEM
        assert EnumItemType("function") == EnumItemType.FUNCTION
        assert EnumItemType("unknown") == EnumItemType.UNKNOWN

    def test_enum_creation_from_invalid_string(self) -> None:
        """Test that invalid strings raise ValueError."""
        with pytest.raises(ValueError):
            EnumItemType("invalid_type")

        with pytest.raises(ValueError):
            EnumItemType("not_a_type")

    def test_is_content_type(self) -> None:
        """Test is_content_type helper method."""
        # Content types
        assert EnumItemType.DOCUMENT.is_content_type()
        assert EnumItemType.TEMPLATE.is_content_type()
        assert EnumItemType.EXAMPLE.is_content_type()
        assert EnumItemType.REFERENCE.is_content_type()

        # Non-content types
        assert not EnumItemType.FUNCTION.is_content_type()
        assert not EnumItemType.DATA_ITEM.is_content_type()
        assert not EnumItemType.SYSTEM.is_content_type()

    def test_is_code_type(self) -> None:
        """Test is_code_type helper method."""
        # Code types
        assert EnumItemType.CODE.is_code_type()
        assert EnumItemType.FUNCTION.is_code_type()
        assert EnumItemType.CLASS.is_code_type()
        assert EnumItemType.MODULE.is_code_type()
        assert EnumItemType.TEST.is_code_type()

        # Non-code types
        assert not EnumItemType.DOCUMENT.is_code_type()
        assert not EnumItemType.DATA_ITEM.is_code_type()
        assert not EnumItemType.SYSTEM.is_code_type()

    def test_is_config_type(self) -> None:
        """Test is_config_type helper method."""
        # Config types
        assert EnumItemType.CONFIG_ITEM.is_config_type()
        assert EnumItemType.SETTING.is_config_type()
        assert EnumItemType.PARAMETER.is_config_type()
        assert EnumItemType.PROPERTY.is_config_type()
        assert EnumItemType.VARIABLE.is_config_type()

        # Non-config types
        assert not EnumItemType.FUNCTION.is_config_type()
        assert not EnumItemType.DOCUMENT.is_config_type()
        assert not EnumItemType.SYSTEM.is_config_type()

    def test_is_system_type(self) -> None:
        """Test is_system_type helper method."""
        # System types
        assert EnumItemType.SYSTEM.is_system_type()
        assert EnumItemType.COMPONENT.is_system_type()
        assert EnumItemType.SERVICE.is_system_type()
        assert EnumItemType.WORKFLOW.is_system_type()

        # Non-system types
        assert not EnumItemType.FUNCTION.is_system_type()
        assert not EnumItemType.DOCUMENT.is_system_type()
        assert not EnumItemType.CONFIG_ITEM.is_system_type()

    def test_enum_uniqueness(self) -> None:
        """Test that all enum values are unique."""
        values = [item.value for item in EnumItemType]
        assert len(values) == len(set(values))

    def test_enum_coverage(self) -> None:
        """Test that enum covers all major item type categories."""
        # Basic item types
        basic_types = {
            EnumItemType.COLLECTION_ITEM,
            EnumItemType.DATA_ITEM,
            EnumItemType.CONFIG_ITEM,
            EnumItemType.METADATA_ITEM,
        }
        assert len(basic_types) == 4

        # Content types
        content_types = {
            EnumItemType.DOCUMENT,
            EnumItemType.TEMPLATE,
            EnumItemType.EXAMPLE,
            EnumItemType.REFERENCE,
        }
        assert len(content_types) == 4

        # Code types
        code_types = {
            EnumItemType.CODE,
            EnumItemType.FUNCTION,
            EnumItemType.CLASS,
            EnumItemType.MODULE,
            EnumItemType.TEST,
        }
        assert len(code_types) == 5

        # Default types
        assert EnumItemType.UNKNOWN in EnumItemType
        assert EnumItemType.OTHER in EnumItemType

    def test_enum_consistency_with_helpers(self) -> None:
        """Test that helper methods are consistent with enum categorization."""
        for item_type in EnumItemType:
            # Each item should belong to at most one primary category
            categories = [
                item_type.is_content_type(),
                item_type.is_code_type(),
                item_type.is_config_type(),
                item_type.is_system_type(),
            ]

            # Allow items to belong to zero or one category
            assert sum(categories) <= 1, f"{item_type} belongs to multiple categories"
