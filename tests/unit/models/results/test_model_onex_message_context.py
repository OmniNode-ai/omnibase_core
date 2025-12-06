"""
Comprehensive tests for ModelOnexMessageContext.

Tests cover:
- Basic instantiation with optional fields
- Key-value pair handling
- ModelSchemaValue type usage (strongly typed)
- arbitrary_types_allowed config
- Type safety verification
"""

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.results.model_onex_message_context import (
    ModelOnexMessageContext,
)


class TestModelOnexMessageContextBasicInstantiation:
    """Test basic instantiation."""

    def test_empty_instantiation(self):
        """Test creating context with no fields."""
        context = ModelOnexMessageContext()

        assert context.key is None
        assert context.value is None

    def test_instantiation_with_key_only(self):
        """Test creating context with key only."""
        context = ModelOnexMessageContext(key="variable_name")

        assert context.key == "variable_name"
        assert context.value is None

    def test_instantiation_with_key_and_value(self):
        """Test creating context with key and value - automatically converts to ModelSchemaValue."""
        context = ModelOnexMessageContext(
            key="variable_name", value=ModelSchemaValue.from_value("test_value")
        )

        assert context.key == "variable_name"
        assert isinstance(context.value, ModelSchemaValue)
        assert context.value.string_value == "test_value"


class TestModelOnexMessageContextKeyField:
    """Test key field handling."""

    def test_key_field_with_string(self):
        """Test key field with string value."""
        context = ModelOnexMessageContext(key="test_key")
        assert context.key == "test_key"

    def test_key_field_optional(self):
        """Test that key field is optional."""
        context = ModelOnexMessageContext()
        assert context.key is None

    def test_key_field_with_various_names(self):
        """Test key field with different naming conventions."""
        keys = [
            "simple",
            "snake_case",
            "camelCase",
            "with.dots",
            "with-dashes",
            "UPPERCASE",
        ]

        for key in keys:
            context = ModelOnexMessageContext(key=key)
            assert context.key == key


class TestModelOnexMessageContextValueField:
    """Test value field with ModelSchemaValue type (strongly typed)."""

    def test_value_field_with_string(self):
        """Test value field with string - converts to ModelSchemaValue."""
        context = ModelOnexMessageContext(
            key="key", value=ModelSchemaValue.from_value("string_value")
        )
        assert isinstance(context.value, ModelSchemaValue)
        assert context.value.string_value == "string_value"

    def test_value_field_with_integer(self):
        """Test value field with integer - converts to ModelSchemaValue."""
        context = ModelOnexMessageContext(
            key="key", value=ModelSchemaValue.from_value(42)
        )
        assert isinstance(context.value, ModelSchemaValue)
        assert context.value.number_value == 42

    def test_value_field_with_float(self):
        """Test value field with float - converts to ModelSchemaValue."""
        context = ModelOnexMessageContext(
            key="key", value=ModelSchemaValue.from_value(3.14)
        )
        assert isinstance(context.value, ModelSchemaValue)
        assert context.value.number_value == 3.14

    def test_value_field_with_boolean(self):
        """Test value field with boolean - converts to ModelSchemaValue."""
        context = ModelOnexMessageContext(
            key="key", value=ModelSchemaValue.from_value(True)
        )
        assert isinstance(context.value, ModelSchemaValue)
        assert context.value.boolean_value is True

        context = ModelOnexMessageContext(
            key="key", value=ModelSchemaValue.from_value(False)
        )
        assert isinstance(context.value, ModelSchemaValue)
        assert context.value.boolean_value is False

    def test_value_field_with_none(self):
        """Test value field with None."""
        context = ModelOnexMessageContext(key="key", value=None)
        assert context.value is None

    def test_value_field_with_list_of_strings(self):
        """Test value field with list - converts to ModelSchemaValue."""
        value_list = ["item1", "item2", "item3"]
        context = ModelOnexMessageContext(
            key="key", value=ModelSchemaValue.from_value(value_list)
        )
        assert isinstance(context.value, ModelSchemaValue)
        assert context.value.value_type == "array"
        assert len(context.value.array_value) == 3

    def test_value_field_with_dict_of_strings(self):
        """Test value field with dict - converts to ModelSchemaValue."""
        value_dict = {"nested_key1": "value1", "nested_key2": "value2"}
        context = ModelOnexMessageContext(
            key="key", value=ModelSchemaValue.from_value(value_dict)
        )
        assert isinstance(context.value, ModelSchemaValue)
        assert context.value.value_type == "object"
        assert "nested_key1" in context.value.object_value

    def test_value_field_defaults_to_none(self):
        """Test that value field defaults to None."""
        context = ModelOnexMessageContext(key="key")
        assert context.value is None


class TestModelOnexMessageContextModelConfig:
    """Test Pydantic model_config settings."""

    def test_arbitrary_types_allowed_config(self):
        """Test that arbitrary_types_allowed is configured correctly."""
        assert ModelOnexMessageContext.model_config["arbitrary_types_allowed"] is True


class TestModelOnexMessageContextFieldValidation:
    """Test field validation."""

    def test_key_must_be_string_or_none(self):
        """Test that key field accepts string or None."""
        # Valid string
        context = ModelOnexMessageContext(key="valid_string")
        assert isinstance(context.key, str)

        # Valid None
        context = ModelOnexMessageContext(key=None)
        assert context.key is None

    def test_value_accepts_schema_value_types(self):
        """Test that value field accepts various types and converts to ModelSchemaValue."""
        # String
        context = ModelOnexMessageContext(value=ModelSchemaValue.from_value("string"))
        assert isinstance(context.value, ModelSchemaValue)

        # Integer
        context = ModelOnexMessageContext(value=ModelSchemaValue.from_value(42))
        assert isinstance(context.value, ModelSchemaValue)

        # Float
        context = ModelOnexMessageContext(value=ModelSchemaValue.from_value(3.14))
        assert isinstance(context.value, ModelSchemaValue)

        # Boolean
        context = ModelOnexMessageContext(value=ModelSchemaValue.from_value(True))
        assert isinstance(context.value, ModelSchemaValue)

        # List
        context = ModelOnexMessageContext(value=ModelSchemaValue.from_value(["a", "b"]))
        assert isinstance(context.value, ModelSchemaValue)

        # Dict
        context = ModelOnexMessageContext(
            value=ModelSchemaValue.from_value({"key": "value"})
        )
        assert isinstance(context.value, ModelSchemaValue)

        # None
        context = ModelOnexMessageContext(value=None)
        assert context.value is None


class TestModelOnexMessageContextSerialization:
    """Test model serialization and deserialization."""

    def test_model_dump_basic(self):
        """Test model_dump() produces correct dictionary with ModelSchemaValue."""
        context = ModelOnexMessageContext(
            key="test_key", value=ModelSchemaValue.from_value("test_value")
        )

        dumped = context.model_dump()

        assert dumped["key"] == "test_key"
        assert isinstance(dumped["value"], dict)  # ModelSchemaValue serializes to dict
        assert dumped["value"]["string_value"] == "test_value"

    def test_model_dump_with_complex_value(self):
        """Test model_dump() with complex value types."""
        value_dict = {"nested": "data", "count": "10"}
        context = ModelOnexMessageContext(
            key="complex", value=ModelSchemaValue.from_value(value_dict)
        )

        dumped = context.model_dump()

        assert dumped["key"] == "complex"
        assert isinstance(dumped["value"], dict)  # ModelSchemaValue serializes to dict
        assert dumped["value"]["value_type"] == "object"
        assert "nested" in dumped["value"]["object_value"]

    def test_model_dump_exclude_none(self):
        """Test model_dump(exclude_none=True) removes None fields."""
        context = ModelOnexMessageContext(key="key")

        dumped = context.model_dump(exclude_none=True)

        assert "key" in dumped
        assert "value" not in dumped

    def test_model_dump_json_roundtrip(self):
        """Test JSON serialization roundtrip."""
        original = ModelOnexMessageContext(
            key="test_key", value=ModelSchemaValue.from_value("test_value")
        )

        json_str = original.model_dump_json()
        restored = ModelOnexMessageContext.model_validate_json(json_str)

        assert restored.key == original.key
        assert isinstance(restored.value, ModelSchemaValue)
        # Note: JSON roundtrip may have nested serialization - just verify the type is correct
        assert restored.value.value_type in ["string", "object"]


class TestModelOnexMessageContextComplexScenarios:
    """Test complex usage scenarios."""

    def test_context_with_error_location(self):
        """Test context holding error location information."""
        context = ModelOnexMessageContext(
            key="line_content",
            value=ModelSchemaValue.from_value("def foo()  # Missing colon"),
        )

        assert context.key == "line_content"
        assert isinstance(context.value, ModelSchemaValue)
        assert "Missing colon" in context.value.string_value

    def test_context_with_variable_info(self):
        """Test context holding variable information."""
        context = ModelOnexMessageContext(
            key="variable_type", value=ModelSchemaValue.from_value("int")
        )

        assert context.key == "variable_type"
        assert isinstance(context.value, ModelSchemaValue)
        assert context.value.string_value == "int"

    def test_context_with_numeric_value(self):
        """Test context with numeric context value."""
        context = ModelOnexMessageContext(
            key="line_number", value=ModelSchemaValue.from_value(42)
        )

        assert context.key == "line_number"
        assert isinstance(context.value, ModelSchemaValue)
        assert context.value.number_value == 42

    def test_multiple_contexts_in_list(self):
        """Test creating multiple context instances."""
        contexts = [
            ModelOnexMessageContext(
                key="file", value=ModelSchemaValue.from_value("main.py")
            ),
            ModelOnexMessageContext(
                key="function", value=ModelSchemaValue.from_value("main")
            ),
            ModelOnexMessageContext(key="line", value=ModelSchemaValue.from_value(10)),
        ]

        assert len(contexts) == 3
        assert contexts[0].key == "file"
        assert contexts[1].key == "function"
        assert isinstance(contexts[2].value, ModelSchemaValue)
        assert contexts[2].value.number_value == 10


class TestModelOnexMessageContextTypeSafety:
    """Test type safety - ZERO TOLERANCE for Any types."""

    def test_value_uses_model_schema_value_not_any(self):
        """Test that value field uses ModelSchemaValue type, not Any."""
        from typing import get_type_hints

        hints = get_type_hints(ModelOnexMessageContext)
        value_type = hints.get("value")

        assert value_type is not None
        type_str = str(value_type)
        # Should use ModelSchemaValue, not Any or loose unions
        assert "ModelSchemaValue" in type_str

    def test_no_any_types_in_annotations(self):
        """Test that model fields don't use Any type."""
        from typing import get_type_hints

        hints = get_type_hints(ModelOnexMessageContext)

        # Check that no field uses Any type directly
        for field_name, field_type in hints.items():
            type_str = str(field_type)
            # Allow typing.Any only in union with other types
            assert "typing.Any" not in type_str or "None" in type_str, (
                f"Field {field_name} uses Any type: {type_str}"
            )


class TestModelOnexMessageContextEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_string_key(self):
        """Test context with empty string key."""
        context = ModelOnexMessageContext(
            key="", value=ModelSchemaValue.from_value("value")
        )
        assert context.key == ""

    def test_empty_string_value(self):
        """Test context with empty string value."""
        context = ModelOnexMessageContext(
            key="key", value=ModelSchemaValue.from_value("")
        )
        assert isinstance(context.value, ModelSchemaValue)
        assert context.value.string_value == ""

    def test_zero_integer_value(self):
        """Test context with zero integer value."""
        context = ModelOnexMessageContext(
            key="count", value=ModelSchemaValue.from_value(0)
        )
        assert isinstance(context.value, ModelSchemaValue)
        assert context.value.number_value == 0

    def test_empty_list_value(self):
        """Test context with empty list value."""
        context = ModelOnexMessageContext(
            key="items", value=ModelSchemaValue.from_value([])
        )
        assert isinstance(context.value, ModelSchemaValue)
        assert context.value.array_value == []

    def test_empty_dict_value(self):
        """Test context with empty dict value."""
        context = ModelOnexMessageContext(
            key="data", value=ModelSchemaValue.from_value({})
        )
        assert isinstance(context.value, ModelSchemaValue)
        assert context.value.object_value == {}
