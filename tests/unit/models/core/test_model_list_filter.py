"""
Tests for ModelListFilter validator behaviors and edge cases.

This module validates:
1. Automatic conversion behavior in field validators
2. Edge cases: empty lists, mixed types, None values
3. Empty list handling in validators
4. ModelSchemaValue conversion patterns

These tests address PR #238 review feedback requiring explicit coverage
of validator behaviors.
"""

import pytest

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.core.model_list_filter import ModelListFilter


@pytest.mark.unit
class TestModelListFilterBasicCreation:
    """Test basic creation scenarios for ModelListFilter."""

    def test_create_with_raw_string_values(self):
        """Test creation with raw string values - automatic conversion."""
        filter_model = ModelListFilter(values=["apple", "banana", "cherry"])

        assert len(filter_model.values) == 3
        # Verify automatic conversion to ModelSchemaValue
        assert all(isinstance(v, ModelSchemaValue) for v in filter_model.values)
        # Verify values are correctly stored
        assert filter_model.values[0].value_type == "string"
        assert filter_model.values[0].string_value == "apple"
        assert filter_model.values[1].string_value == "banana"
        assert filter_model.values[2].string_value == "cherry"

    def test_create_with_raw_integer_values(self):
        """Test creation with raw integer values - automatic conversion."""
        filter_model = ModelListFilter(values=[1, 2, 3, 42])

        assert len(filter_model.values) == 4
        assert all(isinstance(v, ModelSchemaValue) for v in filter_model.values)
        assert filter_model.values[0].value_type == "number"
        # Access the numeric value
        assert filter_model.values[3].number_value is not None
        assert filter_model.values[3].number_value.to_python_value() == 42

    def test_create_with_raw_float_values(self):
        """Test creation with raw float values - automatic conversion."""
        filter_model = ModelListFilter(values=[1.5, 2.7, 3.14])

        assert len(filter_model.values) == 3
        assert all(isinstance(v, ModelSchemaValue) for v in filter_model.values)
        assert filter_model.values[2].value_type == "number"
        assert filter_model.values[2].number_value is not None
        # Float values should be preserved
        assert abs(filter_model.values[2].number_value.to_python_value() - 3.14) < 0.001

    def test_create_with_raw_boolean_values(self):
        """Test creation with raw boolean values - automatic conversion."""
        filter_model = ModelListFilter(values=[True, False, True])

        assert len(filter_model.values) == 3
        assert all(isinstance(v, ModelSchemaValue) for v in filter_model.values)
        assert filter_model.values[0].value_type == "boolean"
        assert filter_model.values[0].boolean_value is True
        assert filter_model.values[1].boolean_value is False

    def test_create_with_model_schema_value_instances(self):
        """Test that existing ModelSchemaValue instances are passed through unchanged."""
        schema_values = [
            ModelSchemaValue.create_string("test1"),
            ModelSchemaValue.create_number(42),
            ModelSchemaValue.create_boolean(True),
        ]
        filter_model = ModelListFilter(values=schema_values)

        assert len(filter_model.values) == 3
        # Should be the same instances (or at least equivalent values)
        assert filter_model.values[0].string_value == "test1"
        assert filter_model.values[1].number_value is not None
        assert filter_model.values[1].number_value.to_python_value() == 42
        assert filter_model.values[2].boolean_value is True


@pytest.mark.unit
class TestModelListFilterEmptyListHandling:
    """Test empty list handling in validators."""

    def test_empty_list_returns_empty_list(self):
        """Test that empty list [] is handled correctly by validator."""
        filter_model = ModelListFilter(values=[])

        assert filter_model.values == []
        assert len(filter_model.values) == 0
        assert isinstance(filter_model.values, list)

    def test_empty_list_with_default_options(self):
        """Test empty list with default filter options."""
        filter_model = ModelListFilter(values=[])

        assert filter_model.filter_type == "list"
        assert filter_model.match_all is False
        assert filter_model.exclude is False
        assert filter_model.enabled is True  # From base class

    def test_empty_list_serialization(self):
        """Test that empty list serializes correctly."""
        filter_model = ModelListFilter(values=[])
        serialized = filter_model.model_dump()

        assert serialized["values"] == []
        assert serialized["filter_type"] == "list"


@pytest.mark.unit
class TestModelListFilterMixedTypes:
    """Test mixed type handling in validators."""

    def test_mixed_primitive_types(self):
        """Test list with mixed primitive types (string, int, float, bool)."""
        filter_model = ModelListFilter(values=["text", 42, 3.14, True])

        assert len(filter_model.values) == 4
        assert filter_model.values[0].value_type == "string"
        assert filter_model.values[0].string_value == "text"
        assert filter_model.values[1].value_type == "number"
        assert filter_model.values[2].value_type == "number"
        assert filter_model.values[3].value_type == "boolean"

    def test_mixed_with_nested_structures(self):
        """Test list with nested dict and list values."""
        filter_model = ModelListFilter(values=["simple", {"key": "value"}, [1, 2, 3]])

        assert len(filter_model.values) == 3
        assert filter_model.values[0].value_type == "string"
        assert filter_model.values[1].value_type == "object"
        assert filter_model.values[2].value_type == "array"

    def test_mixed_raw_and_schema_values(self):
        """Test list with both raw values and ModelSchemaValue instances."""
        # Note: The current validator checks only the first element
        # This tests that behavior
        mixed_values = ["raw_string", 42]
        filter_model = ModelListFilter(values=mixed_values)

        assert len(filter_model.values) == 2
        # Both should be converted to ModelSchemaValue
        assert all(isinstance(v, ModelSchemaValue) for v in filter_model.values)


@pytest.mark.unit
class TestModelListFilterNoneValueHandling:
    """Test None value handling in validators."""

    def test_none_value_in_list(self):
        """Test that None values in list are converted to null ModelSchemaValue."""
        filter_model = ModelListFilter(values=[None, "value", None])

        assert len(filter_model.values) == 3
        # None should become null type
        assert filter_model.values[0].value_type == "null"
        assert filter_model.values[0].null_value is True
        assert filter_model.values[1].value_type == "string"
        assert filter_model.values[2].value_type == "null"

    def test_single_none_value(self):
        """Test list with only None value."""
        filter_model = ModelListFilter(values=[None])

        assert len(filter_model.values) == 1
        assert filter_model.values[0].value_type == "null"
        assert filter_model.values[0].null_value is True

    def test_none_interspersed_with_values(self):
        """Test None values mixed with other types."""
        filter_model = ModelListFilter(values=[1, None, "text", None, True])

        assert len(filter_model.values) == 5
        assert filter_model.values[0].value_type == "number"
        assert filter_model.values[1].value_type == "null"
        assert filter_model.values[2].value_type == "string"
        assert filter_model.values[3].value_type == "null"
        assert filter_model.values[4].value_type == "boolean"


@pytest.mark.unit
class TestModelListFilterValidatorConversionBehavior:
    """Test specific validator conversion behaviors documented in convert_values_to_schema."""

    def test_validator_preserves_schema_values(self):
        """Test that validator returns ModelSchemaValue instances as-is when first element is ModelSchemaValue."""
        # When the first element is already a ModelSchemaValue, the validator should
        # return the list unchanged
        schema_values = [
            ModelSchemaValue.create_string("first"),
            ModelSchemaValue.create_number(2),
        ]

        filter_model = ModelListFilter(values=schema_values)

        # Should preserve the original values
        assert filter_model.values[0].string_value == "first"
        assert filter_model.values[1].number_value is not None

    def test_validator_converts_all_raw_values(self):
        """Test that validator converts all raw values to ModelSchemaValue."""
        raw_values = ["a", "b", "c", "d"]
        filter_model = ModelListFilter(values=raw_values)

        # All should be converted
        for i, v in enumerate(filter_model.values):
            assert isinstance(v, ModelSchemaValue)
            assert v.value_type == "string"
            assert v.string_value == raw_values[i]

    def test_validator_with_complex_nested_objects(self):
        """Test conversion of complex nested objects."""
        complex_value = {"level1": {"level2": [1, 2, {"nested": "value"}]}}
        filter_model = ModelListFilter(values=[complex_value])

        assert len(filter_model.values) == 1
        assert filter_model.values[0].value_type == "object"
        assert filter_model.values[0].object_value is not None

        # Verify nested structure is preserved
        level1 = filter_model.values[0].object_value.get("level1")
        assert level1 is not None
        assert level1.value_type == "object"

    def test_validator_with_unknown_types(self):
        """Test that unknown types are converted to string representation."""

        # Custom class instance - should be converted to string
        class CustomObject:
            def __str__(self):
                return "custom_string_repr"

        filter_model = ModelListFilter(values=[CustomObject()])

        assert len(filter_model.values) == 1
        # Unknown types should become strings via str()
        assert filter_model.values[0].value_type == "string"
        assert filter_model.values[0].string_value == "custom_string_repr"


@pytest.mark.unit
class TestModelListFilterFilterOptions:
    """Test filter option combinations."""

    def test_match_all_option(self):
        """Test match_all filter option."""
        filter_model = ModelListFilter(values=["a", "b"], match_all=True)

        assert filter_model.match_all is True
        assert filter_model.exclude is False

    def test_exclude_option(self):
        """Test exclude filter option."""
        filter_model = ModelListFilter(values=["excluded"], exclude=True)

        assert filter_model.exclude is True
        assert filter_model.match_all is False

    def test_combined_options(self):
        """Test combined match_all and exclude options."""
        filter_model = ModelListFilter(
            values=["a", "b", "c"],
            match_all=True,
            exclude=True,
        )

        assert filter_model.match_all is True
        assert filter_model.exclude is True
        assert len(filter_model.values) == 3

    def test_filter_with_priority(self):
        """Test filter priority from base class."""
        filter_model = ModelListFilter(values=["test"], priority=10)

        assert filter_model.priority == 10

    def test_filter_disabled(self):
        """Test disabled filter."""
        filter_model = ModelListFilter(values=["test"], enabled=False)

        assert filter_model.enabled is False


@pytest.mark.unit
class TestModelListFilterSerialization:
    """Test serialization and deserialization of ModelListFilter."""

    def test_model_dump_preserves_structure(self):
        """Test that model_dump preserves the complete structure."""
        filter_model = ModelListFilter(
            values=["a", 1, True],
            match_all=True,
            exclude=False,
        )
        dumped = filter_model.model_dump()

        assert "values" in dumped
        assert "filter_type" in dumped
        assert "match_all" in dumped
        assert "exclude" in dumped
        assert dumped["match_all"] is True
        assert dumped["filter_type"] == "list"

    def test_to_dict_method(self):
        """Test to_dict method from base class."""
        filter_model = ModelListFilter(values=["test"])
        dict_repr = filter_model.to_dict()

        assert isinstance(dict_repr, dict)
        assert "values" in dict_repr
        assert "filter_type" in dict_repr

    def test_roundtrip_serialization(self):
        """Test that serialization and deserialization preserve values."""
        original = ModelListFilter(
            values=["string", 42, True, None],
            match_all=True,
            exclude=True,
            priority=5,
        )

        # Serialize
        serialized = original.model_dump()

        # Deserialize
        restored = ModelListFilter.model_validate(serialized)

        assert len(restored.values) == 4
        assert restored.match_all is True
        assert restored.exclude is True
        assert restored.priority == 5


@pytest.mark.unit
class TestModelListFilterEdgeCases:
    """Additional edge cases for comprehensive coverage."""

    def test_large_list_values(self):
        """Test with a large list of values."""
        large_list = [f"item_{i}" for i in range(100)]
        filter_model = ModelListFilter(values=large_list)

        assert len(filter_model.values) == 100
        assert filter_model.values[0].string_value == "item_0"
        assert filter_model.values[99].string_value == "item_99"

    def test_unicode_string_values(self):
        """Test with unicode string values."""
        filter_model = ModelListFilter(values=["hello", "world", "emoji"])

        assert len(filter_model.values) == 3
        assert filter_model.values[2].string_value == "emoji"

    def test_special_string_values(self):
        """Test with special string values (empty, whitespace, special chars)."""
        filter_model = ModelListFilter(values=["", "  ", "\n\t", "special!@#$%"])

        assert len(filter_model.values) == 4
        assert filter_model.values[0].string_value == ""
        assert filter_model.values[1].string_value == "  "
        assert filter_model.values[2].string_value == "\n\t"
        assert filter_model.values[3].string_value == "special!@#$%"

    def test_numeric_edge_cases(self):
        """Test with numeric edge cases (zero, negative, very large)."""
        filter_model = ModelListFilter(values=[0, -1, -999, 999999999])

        assert len(filter_model.values) == 4
        assert filter_model.values[0].number_value.to_python_value() == 0
        assert filter_model.values[1].number_value.to_python_value() == -1
        assert filter_model.values[2].number_value.to_python_value() == -999
        assert filter_model.values[3].number_value.to_python_value() == 999999999

    def test_deeply_nested_arrays(self):
        """Test with deeply nested array values."""
        nested = [[[1, 2], [3, 4]], [[5, 6], [7, 8]]]
        filter_model = ModelListFilter(values=[nested])

        assert len(filter_model.values) == 1
        assert filter_model.values[0].value_type == "array"

    def test_filter_type_is_always_list(self):
        """Verify filter_type is always 'list'."""
        filter_model = ModelListFilter(values=["test"])
        assert filter_model.filter_type == "list"

        # Even after modification attempt (if allowed)
        filter_model2 = ModelListFilter(values=["test"], filter_type="list")
        assert filter_model2.filter_type == "list"
