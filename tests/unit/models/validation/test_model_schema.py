"""
Test suite for ModelSchema - schema validation models.

This test suite covers ModelSchema, ModelSchemaPropertiesModel, and ModelRequiredFieldsModel
to maximize coverage of the schema validation system.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.models.validation.model_required_fields_model import (
    ModelRequiredFieldsModel,
    RequiredFieldsModel,
)
from omnibase_core.models.validation.model_schema_class import (
    ModelSchema,
    SchemaModel,
)
from omnibase_core.models.validation.model_schema_properties_model import (
    ModelSchemaPropertiesModel,
    SchemaPropertiesModel,
)
from omnibase_core.models.validation.model_schema_property import ModelSchemaProperty

# Rebuild models to resolve forward references
ModelSchemaProperty.model_rebuild()
ModelSchemaPropertiesModel.model_rebuild()
ModelSchema.model_rebuild()


class TestModelSchemaInstantiation:
    """Test basic ModelSchema instantiation."""

    def test_default_initialization(self):
        """Test ModelSchema initializes with all None values."""
        schema = ModelSchema()
        assert schema.schema_uri is None
        assert schema.title is None
        assert schema.type is None
        assert schema.properties is None
        assert schema.required is None

    def test_full_initialization(self):
        """Test ModelSchema with all fields provided."""
        properties = ModelSchemaPropertiesModel(
            root={
                "name": ModelSchemaProperty(type="string", title="Name"),
                "age": ModelSchemaProperty(type="integer", title="Age"),
            }
        )
        required = ModelRequiredFieldsModel(root=["name", "age"])

        schema = ModelSchema(
            schema_uri="https://example.com/schema.json",
            title="Person Schema",
            type="object",
            properties=properties,
            required=required,
        )

        assert schema.schema_uri == "https://example.com/schema.json"
        assert schema.title == "Person Schema"
        assert schema.type == "object"
        assert schema.properties is not None
        assert schema.required is not None

    def test_partial_initialization(self):
        """Test ModelSchema with partial fields."""
        schema = ModelSchema(
            title="Minimal Schema",
            type="object",
        )

        assert schema.title == "Minimal Schema"
        assert schema.type == "object"
        assert schema.schema_uri is None
        assert schema.properties is None
        assert schema.required is None

    def test_schema_uri_optional(self):
        """Test schema_uri can be None."""
        schema = ModelSchema(schema_uri=None)
        assert schema.schema_uri is None

    def test_properties_with_empty_dict(self):
        """Test ModelSchema with empty properties."""
        properties = ModelSchemaPropertiesModel(root={})
        schema = ModelSchema(properties=properties)
        assert schema.properties is not None
        assert len(schema.properties.root) == 0

    def test_required_with_empty_list(self):
        """Test ModelSchema with empty required list."""
        required = ModelRequiredFieldsModel(root=[])
        schema = ModelSchema(required=required)
        assert schema.required is not None
        assert len(schema.required.root) == 0


class TestModelSchemaCompatibilityAliases:
    """Test compatibility aliases for ModelSchema."""

    def test_schema_model_alias(self):
        """Test SchemaModel is an alias for ModelSchema."""
        assert SchemaModel is ModelSchema

    def test_schema_model_instantiation(self):
        """Test SchemaModel can be instantiated."""
        schema = SchemaModel(title="Test Schema")
        assert isinstance(schema, ModelSchema)
        assert schema.title == "Test Schema"


class TestModelSchemaSerialization:
    """Test ModelSchema serialization."""

    def test_model_dump(self):
        """Test model_dump returns dict."""
        schema = ModelSchema(
            title="Test Schema",
            type="object",
        )
        dumped = schema.model_dump()

        assert isinstance(dumped, dict)
        assert dumped["title"] == "Test Schema"
        assert dumped["type"] == "object"

    def test_model_dump_json(self):
        """Test model_dump_json returns JSON string."""
        schema = ModelSchema(title="Test Schema")
        json_str = schema.model_dump_json()

        assert isinstance(json_str, str)
        assert "Test Schema" in json_str

    def test_round_trip_serialization(self):
        """Test serialization and deserialization."""
        original = ModelSchema(
            schema_uri="https://example.com/schema.json",
            title="Test Schema",
            type="object",
        )

        # Serialize
        dumped = original.model_dump()

        # Deserialize
        restored = ModelSchema(**dumped)

        assert restored.schema_uri == original.schema_uri
        assert restored.title == original.title
        assert restored.type == original.type

    def test_exclude_unset_fields(self):
        """Test model_dump with exclude_unset."""
        schema = ModelSchema(title="Test")
        dumped = schema.model_dump(exclude_unset=True)

        assert "title" in dumped
        assert "schema_uri" not in dumped
        assert "type" not in dumped


class TestModelSchemaPropertiesModel:
    """Test ModelSchemaPropertiesModel."""

    def test_default_initialization(self):
        """Test ModelSchemaPropertiesModel with dict of properties."""
        properties = ModelSchemaPropertiesModel(
            root={
                "name": ModelSchemaProperty(type="string"),
                "age": ModelSchemaProperty(type="integer"),
            }
        )

        assert isinstance(properties.root, dict)
        assert len(properties.root) == 2
        assert "name" in properties.root
        assert "age" in properties.root

    def test_empty_properties(self):
        """Test ModelSchemaPropertiesModel with empty dict."""
        properties = ModelSchemaPropertiesModel(root={})
        assert isinstance(properties.root, dict)
        assert len(properties.root) == 0

    def test_single_property(self):
        """Test ModelSchemaPropertiesModel with single property."""
        properties = ModelSchemaPropertiesModel(
            root={"name": ModelSchemaProperty(type="string", title="Name")}
        )

        assert len(properties.root) == 1
        assert properties.root["name"].type == "string"
        assert properties.root["name"].title == "Name"

    def test_nested_properties(self):
        """Test ModelSchemaPropertiesModel with nested object properties."""
        nested_props = ModelSchemaPropertiesModel(
            root={
                "street": ModelSchemaProperty(type="string"),
                "city": ModelSchemaProperty(type="string"),
            }
        )

        properties = ModelSchemaPropertiesModel(
            root={
                "address": ModelSchemaProperty(
                    type="object",
                    properties=nested_props,
                )
            }
        )

        assert "address" in properties.root
        assert properties.root["address"].type == "object"
        assert properties.root["address"].properties is not None

    def test_compatibility_alias(self):
        """Test SchemaPropertiesModel is an alias."""
        assert SchemaPropertiesModel is ModelSchemaPropertiesModel

    def test_model_dump(self):
        """Test ModelSchemaPropertiesModel serialization."""
        properties = ModelSchemaPropertiesModel(
            root={"name": ModelSchemaProperty(type="string")}
        )
        dumped = properties.model_dump()

        assert isinstance(dumped, dict)
        assert "name" in dumped
        assert dumped["name"]["type"] == "string"

    def test_access_root_directly(self):
        """Test direct access to root attribute."""
        properties = ModelSchemaPropertiesModel(
            root={"field1": ModelSchemaProperty(type="string")}
        )

        # Access root directly
        assert isinstance(properties.root, dict)
        assert properties.root["field1"].type == "string"

    def test_complex_schema_with_multiple_types(self):
        """Test properties with various types."""
        properties = ModelSchemaPropertiesModel(
            root={
                "name": ModelSchemaProperty(type="string"),
                "age": ModelSchemaProperty(type="integer"),
                "active": ModelSchemaProperty(type="boolean"),
                "score": ModelSchemaProperty(type="number"),
                "tags": ModelSchemaProperty(type="array", items=ModelSchemaProperty(type="string")),
            }
        )

        assert len(properties.root) == 5
        assert properties.root["name"].type == "string"
        assert properties.root["age"].type == "integer"
        assert properties.root["active"].type == "boolean"
        assert properties.root["score"].type == "number"
        assert properties.root["tags"].type == "array"


class TestModelRequiredFieldsModel:
    """Test ModelRequiredFieldsModel."""

    def test_default_initialization(self):
        """Test ModelRequiredFieldsModel with list of strings."""
        required = ModelRequiredFieldsModel(root=["name", "email", "age"])

        assert isinstance(required.root, list)
        assert len(required.root) == 3
        assert "name" in required.root
        assert "email" in required.root
        assert "age" in required.root

    def test_empty_required(self):
        """Test ModelRequiredFieldsModel with empty list."""
        required = ModelRequiredFieldsModel(root=[])
        assert isinstance(required.root, list)
        assert len(required.root) == 0

    def test_single_required_field(self):
        """Test ModelRequiredFieldsModel with single field."""
        required = ModelRequiredFieldsModel(root=["id"])
        assert len(required.root) == 1
        assert required.root[0] == "id"

    def test_compatibility_alias(self):
        """Test RequiredFieldsModel is an alias."""
        assert RequiredFieldsModel is ModelRequiredFieldsModel

    def test_model_dump(self):
        """Test ModelRequiredFieldsModel serialization."""
        required = ModelRequiredFieldsModel(root=["field1", "field2"])
        dumped = required.model_dump()

        assert isinstance(dumped, list)
        assert len(dumped) == 2
        assert "field1" in dumped
        assert "field2" in dumped

    def test_access_root_directly(self):
        """Test direct access to root attribute."""
        required = ModelRequiredFieldsModel(root=["name", "email"])

        # Access root directly
        assert isinstance(required.root, list)
        assert required.root[0] == "name"
        assert required.root[1] == "email"

    def test_duplicate_fields(self):
        """Test ModelRequiredFieldsModel with duplicate field names."""
        required = ModelRequiredFieldsModel(root=["name", "name", "email"])
        # Duplicates are allowed in the list
        assert len(required.root) == 3


class TestModelSchemaIntegration:
    """Test ModelSchema integration with properties and required fields."""

    def test_schema_with_properties_and_required(self):
        """Test complete schema with properties and required fields."""
        properties = ModelSchemaPropertiesModel(
            root={
                "name": ModelSchemaProperty(type="string", title="Name"),
                "email": ModelSchemaProperty(type="string", format="email"),
                "age": ModelSchemaProperty(type="integer", default=0),
            }
        )
        required = ModelRequiredFieldsModel(root=["name", "email"])

        schema = ModelSchema(
            schema_uri="https://example.com/person.json",
            title="Person",
            type="object",
            properties=properties,
            required=required,
        )

        assert schema.title == "Person"
        assert len(schema.properties.root) == 3
        assert len(schema.required.root) == 2
        assert "name" in schema.properties.root
        assert "name" in schema.required.root

    def test_schema_without_required_fields(self):
        """Test schema with properties but no required fields."""
        properties = ModelSchemaPropertiesModel(
            root={
                "optional1": ModelSchemaProperty(type="string"),
                "optional2": ModelSchemaProperty(type="integer"),
            }
        )

        schema = ModelSchema(
            title="Optional Schema",
            type="object",
            properties=properties,
        )

        assert schema.properties is not None
        assert schema.required is None

    def test_schema_with_required_but_no_properties(self):
        """Test schema with required fields but no properties defined."""
        required = ModelRequiredFieldsModel(root=["field1"])

        schema = ModelSchema(
            title="Required Only Schema",
            required=required,
        )

        assert schema.required is not None
        assert schema.properties is None

    def test_full_schema_serialization(self):
        """Test complete schema serialization."""
        properties = ModelSchemaPropertiesModel(
            root={
                "id": ModelSchemaProperty(type="integer", title="ID"),
                "name": ModelSchemaProperty(type="string", title="Name"),
            }
        )
        required = ModelRequiredFieldsModel(root=["id"])

        schema = ModelSchema(
            schema_uri="https://example.com/schema.json",
            title="Full Schema",
            type="object",
            properties=properties,
            required=required,
        )

        dumped = schema.model_dump()

        assert "schema_uri" in dumped
        assert "title" in dumped
        assert "type" in dumped
        assert "properties" in dumped
        assert "required" in dumped

    def test_nested_object_schema(self):
        """Test schema with nested object properties."""
        address_props = ModelSchemaPropertiesModel(
            root={
                "street": ModelSchemaProperty(type="string"),
                "city": ModelSchemaProperty(type="string"),
                "zip": ModelSchemaProperty(type="string"),
            }
        )

        properties = ModelSchemaPropertiesModel(
            root={
                "name": ModelSchemaProperty(type="string"),
                "address": ModelSchemaProperty(type="object", properties=address_props),
            }
        )

        required = ModelRequiredFieldsModel(root=["name"])

        schema = ModelSchema(
            title="Person with Address",
            type="object",
            properties=properties,
            required=required,
        )

        assert schema.properties is not None
        assert "address" in schema.properties.root
        assert schema.properties.root["address"].type == "object"
        assert schema.properties.root["address"].properties is not None


class TestModelSchemaEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_schema(self):
        """Test completely empty schema."""
        schema = ModelSchema()
        assert schema.schema_uri is None
        assert schema.title is None
        assert schema.type is None
        assert schema.properties is None
        assert schema.required is None

    def test_schema_with_only_uri(self):
        """Test schema with only URI set."""
        schema = ModelSchema(schema_uri="https://example.com/schema.json")
        assert schema.schema_uri == "https://example.com/schema.json"
        assert schema.title is None

    def test_schema_with_only_title(self):
        """Test schema with only title set."""
        schema = ModelSchema(title="Test Schema")
        assert schema.title == "Test Schema"
        assert schema.schema_uri is None

    def test_long_schema_uri(self):
        """Test schema with very long URI."""
        long_uri = "https://example.com/" + "a" * 1000 + "/schema.json"
        schema = ModelSchema(schema_uri=long_uri)
        assert schema.schema_uri == long_uri

    def test_unicode_in_title(self):
        """Test schema with unicode characters in title."""
        schema = ModelSchema(title="Schema 测试 🎉")
        assert schema.title == "Schema 测试 🎉"

    def test_special_characters_in_property_names(self):
        """Test properties with special characters in names."""
        properties = ModelSchemaPropertiesModel(
            root={
                "field-with-dash": ModelSchemaProperty(type="string"),
                "field_with_underscore": ModelSchemaProperty(type="string"),
                "field.with.dot": ModelSchemaProperty(type="string"),
            }
        )

        schema = ModelSchema(properties=properties)
        assert "field-with-dash" in schema.properties.root
        assert "field_with_underscore" in schema.properties.root
        assert "field.with.dot" in schema.properties.root

    def test_numeric_string_in_required(self):
        """Test required fields with numeric strings."""
        required = ModelRequiredFieldsModel(root=["field1", "2", "field_3"])
        assert len(required.root) == 3
        assert "2" in required.root

    def test_empty_string_in_required(self):
        """Test required fields with empty string."""
        required = ModelRequiredFieldsModel(root=["", "field1"])
        assert len(required.root) == 2
        assert "" in required.root

    def test_model_validation_with_extra_fields(self):
        """Test that extra fields are handled correctly."""
        # ModelSchema doesn't explicitly forbid extra fields
        # This tests Pydantic's default behavior
        data = {
            "title": "Test",
            "extra_field": "should be ignored or allowed",
        }
        schema = ModelSchema(**data)
        assert schema.title == "Test"


class TestModelSchemaTypeValidation:
    """Test type validation and constraints."""

    def test_schema_uri_must_be_string_or_none(self):
        """Test schema_uri accepts string or None."""
        schema1 = ModelSchema(schema_uri="https://example.com")
        assert isinstance(schema1.schema_uri, str)

        schema2 = ModelSchema(schema_uri=None)
        assert schema2.schema_uri is None

    def test_type_field_various_values(self):
        """Test type field with various JSON schema types."""
        for schema_type in ["object", "array", "string", "integer", "number", "boolean", "null"]:
            schema = ModelSchema(type=schema_type)
            assert schema.type == schema_type

    def test_properties_must_be_properties_model_or_none(self):
        """Test properties field type constraints."""
        # Valid: None
        schema1 = ModelSchema(properties=None)
        assert schema1.properties is None

        # Valid: ModelSchemaPropertiesModel
        props = ModelSchemaPropertiesModel(root={})
        schema2 = ModelSchema(properties=props)
        assert isinstance(schema2.properties, ModelSchemaPropertiesModel)

    def test_required_must_be_required_model_or_none(self):
        """Test required field type constraints."""
        # Valid: None
        schema1 = ModelSchema(required=None)
        assert schema1.required is None

        # Valid: ModelRequiredFieldsModel
        req = ModelRequiredFieldsModel(root=[])
        schema2 = ModelSchema(required=req)
        assert isinstance(schema2.required, ModelRequiredFieldsModel)


class TestModelSchemaComplexScenarios:
    """Test complex real-world schema scenarios."""

    def test_json_schema_like_structure(self):
        """Test creating a structure similar to JSON Schema."""
        properties = ModelSchemaPropertiesModel(
            root={
                "id": ModelSchemaProperty(
                    type="integer",
                    title="User ID",
                    description="Unique identifier",
                ),
                "username": ModelSchemaProperty(
                    type="string",
                    title="Username",
                    description="User login name",
                ),
                "email": ModelSchemaProperty(
                    type="string",
                    format="email",
                    title="Email",
                ),
                "age": ModelSchemaProperty(
                    type="integer",
                    title="Age",
                    default=18,
                ),
                "roles": ModelSchemaProperty(
                    type="array",
                    items=ModelSchemaProperty(type="string"),
                    title="User Roles",
                ),
            }
        )

        required = ModelRequiredFieldsModel(root=["id", "username", "email"])

        schema = ModelSchema(
            schema_uri="https://api.example.com/schemas/user.json",
            title="User Schema",
            type="object",
            properties=properties,
            required=required,
        )

        # Verify structure
        assert schema.title == "User Schema"
        assert len(schema.properties.root) == 5
        assert len(schema.required.root) == 3
        assert "id" in schema.required.root
        assert schema.properties.root["age"].default == 18

    def test_deeply_nested_schema(self):
        """Test schema with multiple levels of nesting."""
        city_props = ModelSchemaPropertiesModel(
            root={
                "name": ModelSchemaProperty(type="string"),
                "zipcode": ModelSchemaProperty(type="string"),
            }
        )

        address_props = ModelSchemaPropertiesModel(
            root={
                "street": ModelSchemaProperty(type="string"),
                "city": ModelSchemaProperty(type="object", properties=city_props),
            }
        )

        person_props = ModelSchemaPropertiesModel(
            root={
                "name": ModelSchemaProperty(type="string"),
                "address": ModelSchemaProperty(type="object", properties=address_props),
            }
        )

        schema = ModelSchema(
            title="Nested Person Schema",
            type="object",
            properties=person_props,
        )

        # Verify nesting
        assert schema.properties is not None
        assert "address" in schema.properties.root
        address_prop = schema.properties.root["address"]
        assert address_prop.properties is not None
        assert "city" in address_prop.properties.root

    def test_array_of_objects_schema(self):
        """Test schema for array of objects."""
        item_props = ModelSchemaPropertiesModel(
            root={
                "id": ModelSchemaProperty(type="integer"),
                "name": ModelSchemaProperty(type="string"),
            }
        )

        properties = ModelSchemaPropertiesModel(
            root={
                "items": ModelSchemaProperty(
                    type="array",
                    items=ModelSchemaProperty(type="object", properties=item_props),
                )
            }
        )

        schema = ModelSchema(
            title="Items List Schema",
            type="object",
            properties=properties,
        )

        assert schema.properties is not None
        items_prop = schema.properties.root["items"]
        assert items_prop.type == "array"
        assert items_prop.items is not None
        assert items_prop.items.type == "object"
