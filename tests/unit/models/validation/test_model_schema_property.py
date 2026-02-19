# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Test suite for ModelSchemaProperty - individual schema property model.

This test suite covers ModelSchemaProperty with all its fields and nested structures.
"""

from __future__ import annotations

import pytest

from omnibase_core.models.validation.model_schema_property import ModelSchemaProperty


@pytest.mark.unit
class TestModelSchemaPropertyInstantiation:
    """Test basic ModelSchemaProperty instantiation."""

    def test_default_initialization(self):
        """Test ModelSchemaProperty initializes with all None values."""
        prop = ModelSchemaProperty()
        assert prop.type is None
        assert prop.title is None
        assert prop.description is None
        assert prop.default is None
        assert prop.enum is None
        assert prop.format is None
        assert prop.items is None
        assert prop.properties is None
        assert prop.required is None

    def test_string_property(self):
        """Test simple string property."""
        prop = ModelSchemaProperty(
            type="string",
            title="Name",
            description="User's name",
        )
        assert prop.type == "string"
        assert prop.title == "Name"
        assert prop.description == "User's name"

    def test_integer_property(self):
        """Test integer property with default."""
        prop = ModelSchemaProperty(
            type="integer",
            title="Age",
            default=0,
        )
        assert prop.type == "integer"
        assert prop.title == "Age"
        assert prop.default == 0

    def test_boolean_property(self):
        """Test boolean property."""
        prop = ModelSchemaProperty(
            type="boolean",
            title="Active",
            default=True,
        )
        assert prop.type == "boolean"
        assert prop.default is True

    def test_number_property(self):
        """Test number/float property."""
        prop = ModelSchemaProperty(
            type="number",
            title="Score",
            default=0.0,
        )
        assert prop.type == "number"
        assert prop.default == 0.0


@pytest.mark.unit
class TestModelSchemaPropertyWithEnum:
    """Test ModelSchemaProperty with enum values."""

    def test_string_enum(self):
        """Test property with string enum values."""
        prop = ModelSchemaProperty(
            type="string",
            title="Status",
            enum=["active", "inactive", "pending"],
        )
        assert prop.enum is not None
        assert len(prop.enum) == 3
        assert "active" in prop.enum
        assert "inactive" in prop.enum
        assert "pending" in prop.enum

    def test_integer_enum(self):
        """Test property with integer enum values."""
        prop = ModelSchemaProperty(
            type="integer",
            enum=[1, 2, 3, 5, 8],
        )
        assert prop.enum is not None
        assert len(prop.enum) == 5
        assert 1 in prop.enum
        assert 8 in prop.enum

    def test_mixed_enum(self):
        """Test property with mixed type enum values."""
        prop = ModelSchemaProperty(
            enum=["red", 1, True, 3.14],
        )
        assert prop.enum is not None
        assert len(prop.enum) == 4
        assert "red" in prop.enum
        assert 1 in prop.enum
        assert True in prop.enum
        assert 3.14 in prop.enum

    def test_empty_enum(self):
        """Test property with empty enum list."""
        prop = ModelSchemaProperty(enum=[])
        assert prop.enum is not None
        assert len(prop.enum) == 0


@pytest.mark.unit
class TestModelSchemaPropertyWithFormat:
    """Test ModelSchemaProperty with format specifiers."""

    def test_email_format(self):
        """Test string property with email format."""
        prop = ModelSchemaProperty(
            type="string",
            format="email",
        )
        assert prop.format == "email"

    def test_datetime_format(self):
        """Test string property with date-time format."""
        prop = ModelSchemaProperty(
            type="string",
            format="date-time",
        )
        assert prop.format == "date-time"

    def test_uri_format(self):
        """Test string property with URI format."""
        prop = ModelSchemaProperty(
            type="string",
            format="uri",
        )
        assert prop.format == "uri"

    def test_uuid_format(self):
        """Test string property with UUID format."""
        prop = ModelSchemaProperty(
            type="string",
            format="uuid",
        )
        assert prop.format == "uuid"

    def test_custom_format(self):
        """Test property with custom format."""
        prop = ModelSchemaProperty(
            type="string",
            format="custom-format",
        )
        assert prop.format == "custom-format"


@pytest.mark.unit
class TestModelSchemaPropertyArrayType:
    """Test ModelSchemaProperty with array type."""

    def test_array_of_strings(self):
        """Test array property with string items."""
        prop = ModelSchemaProperty(
            type="array",
            items=ModelSchemaProperty(type="string"),
        )
        assert prop.type == "array"
        assert prop.items is not None
        assert prop.items.type == "string"

    def test_array_of_integers(self):
        """Test array property with integer items."""
        prop = ModelSchemaProperty(
            type="array",
            items=ModelSchemaProperty(type="integer"),
        )
        assert prop.items is not None
        assert prop.items.type == "integer"

    def test_array_of_objects(self):
        """Test array property with object items."""
        from omnibase_core.models.validation.model_schema_properties_model import (
            ModelSchemaPropertiesModel,
        )

        item_props = ModelSchemaPropertiesModel(
            root={
                "id": ModelSchemaProperty(type="integer"),
                "name": ModelSchemaProperty(type="string"),
            }
        )

        prop = ModelSchemaProperty(
            type="array",
            items=ModelSchemaProperty(type="object", properties=item_props),
        )

        assert prop.type == "array"
        assert prop.items is not None
        assert prop.items.type == "object"
        assert prop.items.properties is not None

    def test_array_without_items(self):
        """Test array property without items specification."""
        prop = ModelSchemaProperty(type="array")
        assert prop.type == "array"
        assert prop.items is None

    def test_nested_array(self):
        """Test array of arrays."""
        prop = ModelSchemaProperty(
            type="array",
            items=ModelSchemaProperty(
                type="array",
                items=ModelSchemaProperty(type="string"),
            ),
        )

        assert prop.type == "array"
        assert prop.items is not None
        assert prop.items.type == "array"
        assert prop.items.items is not None
        assert prop.items.items.type == "string"


@pytest.mark.unit
class TestModelSchemaPropertyObjectType:
    """Test ModelSchemaProperty with object type."""

    def test_object_with_properties(self):
        """Test object property with nested properties."""
        from omnibase_core.models.validation.model_schema_properties_model import (
            ModelSchemaPropertiesModel,
        )

        nested_props = ModelSchemaPropertiesModel(
            root={
                "street": ModelSchemaProperty(type="string"),
                "city": ModelSchemaProperty(type="string"),
                "zip": ModelSchemaProperty(type="string"),
            }
        )

        prop = ModelSchemaProperty(
            type="object",
            properties=nested_props,
        )

        assert prop.type == "object"
        assert prop.properties is not None
        assert len(prop.properties.root) == 3
        assert "street" in prop.properties.root

    def test_object_with_required_fields(self):
        """Test object property with required fields."""
        from omnibase_core.models.validation.model_required_fields_model import (
            ModelRequiredFieldsModel,
        )
        from omnibase_core.models.validation.model_schema_properties_model import (
            ModelSchemaPropertiesModel,
        )

        nested_props = ModelSchemaPropertiesModel(
            root={
                "name": ModelSchemaProperty(type="string"),
                "age": ModelSchemaProperty(type="integer"),
            }
        )

        required = ModelRequiredFieldsModel(root=["name"])

        prop = ModelSchemaProperty(
            type="object",
            properties=nested_props,
            required=required,
        )

        assert prop.type == "object"
        assert prop.properties is not None
        assert prop.required is not None
        assert "name" in prop.required.root

    def test_nested_objects(self):
        """Test deeply nested object properties."""
        from omnibase_core.models.validation.model_schema_properties_model import (
            ModelSchemaPropertiesModel,
        )

        level2_props = ModelSchemaPropertiesModel(
            root={"value": ModelSchemaProperty(type="string")}
        )

        level1_props = ModelSchemaPropertiesModel(
            root={"nested": ModelSchemaProperty(type="object", properties=level2_props)}
        )

        prop = ModelSchemaProperty(
            type="object",
            properties=level1_props,
        )

        assert prop.type == "object"
        assert prop.properties is not None
        assert "nested" in prop.properties.root
        nested_prop = prop.properties.root["nested"]
        assert nested_prop.type == "object"
        assert nested_prop.properties is not None


@pytest.mark.unit
class TestModelSchemaPropertyDefaultValues:
    """Test ModelSchemaProperty with various default values."""

    def test_string_default(self):
        """Test property with string default."""
        prop = ModelSchemaProperty(
            type="string",
            default="default value",
        )
        assert prop.default == "default value"

    def test_integer_default(self):
        """Test property with integer default."""
        prop = ModelSchemaProperty(
            type="integer",
            default=42,
        )
        assert prop.default == 42

    def test_float_default(self):
        """Test property with float default."""
        prop = ModelSchemaProperty(
            type="number",
            default=3.14,
        )
        assert prop.default == 3.14

    def test_boolean_default_true(self):
        """Test property with boolean default True."""
        prop = ModelSchemaProperty(
            type="boolean",
            default=True,
        )
        assert prop.default is True

    def test_boolean_default_false(self):
        """Test property with boolean default False."""
        prop = ModelSchemaProperty(
            type="boolean",
            default=False,
        )
        assert prop.default is False

    def test_list_default(self):
        """Test property with list default."""
        prop = ModelSchemaProperty(
            type="array",
            default=["item1", "item2"],
        )
        assert isinstance(prop.default, list)
        assert len(prop.default) == 2
        assert "item1" in prop.default

    def test_dict_default(self):
        """Test property with dict default."""
        prop = ModelSchemaProperty(
            type="object",
            default={"key": "value"},
        )
        assert isinstance(prop.default, dict)
        assert prop.default["key"] == "value"

    def test_none_default(self):
        """Test property with None default."""
        prop = ModelSchemaProperty(
            type="string",
            default=None,
        )
        assert prop.default is None

    def test_zero_defaults(self):
        """Test properties with zero as default."""
        int_prop = ModelSchemaProperty(type="integer", default=0)
        float_prop = ModelSchemaProperty(type="number", default=0.0)

        assert int_prop.default == 0
        assert float_prop.default == 0.0

    def test_empty_string_default(self):
        """Test property with empty string default."""
        prop = ModelSchemaProperty(
            type="string",
            default="",
        )
        assert prop.default == ""

    def test_empty_list_default(self):
        """Test property with empty list default."""
        prop = ModelSchemaProperty(
            type="array",
            default=[],
        )
        assert isinstance(prop.default, list)
        assert len(prop.default) == 0

    def test_empty_dict_default(self):
        """Test property with empty dict default."""
        prop = ModelSchemaProperty(
            type="object",
            default={},
        )
        assert isinstance(prop.default, dict)
        assert len(prop.default) == 0


@pytest.mark.unit
class TestModelSchemaPropertySerialization:
    """Test ModelSchemaProperty serialization."""

    def test_model_dump(self):
        """Test model_dump returns dict."""
        prop = ModelSchemaProperty(
            type="string",
            title="Test Property",
            description="A test property",
        )
        dumped = prop.model_dump()

        assert isinstance(dumped, dict)
        assert dumped["type"] == "string"
        assert dumped["title"] == "Test Property"
        assert dumped["description"] == "A test property"

    def test_model_dump_json(self):
        """Test model_dump_json returns JSON string."""
        prop = ModelSchemaProperty(type="string", title="Test")
        json_str = prop.model_dump_json()

        assert isinstance(json_str, str)
        assert "Test" in json_str

    def test_round_trip_serialization(self):
        """Test serialization and deserialization."""
        original = ModelSchemaProperty(
            type="integer",
            title="Age",
            description="User age",
            default=18,
        )

        # Serialize
        dumped = original.model_dump()

        # Deserialize
        restored = ModelSchemaProperty(**dumped)

        assert restored.type == original.type
        assert restored.title == original.title
        assert restored.description == original.description
        assert restored.default == original.default

    def test_exclude_unset_fields(self):
        """Test model_dump with exclude_unset."""
        prop = ModelSchemaProperty(type="string", title="Test")
        dumped = prop.model_dump(exclude_unset=True)

        assert "type" in dumped
        assert "title" in dumped
        assert "description" not in dumped
        assert "default" not in dumped

    def test_exclude_none_fields(self):
        """Test model_dump with exclude_none."""
        prop = ModelSchemaProperty(
            type="string",
            title="Test",
            description=None,
        )
        dumped = prop.model_dump(exclude_none=True)

        assert "type" in dumped
        assert "title" in dumped
        assert "description" not in dumped


@pytest.mark.unit
class TestModelSchemaPropertyModelConfig:
    """Test ModelSchemaProperty model configuration."""

    def test_arbitrary_types_allowed(self):
        """Test arbitrary_types_allowed config."""
        # The model should allow arbitrary types
        prop = ModelSchemaProperty(type="custom")
        assert prop.type == "custom"

    def test_extra_fields_allowed(self):
        """Test extra='allow' configuration."""
        # Extra fields should be allowed
        prop = ModelSchemaProperty(
            type="string",
            custom_field="custom value",
        )
        assert prop.type == "string"
        # Extra field should be accessible
        assert hasattr(prop, "custom_field")


@pytest.mark.unit
class TestModelSchemaPropertyEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_all_fields_none(self):
        """Test property with all fields as None."""
        prop = ModelSchemaProperty(
            type=None,
            title=None,
            description=None,
            default=None,
            enum=None,
            format=None,
            items=None,
            properties=None,
            required=None,
        )
        assert prop.type is None
        assert prop.title is None
        # All fields should be None

    def test_unicode_in_fields(self):
        """Test property with unicode characters."""
        prop = ModelSchemaProperty(
            type="string",
            title="名前",
            description="用户名称 🎉",
        )
        assert prop.title == "名前"
        assert "🎉" in prop.description

    def test_long_strings(self):
        """Test property with very long strings."""
        long_title = "A" * 10000
        long_description = "B" * 10000

        prop = ModelSchemaProperty(
            title=long_title,
            description=long_description,
        )

        assert len(prop.title) == 10000
        assert len(prop.description) == 10000

    def test_special_characters_in_title(self):
        """Test property with special characters in title."""
        prop = ModelSchemaProperty(
            title='Test "quotes" and \\backslash\\',
        )
        assert '"quotes"' in prop.title
        assert "\\backslash\\" in prop.title

    def test_type_field_various_json_types(self):
        """Test type field with all JSON schema types."""
        types = ["string", "integer", "number", "boolean", "object", "array", "null"]
        for schema_type in types:
            prop = ModelSchemaProperty(type=schema_type)
            assert prop.type == schema_type

    def test_negative_integer_default(self):
        """Test property with negative integer default."""
        prop = ModelSchemaProperty(
            type="integer",
            default=-100,
        )
        assert prop.default == -100

    def test_negative_float_default(self):
        """Test property with negative float default."""
        prop = ModelSchemaProperty(
            type="number",
            default=-3.14,
        )
        assert prop.default == -3.14

    def test_very_large_number_default(self):
        """Test property with very large number default."""
        prop = ModelSchemaProperty(
            type="integer",
            default=999999999999999999,
        )
        assert prop.default == 999999999999999999

    def test_complex_nested_default(self):
        """Test property with complex nested default value."""
        prop = ModelSchemaProperty(
            type="object",
            default={
                "nested": {
                    "deeper": {
                        "value": [1, 2, 3],
                    }
                }
            },
        )
        assert isinstance(prop.default, dict)
        assert prop.default["nested"]["deeper"]["value"] == [1, 2, 3]


@pytest.mark.unit
class TestModelSchemaPropertyComplexScenarios:
    """Test complex real-world property scenarios."""

    def test_email_property_complete(self):
        """Test complete email property definition."""
        prop = ModelSchemaProperty(
            type="string",
            title="Email Address",
            description="User's email address",
            format="email",
        )

        assert prop.type == "string"
        assert prop.format == "email"
        assert "email" in prop.description.lower()

    def test_enum_with_descriptions(self):
        """Test enum property with title and description."""
        prop = ModelSchemaProperty(
            type="string",
            title="Status",
            description="Current user status",
            enum=["active", "inactive", "suspended"],
            default="active",
        )

        assert prop.enum is not None
        assert len(prop.enum) == 3
        assert prop.default == "active"
        assert prop.default in prop.enum

    def test_password_property(self):
        """Test password property with format."""
        prop = ModelSchemaProperty(
            type="string",
            title="Password",
            description="User password",
            format="password",
        )

        assert prop.format == "password"
        assert prop.type == "string"

    def test_timestamp_property(self):
        """Test timestamp property."""
        prop = ModelSchemaProperty(
            type="string",
            title="Created At",
            format="date-time",
        )

        assert prop.format == "date-time"
        assert prop.type == "string"

    def test_url_property(self):
        """Test URL property."""
        prop = ModelSchemaProperty(
            type="string",
            title="Website",
            format="uri",
        )

        assert prop.format == "uri"

    def test_tags_array_property(self):
        """Test array of tags."""
        prop = ModelSchemaProperty(
            type="array",
            title="Tags",
            description="List of tags",
            items=ModelSchemaProperty(type="string"),
            default=[],
        )

        assert prop.type == "array"
        assert prop.items is not None
        assert prop.items.type == "string"
        assert isinstance(prop.default, list)

    def test_metadata_object_property(self):
        """Test metadata object property."""
        from omnibase_core.models.validation.model_schema_properties_model import (
            ModelSchemaPropertiesModel,
        )

        metadata_props = ModelSchemaPropertiesModel(
            root={
                "created_by": ModelSchemaProperty(type="string"),
                "created_at": ModelSchemaProperty(type="string", format="date-time"),
                "updated_at": ModelSchemaProperty(type="string", format="date-time"),
            }
        )

        prop = ModelSchemaProperty(
            type="object",
            title="Metadata",
            properties=metadata_props,
        )

        assert prop.type == "object"
        assert prop.properties is not None
        assert len(prop.properties.root) == 3

    def test_pagination_object(self):
        """Test complex pagination object."""
        from omnibase_core.models.validation.model_schema_properties_model import (
            ModelSchemaPropertiesModel,
        )

        pagination_props = ModelSchemaPropertiesModel(
            root={
                "page": ModelSchemaProperty(type="integer", default=1),
                "per_page": ModelSchemaProperty(type="integer", default=10),
                "total": ModelSchemaProperty(type="integer"),
                "total_pages": ModelSchemaProperty(type="integer"),
            }
        )

        prop = ModelSchemaProperty(
            type="object",
            title="Pagination",
            properties=pagination_props,
        )

        assert prop.properties is not None
        assert "page" in prop.properties.root
        assert prop.properties.root["page"].default == 1

    def test_recursive_property_structure(self):
        """Test property that could reference itself (like a tree node)."""
        # Note: This tests the structure capability, not actual recursion
        from omnibase_core.models.validation.model_schema_properties_model import (
            ModelSchemaPropertiesModel,
        )

        node_props = ModelSchemaPropertiesModel(
            root={
                "value": ModelSchemaProperty(type="string"),
                "children": ModelSchemaProperty(
                    type="array",
                    items=ModelSchemaProperty(type="object"),
                ),
            }
        )

        prop = ModelSchemaProperty(
            type="object",
            title="Tree Node",
            properties=node_props,
        )

        assert prop.type == "object"
        assert "children" in prop.properties.root
        children_prop = prop.properties.root["children"]
        assert children_prop.type == "array"
        assert children_prop.items is not None
