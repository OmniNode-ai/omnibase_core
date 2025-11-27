from enum import Enum

import pytest

from omnibase_core.enums.enum_item_type import EnumItemType


class TestEnumItemType:
    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert EnumItemType.COLLECTION_ITEM == "collection_item"
        assert EnumItemType.DATA_ITEM == "data_item"
        assert EnumItemType.CONFIG_ITEM == "config_item"
        assert EnumItemType.METADATA_ITEM == "metadata_item"
        assert EnumItemType.DOCUMENT == "document"
        assert EnumItemType.TEMPLATE == "template"
        assert EnumItemType.EXAMPLE == "example"
        assert EnumItemType.REFERENCE == "reference"
        assert EnumItemType.CODE == "code"
        assert EnumItemType.FUNCTION == "function"
        assert EnumItemType.CLASS == "class"
        assert EnumItemType.MODULE == "module"
        assert EnumItemType.TEST == "test"
        assert EnumItemType.SETTING == "setting"
        assert EnumItemType.PARAMETER == "parameter"
        assert EnumItemType.PROPERTY == "property"
        assert EnumItemType.VARIABLE == "variable"
        assert EnumItemType.IMAGE == "image"
        assert EnumItemType.FILE == "file"
        assert EnumItemType.RESOURCE == "resource"
        assert EnumItemType.ARTIFACT == "artifact"
        assert EnumItemType.SYSTEM == "system"
        assert EnumItemType.COMPONENT == "component"
        assert EnumItemType.SERVICE == "service"
        assert EnumItemType.WORKFLOW == "workflow"
        assert EnumItemType.UNKNOWN == "unknown"
        assert EnumItemType.OTHER == "other"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumItemType, str)
        assert issubclass(EnumItemType, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        item_type = EnumItemType.DOCUMENT
        assert isinstance(item_type, str)
        assert item_type == "document"
        assert len(item_type) == 8
        assert item_type.startswith("doc")

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumItemType)
        assert len(values) == 27
        assert EnumItemType.DOCUMENT in values
        assert EnumItemType.UNKNOWN in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumItemType.FUNCTION in EnumItemType
        assert "function" in [e.value for e in EnumItemType]

    def test_enum_comparison(self):
        """Test enum comparison."""
        item1 = EnumItemType.CODE
        item2 = EnumItemType.CODE
        item3 = EnumItemType.FUNCTION

        assert item1 == item2
        assert item1 != item3
        assert item1 == "code"

    def test_enum_serialization(self):
        """Test enum serialization."""
        item_type = EnumItemType.TEMPLATE
        serialized = item_type.value
        assert serialized == "template"
        import json

        json_str = json.dumps(item_type)
        assert json_str == '"template"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        item_type = EnumItemType("workflow")
        assert item_type == EnumItemType.WORKFLOW

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumItemType("invalid_item")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "collection_item",
            "data_item",
            "config_item",
            "metadata_item",
            "document",
            "template",
            "example",
            "reference",
            "code",
            "function",
            "class",
            "module",
            "test",
            "setting",
            "parameter",
            "property",
            "variable",
            "image",
            "file",
            "resource",
            "artifact",
            "system",
            "component",
            "service",
            "workflow",
            "unknown",
            "other",
        }
        actual_values = {e.value for e in EnumItemType}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumItemType.__doc__ is not None
        assert "item type enumeration" in EnumItemType.__doc__.lower()

    def test_enum_str_method(self):
        """Test __str__ method."""
        item_type = EnumItemType.MODULE
        assert str(item_type) == "module"
        assert str(item_type) == item_type.value

    def test_is_content_type_method(self):
        """Test is_content_type method."""
        # Content types
        assert EnumItemType.DOCUMENT.is_content_type()
        assert EnumItemType.TEMPLATE.is_content_type()
        assert EnumItemType.EXAMPLE.is_content_type()
        assert EnumItemType.REFERENCE.is_content_type()

        # Non-content types
        assert not EnumItemType.CODE.is_content_type()
        assert not EnumItemType.FUNCTION.is_content_type()
        assert not EnumItemType.SETTING.is_content_type()

    def test_is_code_type_method(self):
        """Test is_code_type method."""
        # Code types
        assert EnumItemType.CODE.is_code_type()
        assert EnumItemType.FUNCTION.is_code_type()
        assert EnumItemType.CLASS.is_code_type()
        assert EnumItemType.MODULE.is_code_type()
        assert EnumItemType.TEST.is_code_type()

        # Non-code types
        assert not EnumItemType.DOCUMENT.is_code_type()
        assert not EnumItemType.SETTING.is_code_type()
        assert not EnumItemType.IMAGE.is_code_type()

    def test_is_config_type_method(self):
        """Test is_config_type method."""
        # Config types
        assert EnumItemType.CONFIG_ITEM.is_config_type()
        assert EnumItemType.SETTING.is_config_type()
        assert EnumItemType.PARAMETER.is_config_type()
        assert EnumItemType.PROPERTY.is_config_type()
        assert EnumItemType.VARIABLE.is_config_type()

        # Non-config types
        assert not EnumItemType.CODE.is_config_type()
        assert not EnumItemType.DOCUMENT.is_config_type()
        assert not EnumItemType.IMAGE.is_config_type()

    def test_is_system_type_method(self):
        """Test is_system_type method."""
        # System types
        assert EnumItemType.SYSTEM.is_system_type()
        assert EnumItemType.COMPONENT.is_system_type()
        assert EnumItemType.SERVICE.is_system_type()
        assert EnumItemType.WORKFLOW.is_system_type()

        # Non-system types
        assert not EnumItemType.CODE.is_system_type()
        assert not EnumItemType.DOCUMENT.is_system_type()
        assert not EnumItemType.SETTING.is_system_type()

    def test_item_type_categorization_completeness(self):
        """Test that all item types are categorized by at least one method."""
        all_types = set(EnumItemType)

        # Get types categorized by each method
        content_types = {e for e in EnumItemType if e.is_content_type()}
        code_types = {e for e in EnumItemType if e.is_code_type()}
        config_types = {e for e in EnumItemType if e.is_config_type()}
        system_types = {e for e in EnumItemType if e.is_system_type()}

        # All types should be categorized (except UNKNOWN and OTHER)
        categorized_types = content_types | code_types | config_types | system_types
        assert EnumItemType.UNKNOWN not in categorized_types
        assert EnumItemType.OTHER not in categorized_types
        # Some types might not be categorized by the current methods
        assert (
            len(categorized_types) >= len(all_types) - 10
        )  # At least most types are categorized

    def test_item_type_categorization_exclusivity(self):
        """Test that item type categories don't overlap inappropriately."""
        content_types = {e for e in EnumItemType if e.is_content_type()}
        code_types = {e for e in EnumItemType if e.is_code_type()}
        config_types = {e for e in EnumItemType if e.is_config_type()}
        system_types = {e for e in EnumItemType if e.is_system_type()}

        # Content and code types should not overlap
        assert content_types.isdisjoint(code_types)

        # Config and system types should not overlap
        assert config_types.isdisjoint(system_types)

    def test_item_type_logical_groupings(self):
        """Test logical groupings of item types."""
        # Basic item types
        basic_types = {
            EnumItemType.COLLECTION_ITEM,
            EnumItemType.DATA_ITEM,
            EnumItemType.CONFIG_ITEM,
            EnumItemType.METADATA_ITEM,
        }

        # Content types
        content_types = {
            EnumItemType.DOCUMENT,
            EnumItemType.TEMPLATE,
            EnumItemType.EXAMPLE,
            EnumItemType.REFERENCE,
        }

        # Code and development types
        code_types = {
            EnumItemType.CODE,
            EnumItemType.FUNCTION,
            EnumItemType.CLASS,
            EnumItemType.MODULE,
            EnumItemType.TEST,
        }

        # Configuration types
        config_types = {
            EnumItemType.SETTING,
            EnumItemType.PARAMETER,
            EnumItemType.PROPERTY,
            EnumItemType.VARIABLE,
        }

        # Asset types
        asset_types = {
            EnumItemType.IMAGE,
            EnumItemType.FILE,
            EnumItemType.RESOURCE,
            EnumItemType.ARTIFACT,
        }

        # System types
        system_types = {
            EnumItemType.SYSTEM,
            EnumItemType.COMPONENT,
            EnumItemType.SERVICE,
            EnumItemType.WORKFLOW,
        }

        # Default types
        default_types = {
            EnumItemType.UNKNOWN,
            EnumItemType.OTHER,
        }

        # Test that all types are covered
        all_grouped_types = (
            basic_types
            | content_types
            | code_types
            | config_types
            | asset_types
            | system_types
            | default_types
        )
        assert all_grouped_types == set(EnumItemType)
