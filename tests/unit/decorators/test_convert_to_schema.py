"""
Unit tests for @convert_to_schema decorator.

Tests cover:
- Automatic list conversion to ModelSchemaValue
- Automatic dict conversion to ModelSchemaValue
- Empty collection handling
- Already-converted values (pass-through)
- Mixed types in collections
- Multiple field support
- Edge cases (None, nested structures)
- Pydantic model integration
- Specialized decorators (convert_list_to_schema, convert_dict_to_schema)
"""

import pytest
from pydantic import BaseModel, Field

from omnibase_core.decorators.convert_to_schema import (
    convert_dict_to_schema,
    convert_list_to_schema,
    convert_to_schema,
)
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


@pytest.mark.unit
class TestConvertToSchemaBasicListBehavior:
    """Test basic @convert_to_schema decorator behavior with lists."""

    def test_convert_list_of_strings(self):
        """Test conversion of string list to ModelSchemaValue list."""

        @convert_to_schema("values")
        class TestModel(BaseModel):
            values: list[ModelSchemaValue] = Field(default_factory=list)

        model = TestModel(values=["hello", "world"])

        assert len(model.values) == 2
        assert all(isinstance(v, ModelSchemaValue) for v in model.values)
        assert model.values[0].get_string() == "hello"
        assert model.values[1].get_string() == "world"

    def test_convert_list_of_numbers(self):
        """Test conversion of numeric list to ModelSchemaValue list."""

        @convert_to_schema("values")
        class TestModel(BaseModel):
            values: list[ModelSchemaValue] = Field(default_factory=list)

        model = TestModel(values=[1, 2.5, 3])

        assert len(model.values) == 3
        assert all(isinstance(v, ModelSchemaValue) for v in model.values)
        assert model.values[0].to_value() == 1
        assert model.values[1].to_value() == 2.5
        assert model.values[2].to_value() == 3

    def test_convert_list_of_booleans(self):
        """Test conversion of boolean list to ModelSchemaValue list."""

        @convert_to_schema("values")
        class TestModel(BaseModel):
            values: list[ModelSchemaValue] = Field(default_factory=list)

        model = TestModel(values=[True, False, True])

        assert len(model.values) == 3
        assert all(isinstance(v, ModelSchemaValue) for v in model.values)
        assert model.values[0].get_boolean() is True
        assert model.values[1].get_boolean() is False
        assert model.values[2].get_boolean() is True

    def test_convert_empty_list(self):
        """Test handling of empty list."""

        @convert_to_schema("values")
        class TestModel(BaseModel):
            values: list[ModelSchemaValue] = Field(default_factory=list)

        model = TestModel(values=[])

        assert model.values == []
        assert isinstance(model.values, list)

    def test_pass_through_already_converted_list(self):
        """Test that already-converted ModelSchemaValue instances pass through."""

        @convert_to_schema("values")
        class TestModel(BaseModel):
            values: list[ModelSchemaValue] = Field(default_factory=list)

        # Pre-create ModelSchemaValue instances
        schema_values = [
            ModelSchemaValue.create_string("already"),
            ModelSchemaValue.create_string("converted"),
        ]
        model = TestModel(values=schema_values)

        assert len(model.values) == 2
        assert model.values[0].get_string() == "already"
        assert model.values[1].get_string() == "converted"

    def test_convert_list_of_dicts(self):
        """Test conversion of dict list to ModelSchemaValue list."""

        @convert_to_schema("values")
        class TestModel(BaseModel):
            values: list[ModelSchemaValue] = Field(default_factory=list)

        model = TestModel(values=[{"a": 1}, {"b": 2}])

        assert len(model.values) == 2
        assert all(isinstance(v, ModelSchemaValue) for v in model.values)
        assert model.values[0].is_object()
        assert model.values[1].is_object()

    def test_convert_list_of_nested_lists(self):
        """Test conversion of nested list to ModelSchemaValue list."""

        @convert_to_schema("values")
        class TestModel(BaseModel):
            values: list[ModelSchemaValue] = Field(default_factory=list)

        model = TestModel(values=[[1, 2], [3, 4]])

        assert len(model.values) == 2
        assert all(isinstance(v, ModelSchemaValue) for v in model.values)
        assert model.values[0].is_array()
        assert model.values[1].is_array()


@pytest.mark.unit
class TestConvertToSchemaBasicDictBehavior:
    """Test basic @convert_to_schema decorator behavior with dicts."""

    def test_convert_dict_of_strings(self):
        """Test conversion of string dict to ModelSchemaValue dict."""

        @convert_to_schema("metadata")
        class TestModel(BaseModel):
            metadata: dict[str, ModelSchemaValue] = Field(default_factory=dict)

        model = TestModel(metadata={"key1": "value1", "key2": "value2"})

        assert len(model.metadata) == 2
        assert all(isinstance(v, ModelSchemaValue) for v in model.metadata.values())
        assert model.metadata["key1"].get_string() == "value1"
        assert model.metadata["key2"].get_string() == "value2"

    def test_convert_dict_of_numbers(self):
        """Test conversion of numeric dict to ModelSchemaValue dict."""

        @convert_to_schema("metadata")
        class TestModel(BaseModel):
            metadata: dict[str, ModelSchemaValue] = Field(default_factory=dict)

        model = TestModel(metadata={"a": 1, "b": 2.5, "c": 3})

        assert len(model.metadata) == 3
        assert all(isinstance(v, ModelSchemaValue) for v in model.metadata.values())
        assert model.metadata["a"].to_value() == 1
        assert model.metadata["b"].to_value() == 2.5
        assert model.metadata["c"].to_value() == 3

    def test_convert_empty_dict(self):
        """Test handling of empty dict."""

        @convert_to_schema("metadata")
        class TestModel(BaseModel):
            metadata: dict[str, ModelSchemaValue] = Field(default_factory=dict)

        model = TestModel(metadata={})

        assert model.metadata == {}
        assert isinstance(model.metadata, dict)

    def test_pass_through_already_converted_dict(self):
        """Test that already-converted ModelSchemaValue dict values pass through."""

        @convert_to_schema("metadata")
        class TestModel(BaseModel):
            metadata: dict[str, ModelSchemaValue] = Field(default_factory=dict)

        # Pre-create ModelSchemaValue instances
        schema_dict = {
            "key1": ModelSchemaValue.create_string("already"),
            "key2": ModelSchemaValue.create_number(42),
        }
        model = TestModel(metadata=schema_dict)

        assert len(model.metadata) == 2
        assert model.metadata["key1"].get_string() == "already"
        assert model.metadata["key2"].to_value() == 42


@pytest.mark.unit
class TestConvertToSchemaMultipleFields:
    """Test @convert_to_schema with multiple fields."""

    def test_convert_multiple_list_fields(self):
        """Test conversion of multiple list fields at once."""

        @convert_to_schema("items", "tags")
        class TestModel(BaseModel):
            items: list[ModelSchemaValue] = Field(default_factory=list)
            tags: list[ModelSchemaValue] = Field(default_factory=list)

        model = TestModel(items=["item1", "item2"], tags=["tag1", "tag2"])

        assert len(model.items) == 2
        assert len(model.tags) == 2
        assert model.items[0].get_string() == "item1"
        assert model.tags[0].get_string() == "tag1"

    def test_convert_mixed_field_types(self):
        """Test conversion with both list and dict fields."""

        @convert_to_schema("items", "metadata")
        class TestModel(BaseModel):
            items: list[ModelSchemaValue] = Field(default_factory=list)
            metadata: dict[str, ModelSchemaValue] = Field(default_factory=dict)

        model = TestModel(items=["item1", "item2"], metadata={"key": "value"})

        assert len(model.items) == 2
        assert len(model.metadata) == 1
        assert model.items[0].get_string() == "item1"
        assert model.metadata["key"].get_string() == "value"

    def test_convert_three_fields(self):
        """Test conversion of three fields at once."""

        @convert_to_schema("a", "b", "c")
        class TestModel(BaseModel):
            a: list[ModelSchemaValue] = Field(default_factory=list)
            b: list[ModelSchemaValue] = Field(default_factory=list)
            c: list[ModelSchemaValue] = Field(default_factory=list)

        model = TestModel(a=[1], b=[2], c=[3])

        assert model.a[0].to_value() == 1
        assert model.b[0].to_value() == 2
        assert model.c[0].to_value() == 3


@pytest.mark.unit
class TestConvertToSchemaEdgeCases:
    """Test @convert_to_schema edge cases and boundary conditions."""

    def test_convert_none_value(self):
        """Test handling of None value."""

        @convert_to_schema("values")
        class TestModel(BaseModel):
            values: list[ModelSchemaValue] = Field(default_factory=list)

        model = TestModel(values=None)

        assert model.values == []

    def test_convert_list_with_none_elements(self):
        """Test conversion of list containing None elements."""

        @convert_to_schema("values")
        class TestModel(BaseModel):
            values: list[ModelSchemaValue] = Field(default_factory=list)

        model = TestModel(values=[1, None, 3])

        assert len(model.values) == 3
        assert model.values[0].to_value() == 1
        assert model.values[1].to_value() is None
        assert model.values[2].to_value() == 3

    def test_convert_mixed_type_list(self):
        """Test conversion of list with mixed types."""

        @convert_to_schema("values")
        class TestModel(BaseModel):
            values: list[ModelSchemaValue] = Field(default_factory=list)

        model = TestModel(values=[1, "two", 3.0, True, None, {"nested": "dict"}])

        assert len(model.values) == 6
        assert model.values[0].is_number()
        assert model.values[1].is_string()
        assert model.values[2].is_number()
        assert model.values[3].is_boolean()
        assert model.values[4].is_null()
        assert model.values[5].is_object()

    def test_convert_deeply_nested_structure(self):
        """Test conversion of deeply nested structures."""

        @convert_to_schema("values")
        class TestModel(BaseModel):
            values: list[ModelSchemaValue] = Field(default_factory=list)

        nested = {"level1": {"level2": {"level3": [1, 2, 3]}}}
        model = TestModel(values=[nested])

        assert len(model.values) == 1
        assert model.values[0].is_object()
        # Verify the nested structure is preserved
        result = model.values[0].to_value()
        assert result == nested

    def test_convert_with_special_characters(self):
        """Test conversion with special characters in strings."""

        @convert_to_schema("values")
        class TestModel(BaseModel):
            values: list[ModelSchemaValue] = Field(default_factory=list)

        special_strings = [
            "hello\nworld",
            "tab\there",
            'quote"test',
            "unicode: \u00e9\u00e8\u00ea",
        ]
        model = TestModel(values=special_strings)

        assert len(model.values) == 4
        for i, s in enumerate(special_strings):
            assert model.values[i].get_string() == s

    def test_convert_empty_string(self):
        """Test conversion of empty string."""

        @convert_to_schema("values")
        class TestModel(BaseModel):
            values: list[ModelSchemaValue] = Field(default_factory=list)

        model = TestModel(values=[""])

        assert len(model.values) == 1
        assert model.values[0].get_string() == ""


@pytest.mark.unit
class TestConvertListToSchemaSpecialized:
    """Test specialized @convert_list_to_schema decorator."""

    def test_convert_list_only_strings(self):
        """Test specialized list decorator with strings."""

        @convert_list_to_schema("items")
        class TestModel(BaseModel):
            items: list[ModelSchemaValue] = Field(default_factory=list)

        model = TestModel(items=["a", "b", "c"])

        assert len(model.items) == 3
        assert all(v.is_string() for v in model.items)

    def test_convert_list_only_empty(self):
        """Test specialized list decorator with empty list."""

        @convert_list_to_schema("items")
        class TestModel(BaseModel):
            items: list[ModelSchemaValue] = Field(default_factory=list)

        model = TestModel(items=[])

        assert model.items == []

    def test_convert_list_only_pass_through(self):
        """Test specialized list decorator pass-through."""

        @convert_list_to_schema("items")
        class TestModel(BaseModel):
            items: list[ModelSchemaValue] = Field(default_factory=list)

        schema_items = [ModelSchemaValue.create_string("pre-converted")]
        model = TestModel(items=schema_items)

        assert len(model.items) == 1
        assert model.items[0].get_string() == "pre-converted"

    def test_convert_list_only_multiple_fields(self):
        """Test specialized list decorator with multiple fields."""

        @convert_list_to_schema("items", "tags", "categories")
        class TestModel(BaseModel):
            items: list[ModelSchemaValue] = Field(default_factory=list)
            tags: list[ModelSchemaValue] = Field(default_factory=list)
            categories: list[ModelSchemaValue] = Field(default_factory=list)

        model = TestModel(items=[1], tags=[2], categories=[3])

        assert model.items[0].to_value() == 1
        assert model.tags[0].to_value() == 2
        assert model.categories[0].to_value() == 3


@pytest.mark.unit
class TestConvertDictToSchemaSpecialized:
    """Test specialized @convert_dict_to_schema decorator."""

    def test_convert_dict_only_strings(self):
        """Test specialized dict decorator with strings."""

        @convert_dict_to_schema("metadata")
        class TestModel(BaseModel):
            metadata: dict[str, ModelSchemaValue] = Field(default_factory=dict)

        model = TestModel(metadata={"a": "1", "b": "2"})

        assert len(model.metadata) == 2
        assert all(v.is_string() for v in model.metadata.values())

    def test_convert_dict_only_empty(self):
        """Test specialized dict decorator with empty dict."""

        @convert_dict_to_schema("metadata")
        class TestModel(BaseModel):
            metadata: dict[str, ModelSchemaValue] = Field(default_factory=dict)

        model = TestModel(metadata={})

        assert model.metadata == {}

    def test_convert_dict_only_pass_through(self):
        """Test specialized dict decorator pass-through."""

        @convert_dict_to_schema("metadata")
        class TestModel(BaseModel):
            metadata: dict[str, ModelSchemaValue] = Field(default_factory=dict)

        schema_dict = {"key": ModelSchemaValue.create_string("pre-converted")}
        model = TestModel(metadata=schema_dict)

        assert len(model.metadata) == 1
        assert model.metadata["key"].get_string() == "pre-converted"

    def test_convert_dict_only_multiple_fields(self):
        """Test specialized dict decorator with multiple fields."""

        @convert_dict_to_schema("config", "settings", "options")
        class TestModel(BaseModel):
            config: dict[str, ModelSchemaValue] = Field(default_factory=dict)
            settings: dict[str, ModelSchemaValue] = Field(default_factory=dict)
            options: dict[str, ModelSchemaValue] = Field(default_factory=dict)

        model = TestModel(config={"a": 1}, settings={"b": 2}, options={"c": 3})

        assert model.config["a"].to_value() == 1
        assert model.settings["b"].to_value() == 2
        assert model.options["c"].to_value() == 3


@pytest.mark.unit
class TestConvertToSchemaModelSerialization:
    """Test @convert_to_schema with model serialization."""

    def test_model_dump_preserves_values(self):
        """Test that model_dump preserves the converted values."""

        @convert_to_schema("values")
        class TestModel(BaseModel):
            values: list[ModelSchemaValue] = Field(default_factory=list)

        model = TestModel(values=["hello", 42, True])
        dumped = model.model_dump()

        assert "values" in dumped
        assert len(dumped["values"]) == 3

    def test_model_validate_round_trip(self):
        """Test model validation round-trip."""

        @convert_to_schema("values")
        class TestModel(BaseModel):
            values: list[ModelSchemaValue] = Field(default_factory=list)

        original = TestModel(values=["hello", 42])
        dumped = original.model_dump()
        restored = TestModel.model_validate(dumped)

        assert len(restored.values) == 2
        assert restored.values[0].to_value() == "hello"
        assert restored.values[1].to_value() == 42


@pytest.mark.unit
class TestConvertToSchemaWithOtherFields:
    """Test @convert_to_schema models with non-converted fields."""

    def test_model_with_regular_fields(self):
        """Test model with both converted and regular fields."""

        @convert_to_schema("items")
        class TestModel(BaseModel):
            name: str
            count: int
            items: list[ModelSchemaValue] = Field(default_factory=list)

        model = TestModel(name="test", count=5, items=["a", "b"])

        assert model.name == "test"
        assert model.count == 5
        assert len(model.items) == 2
        assert model.items[0].get_string() == "a"

    def test_model_with_optional_fields(self):
        """Test model with optional fields."""

        @convert_to_schema("items")
        class TestModel(BaseModel):
            name: str | None = None
            items: list[ModelSchemaValue] = Field(default_factory=list)

        model = TestModel(items=["a"])

        assert model.name is None
        assert len(model.items) == 1


@pytest.mark.unit
class TestConvertToSchemaDecoratorImport:
    """Test decorator import from main decorators module."""

    def test_import_from_decorators_module(self):
        """Test that decorators can be imported from main module."""
        from omnibase_core.decorators import (
            convert_dict_to_schema,
            convert_list_to_schema,
            convert_to_schema,
        )

        # All should be callable
        assert callable(convert_to_schema)
        assert callable(convert_list_to_schema)
        assert callable(convert_dict_to_schema)

    def test_decorator_in_all_export(self):
        """Test that decorators are in __all__ export list."""
        from omnibase_core import decorators

        assert "convert_to_schema" in decorators.__all__
        assert "convert_list_to_schema" in decorators.__all__
        assert "convert_dict_to_schema" in decorators.__all__


@pytest.mark.unit
class TestConvertToSchemaTypeChecking:
    """Test type safety aspects of @convert_to_schema decorator."""

    def test_converted_values_are_model_schema_value(self):
        """Test that all converted values are ModelSchemaValue instances."""

        @convert_to_schema("values")
        class TestModel(BaseModel):
            values: list[ModelSchemaValue] = Field(default_factory=list)

        model = TestModel(values=[1, "two", True, None, [], {}])

        for value in model.values:
            assert isinstance(value, ModelSchemaValue)

    def test_value_type_is_preserved(self):
        """Test that original value types are preserved in ModelSchemaValue."""

        @convert_to_schema("values")
        class TestModel(BaseModel):
            values: list[ModelSchemaValue] = Field(default_factory=list)

        model = TestModel(values=[1, "text", True, None])

        assert model.values[0].value_type == "number"
        assert model.values[1].value_type == "string"
        assert model.values[2].value_type == "boolean"
        assert model.values[3].value_type == "null"

    def test_to_value_returns_original_type(self):
        """Test that to_value() returns the original type."""

        @convert_to_schema("values")
        class TestModel(BaseModel):
            values: list[ModelSchemaValue] = Field(default_factory=list)

        original_values = [42, "hello", True, None, [1, 2], {"a": 1}]
        model = TestModel(values=original_values)

        for i, original in enumerate(original_values):
            restored = model.values[i].to_value()
            assert restored == original
