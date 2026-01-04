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

from omnibase_core.decorators.decorator_convert_to_schema import (
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
        """Test handling of None value uses default_factory when field omitted.

        Note: Explicitly passing None to a non-optional field will fail Pydantic
        validation. To get the default, omit the field entirely.
        """

        @convert_to_schema("values")
        class TestModel(BaseModel):
            values: list[ModelSchemaValue] = Field(default_factory=list)

        # When field is omitted, default_factory provides empty list
        model = TestModel()
        assert model.values == []

    def test_convert_dict_none_value(self):
        """Test that dict fields with None don't get incorrectly converted to []."""

        @convert_to_schema("metadata")
        class TestModel(BaseModel):
            metadata: dict[str, ModelSchemaValue] | None = Field(default=None)

        # None should remain None for optional dict fields
        model = TestModel(metadata=None)
        assert model.metadata is None

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

    def test_convert_dict_with_none_values(self):
        """Test conversion of dict containing None values (not a None dict itself).

        This tests that when a dict has None as one of its VALUES (e.g., {"key": None}),
        the None is properly converted to ModelSchemaValue.null.
        """

        @convert_to_schema("metadata")
        class TestModel(BaseModel):
            metadata: dict[str, ModelSchemaValue] = Field(default_factory=dict)

        model = TestModel(metadata={"key1": "value", "key2": None, "key3": 42})

        assert len(model.metadata) == 3
        assert model.metadata["key1"].get_string() == "value"
        assert model.metadata["key2"].is_null()
        assert model.metadata["key2"].to_value() is None
        assert model.metadata["key3"].to_value() == 42

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

    def test_field_names_with_underscores_no_collision(self):
        """Test that field names with underscores don't cause validator name collisions.

        Previously, ("a_b", "c") and ("a", "b_c") would both produce validator name
        "_convert_to_schema_a_b_c". With double-underscore separator, they produce
        "_convert_to_schema_a_b__c" and "_convert_to_schema_a__b_c" respectively.
        """

        # Model 1: fields "a_b" and "c"
        @convert_to_schema("a_b", "c")
        class TestModel1(BaseModel):
            a_b: list[ModelSchemaValue] = Field(default_factory=list)
            c: list[ModelSchemaValue] = Field(default_factory=list)

        # Model 2: fields "a" and "b_c"
        @convert_to_schema("a", "b_c")
        class TestModel2(BaseModel):
            a: list[ModelSchemaValue] = Field(default_factory=list)
            b_c: list[ModelSchemaValue] = Field(default_factory=list)

        # Both should work correctly with their respective fields
        model1 = TestModel1(a_b=["x"], c=["y"])
        assert model1.a_b[0].get_string() == "x"
        assert model1.c[0].get_string() == "y"

        model2 = TestModel2(a=["p"], b_c=["q"])
        assert model2.a[0].get_string() == "p"
        assert model2.b_c[0].get_string() == "q"

        # Verify validator names are different (implementation detail, but good to verify)
        # Note: Uses internal attribute, this is a white-box test
        validators1 = TestModel1.__pydantic_decorators__.model_validators
        validators2 = TestModel2.__pydantic_decorators__.model_validators

        # Get the validator names that start with "_convert_to_schema_"
        names1 = [k for k in validators1 if k.startswith("_convert_to_schema_")]
        names2 = [k for k in validators2 if k.startswith("_convert_to_schema_")]

        assert len(names1) == 1
        assert len(names2) == 1
        assert names1[0] != names2[0], "Validator names should be different"

    def test_field_names_with_double_underscores_no_collision(self):
        """Test that field names with double underscores don't cause validator name collisions.

        Without escaping, ("a__b", "c") and ("a", "b__c") would both produce validator name
        "_convert_to_schema_a__b__c". With escaping __ to ___, they produce
        "_convert_to_schema_a___b__c" and "_convert_to_schema_a__b___c" respectively.
        """

        # Model 1: fields "a__b" and "c"
        @convert_to_schema("a__b", "c")
        class TestModel1(BaseModel):
            a__b: list[ModelSchemaValue] = Field(default_factory=list)
            c: list[ModelSchemaValue] = Field(default_factory=list)

        # Model 2: fields "a" and "b__c"
        @convert_to_schema("a", "b__c")
        class TestModel2(BaseModel):
            a: list[ModelSchemaValue] = Field(default_factory=list)
            b__c: list[ModelSchemaValue] = Field(default_factory=list)

        # Both should work correctly with their respective fields
        model1 = TestModel1(a__b=["x"], c=["y"])
        assert model1.a__b[0].get_string() == "x"
        assert model1.c[0].get_string() == "y"

        model2 = TestModel2(a=["p"], b__c=["q"])
        assert model2.a[0].get_string() == "p"
        assert model2.b__c[0].get_string() == "q"

        # Verify validator names are different (implementation detail, but good to verify)
        validators1 = TestModel1.__pydantic_decorators__.model_validators
        validators2 = TestModel2.__pydantic_decorators__.model_validators

        names1 = [k for k in validators1 if k.startswith("_convert_to_schema_")]
        names2 = [k for k in validators2 if k.startswith("_convert_to_schema_")]

        assert len(names1) == 1
        assert len(names2) == 1
        assert names1[0] != names2[0], (
            f"Validator names should be different: {names1[0]} vs {names2[0]}"
        )

        # Verify the escaped names are correct
        # "a__b" and "c" sorted = ["a__b", "c"], escaped = ["a___b", "c"]
        # -> "_convert_to_schema_a___b__c"
        assert "_convert_to_schema_a___b__c" in validators1
        # "a" and "b__c" sorted = ["a", "b__c"], escaped = ["a", "b___c"]
        # -> "_convert_to_schema_a__b___c"
        assert "_convert_to_schema_a__b___c" in validators2


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


@pytest.mark.unit
class TestVersionParsing:
    """Test version parsing helper function for pre-release version compatibility."""

    def test_parse_standard_version(self):
        """Test parsing standard version strings like '2.11.0'."""
        from omnibase_core.decorators.decorator_convert_to_schema import (
            _parse_version_component,
        )

        assert _parse_version_component("2.11.0", 0) == 2
        assert _parse_version_component("2.11.0", 1) == 11
        assert _parse_version_component("2.11.0", 2) == 0

    def test_parse_prerelease_version(self):
        """Test parsing pre-release versions like '2.11.0a1', '2.11.0rc1'."""
        from omnibase_core.decorators.decorator_convert_to_schema import (
            _parse_version_component,
        )

        # Alpha versions
        assert _parse_version_component("2.11.0a1", 0) == 2
        assert _parse_version_component("2.11.0a1", 1) == 11
        assert _parse_version_component("2.11.0a1", 2) == 0

        # Release candidate versions
        assert _parse_version_component("2.11.0rc1", 2) == 0

    def test_parse_dev_version(self):
        """Test parsing dev versions like '2.11-dev' or '3.0.0-dev'."""
        from omnibase_core.decorators.decorator_convert_to_schema import (
            _parse_version_component,
        )

        # Dev version with hyphen
        assert _parse_version_component("2.11-dev", 0) == 2
        assert _parse_version_component("2.11-dev", 1) == 11
        # Only two parts, so index 2 returns 0
        assert _parse_version_component("2.11-dev", 2) == 0

    def test_parse_component_beyond_end(self):
        """Test parsing component index beyond available parts."""
        from omnibase_core.decorators.decorator_convert_to_schema import (
            _parse_version_component,
        )

        assert _parse_version_component("2.11", 2) == 0
        assert _parse_version_component("2", 1) == 0

    def test_parse_non_numeric_start(self):
        """Test parsing version with non-numeric start returns 0."""
        from omnibase_core.decorators.decorator_convert_to_schema import (
            _parse_version_component,
        )

        # Edge case: component starts with non-digit
        assert _parse_version_component("v2.11.0", 0) == 0
        # But other parts parse fine
        assert _parse_version_component("v2.11.0", 1) == 11

    def test_parse_empty_string(self):
        """Test parsing empty version string."""
        from omnibase_core.decorators.decorator_convert_to_schema import (
            _parse_version_component,
        )

        assert _parse_version_component("", 0) == 0
        assert _parse_version_component("", 1) == 0

    def test_parse_hyphenated_prerelease_with_dot_suffix(self):
        """Test parsing version with hyphenated pre-release suffix containing dots.

        Covers edge case: "3.0.0-alpha.1" where the pre-release suffix
        includes a dot separator that could interfere with version splitting.
        """
        from omnibase_core.decorators.decorator_convert_to_schema import (
            _parse_version_component,
        )

        # "3.0.0-alpha.1" splits to ["3", "0", "0-alpha", "1"]
        # Major: 3
        assert _parse_version_component("3.0.0-alpha.1", 0) == 3
        # Minor: 0
        assert _parse_version_component("3.0.0-alpha.1", 1) == 0
        # Patch: "0-alpha" -> extracts leading "0"
        assert _parse_version_component("3.0.0-alpha.1", 2) == 0
        # 4th component: "1" -> 1
        assert _parse_version_component("3.0.0-alpha.1", 3) == 1

    def test_parse_build_metadata_suffix(self):
        """Test parsing version with build metadata suffix.

        Covers edge case: "2.11-dev+commit.sha" where build metadata
        (after +) contains additional dots and characters.
        """
        from omnibase_core.decorators.decorator_convert_to_schema import (
            _parse_version_component,
        )

        # "2.11-dev+commit.sha" splits to ["2", "11-dev+commit", "sha"]
        # Major: 2
        assert _parse_version_component("2.11-dev+commit.sha", 0) == 2
        # Minor: "11-dev+commit" -> extracts leading "11"
        assert _parse_version_component("2.11-dev+commit.sha", 1) == 11
        # Patch: "sha" -> no leading digits -> 0
        assert _parse_version_component("2.11-dev+commit.sha", 2) == 0

    def test_parse_four_component_version_with_dev_suffix(self):
        """Test parsing 4-component version with dev suffix.

        Covers edge case: "1.0.0.dev1" which is a common pattern
        in Python packaging for development versions.
        """
        from omnibase_core.decorators.decorator_convert_to_schema import (
            _parse_version_component,
        )

        # "1.0.0.dev1" splits to ["1", "0", "0", "dev1"]
        # Major: 1
        assert _parse_version_component("1.0.0.dev1", 0) == 1
        # Minor: 0
        assert _parse_version_component("1.0.0.dev1", 1) == 0
        # Patch: 0
        assert _parse_version_component("1.0.0.dev1", 2) == 0
        # 4th component: "dev1" -> no leading digits -> 0
        assert _parse_version_component("1.0.0.dev1", 3) == 0

    def test_parse_component_all_non_numeric(self):
        """Test parsing component that is entirely non-numeric.

        Covers edge case where a version component has no leading digits at all.
        """
        from omnibase_core.decorators.decorator_convert_to_schema import (
            _parse_version_component,
        )

        # "alpha" -> no leading digits -> 0
        assert _parse_version_component("1.0.alpha", 2) == 0
        # "beta-2" starts with non-digit -> 0
        assert _parse_version_component("1.0.beta-2", 2) == 0


@pytest.mark.unit
class TestEscapeFieldNameForValidator:
    """Test the field name escape function for validator name generation."""

    def test_escape_single_underscore_unchanged(self):
        """Test that single underscores are not escaped."""
        from omnibase_core.decorators.decorator_convert_to_schema import (
            _escape_field_name_for_validator,
        )

        assert _escape_field_name_for_validator("a_b") == "a_b"
        assert _escape_field_name_for_validator("foo_bar_baz") == "foo_bar_baz"

    def test_escape_double_underscore(self):
        """Test that double underscores are escaped to triple."""
        from omnibase_core.decorators.decorator_convert_to_schema import (
            _escape_field_name_for_validator,
        )

        assert _escape_field_name_for_validator("a__b") == "a___b"
        assert _escape_field_name_for_validator("foo__bar") == "foo___bar"

    def test_escape_multiple_double_underscores(self):
        """Test that multiple double underscores are all escaped."""
        from omnibase_core.decorators.decorator_convert_to_schema import (
            _escape_field_name_for_validator,
        )

        assert _escape_field_name_for_validator("a__b__c") == "a___b___c"

    def test_escape_triple_underscore(self):
        """Test that triple underscores have their __ portion escaped."""
        from omnibase_core.decorators.decorator_convert_to_schema import (
            _escape_field_name_for_validator,
        )

        # "a___b" contains "a__" + "_b", so __ gets escaped to ___
        # Result: "a____b" (4 underscores)
        assert _escape_field_name_for_validator("a___b") == "a____b"

    def test_escape_no_underscores(self):
        """Test that names without underscores are unchanged."""
        from omnibase_core.decorators.decorator_convert_to_schema import (
            _escape_field_name_for_validator,
        )

        assert _escape_field_name_for_validator("abc") == "abc"
        assert _escape_field_name_for_validator("foobar") == "foobar"


@pytest.mark.unit
class TestDictNoneHandlingEdgeCases:
    """Test edge cases for dict conversion with None values."""

    def test_dict_with_all_none_values(self):
        """Test conversion of dict where ALL values are None."""

        @convert_to_schema("metadata")
        class TestModel(BaseModel):
            metadata: dict[str, ModelSchemaValue] = Field(default_factory=dict)

        model = TestModel(metadata={"key1": None, "key2": None, "key3": None})

        assert len(model.metadata) == 3
        assert all(v.is_null() for v in model.metadata.values())
        assert model.metadata["key1"].to_value() is None
        assert model.metadata["key2"].to_value() is None
        assert model.metadata["key3"].to_value() is None

    def test_dict_with_first_value_none(self):
        """Test conversion where the first value happens to be None.

        Dict iteration order is insertion order in Python 3.7+, so this tests
        the scenario where the first iterated value is None but others need
        conversion.
        """

        @convert_to_schema("metadata")
        class TestModel(BaseModel):
            metadata: dict[str, ModelSchemaValue] = Field(default_factory=dict)

        # Create dict with None as first value
        model = TestModel(metadata={"first": None, "second": "value", "third": 42})

        assert len(model.metadata) == 3
        assert model.metadata["first"].is_null()
        assert model.metadata["second"].get_string() == "value"
        assert model.metadata["third"].to_value() == 42
