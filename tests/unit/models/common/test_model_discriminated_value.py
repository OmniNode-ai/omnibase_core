# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelDiscriminatedValue."""

import json

import pytest

from omnibase_core.enums.enum_discriminated_value_type import EnumDiscriminatedValueType
from omnibase_core.models.common.model_discriminated_value import (
    ModelDiscriminatedValue,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


@pytest.mark.unit
class TestModelDiscriminatedValueInstantiation:
    """Tests for ModelDiscriminatedValue instantiation with primitive types."""

    def test_create_from_bool(self) -> None:
        """Test creating discriminated value from boolean."""
        value = ModelDiscriminatedValue.from_bool(True)
        assert value.value_type == EnumDiscriminatedValueType.BOOL
        assert value.bool_value is True
        assert value.get_value() is True

    def test_create_from_bool_false(self) -> None:
        """Test creating discriminated value from boolean False."""
        value = ModelDiscriminatedValue.from_bool(False)
        assert value.value_type == EnumDiscriminatedValueType.BOOL
        assert value.bool_value is False
        assert value.get_value() is False

    def test_create_from_int(self) -> None:
        """Test creating discriminated value from integer."""
        value = ModelDiscriminatedValue.from_int(42)
        assert value.value_type == EnumDiscriminatedValueType.INT
        assert value.int_value == 42
        assert value.get_value() == 42

    def test_create_from_int_negative(self) -> None:
        """Test creating discriminated value from negative integer."""
        value = ModelDiscriminatedValue.from_int(-100)
        assert value.value_type == EnumDiscriminatedValueType.INT
        assert value.int_value == -100
        assert value.get_value() == -100

    def test_create_from_int_zero(self) -> None:
        """Test creating discriminated value from zero integer."""
        value = ModelDiscriminatedValue.from_int(0)
        assert value.value_type == EnumDiscriminatedValueType.INT
        assert value.int_value == 0
        assert value.get_value() == 0

    def test_create_from_float(self) -> None:
        """Test creating discriminated value from float."""
        value = ModelDiscriminatedValue.from_float(3.14)
        assert value.value_type == EnumDiscriminatedValueType.FLOAT
        assert value.float_value == 3.14
        assert value.get_value() == 3.14

    def test_create_from_float_negative(self) -> None:
        """Test creating discriminated value from negative float."""
        value = ModelDiscriminatedValue.from_float(-99.99)
        assert value.value_type == EnumDiscriminatedValueType.FLOAT
        assert value.float_value == -99.99

    def test_create_from_float_zero(self) -> None:
        """Test creating discriminated value from zero float."""
        value = ModelDiscriminatedValue.from_float(0.0)
        assert value.value_type == EnumDiscriminatedValueType.FLOAT
        assert value.float_value == 0.0

    def test_create_from_str(self) -> None:
        """Test creating discriminated value from string."""
        value = ModelDiscriminatedValue.from_str("test")
        assert value.value_type == EnumDiscriminatedValueType.STR
        assert value.str_value == "test"
        assert value.get_value() == "test"

    def test_create_from_str_empty(self) -> None:
        """Test creating discriminated value from empty string."""
        value = ModelDiscriminatedValue.from_str("")
        assert value.value_type == EnumDiscriminatedValueType.STR
        assert value.str_value == ""
        assert value.get_value() == ""


@pytest.mark.unit
class TestModelDiscriminatedValueCollections:
    """Tests for ModelDiscriminatedValue with collection types."""

    def test_create_from_dict(self) -> None:
        """Test creating discriminated value from dictionary."""
        test_dict = {"key1": "value1", "key2": 42}
        value = ModelDiscriminatedValue.from_dict(test_dict)
        assert value.value_type == EnumDiscriminatedValueType.DICT
        assert value.dict_value == test_dict
        assert value.get_value() == test_dict

    def test_create_from_empty_dict(self) -> None:
        """Test creating discriminated value from empty dictionary."""
        value = ModelDiscriminatedValue.from_dict({})
        assert value.value_type == EnumDiscriminatedValueType.DICT
        assert value.dict_value == {}
        assert value.get_value() == {}

    def test_create_from_nested_dict(self) -> None:
        """Test creating discriminated value from nested dictionary."""
        nested_dict = {"outer": {"inner": "value"}}
        value = ModelDiscriminatedValue.from_dict(nested_dict)
        assert value.value_type == EnumDiscriminatedValueType.DICT
        assert value.dict_value == nested_dict
        assert value.get_value() == nested_dict

    def test_create_from_list(self) -> None:
        """Test creating discriminated value from list."""
        test_list = [1, 2, 3, "four"]
        value = ModelDiscriminatedValue.from_list(test_list)
        assert value.value_type == EnumDiscriminatedValueType.LIST
        assert value.list_value == test_list
        assert value.get_value() == test_list

    def test_create_from_empty_list(self) -> None:
        """Test creating discriminated value from empty list."""
        value = ModelDiscriminatedValue.from_list([])
        assert value.value_type == EnumDiscriminatedValueType.LIST
        assert value.list_value == []
        assert value.get_value() == []

    def test_create_from_nested_list(self) -> None:
        """Test creating discriminated value from nested list."""
        nested_list = [[1, 2], [3, 4], ["a", "b"]]
        value = ModelDiscriminatedValue.from_list(nested_list)
        assert value.value_type == EnumDiscriminatedValueType.LIST
        assert value.list_value == nested_list
        assert value.get_value() == nested_list

    def test_dict_with_mixed_types(self) -> None:
        """Test dictionary with mixed value types."""
        mixed_dict = {"str": "value", "int": 42, "bool": True, "float": 3.14}
        value = ModelDiscriminatedValue.from_dict(mixed_dict)
        assert value.value_type == EnumDiscriminatedValueType.DICT
        assert value.dict_value == mixed_dict

    def test_list_with_mixed_types(self) -> None:
        """Test list with mixed value types."""
        mixed_list = ["string", 42, True, 3.14, None]
        value = ModelDiscriminatedValue.from_list(mixed_list)
        assert value.value_type == EnumDiscriminatedValueType.LIST
        assert value.list_value == mixed_list


@pytest.mark.unit
class TestModelDiscriminatedValueAutoDetection:
    """Tests for ModelDiscriminatedValue automatic type detection."""

    def test_from_any_bool(self) -> None:
        """Test from_any with boolean (must be detected before int)."""
        value = ModelDiscriminatedValue.from_any(True)
        assert value.value_type == EnumDiscriminatedValueType.BOOL
        assert value.get_value() is True

    def test_from_any_int(self) -> None:
        """Test from_any with integer."""
        value = ModelDiscriminatedValue.from_any(42)
        assert value.value_type == EnumDiscriminatedValueType.INT
        assert value.get_value() == 42

    def test_from_any_float(self) -> None:
        """Test from_any with float."""
        value = ModelDiscriminatedValue.from_any(3.14)
        assert value.value_type == EnumDiscriminatedValueType.FLOAT
        assert value.get_value() == 3.14

    def test_from_any_str(self) -> None:
        """Test from_any with string."""
        value = ModelDiscriminatedValue.from_any("test")
        assert value.value_type == EnumDiscriminatedValueType.STR
        assert value.get_value() == "test"

    def test_from_any_dict(self) -> None:
        """Test from_any with dictionary."""
        test_dict = {"key": "value"}
        value = ModelDiscriminatedValue.from_any(test_dict)
        assert value.value_type == EnumDiscriminatedValueType.DICT
        assert value.get_value() == test_dict

    def test_from_any_list(self) -> None:
        """Test from_any with list."""
        test_list = [1, 2, 3]
        value = ModelDiscriminatedValue.from_any(test_list)
        assert value.value_type == EnumDiscriminatedValueType.LIST
        assert value.get_value() == test_list

    def test_from_any_bool_not_confused_with_int(self) -> None:
        """Test that boolean True is not detected as integer 1."""
        bool_value = ModelDiscriminatedValue.from_any(True)
        int_value = ModelDiscriminatedValue.from_any(1)
        assert bool_value.value_type == EnumDiscriminatedValueType.BOOL
        assert int_value.value_type == EnumDiscriminatedValueType.INT
        assert bool_value.value_type != int_value.value_type  # type: ignore[comparison-overlap]


@pytest.mark.unit
class TestModelDiscriminatedValueMetadata:
    """Tests for ModelDiscriminatedValue metadata support."""

    def test_create_with_metadata(self) -> None:
        """Test creating value with metadata."""
        metadata = {"source": "api", "version": "1.0"}
        value = ModelDiscriminatedValue.from_int(42, metadata=metadata)
        assert value.metadata == metadata

    def test_create_without_metadata(self) -> None:
        """Test creating value without metadata."""
        value = ModelDiscriminatedValue.from_str("test")
        assert value.metadata == {}

    def test_metadata_preserved_through_operations(self) -> None:
        """Test that metadata is preserved."""
        metadata = {"key": "value"}
        value = ModelDiscriminatedValue.from_bool(True, metadata=metadata)
        assert value.metadata["key"] == "value"


@pytest.mark.unit
class TestModelDiscriminatedValueValidation:
    """Tests for ModelDiscriminatedValue validation."""

    def test_validation_single_value_required(self) -> None:
        """Test that exactly one value must be set."""
        # Valid: only int_value is set
        value = ModelDiscriminatedValue(
            value_type=EnumDiscriminatedValueType.INT, int_value=42
        )
        assert value.int_value == 42

    def test_validation_missing_required_value(self) -> None:
        """Test that required value must be set for type."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDiscriminatedValue(value_type=EnumDiscriminatedValueType.STR)
        assert "must be set" in str(exc_info.value) or "is None" in str(exc_info.value)

    def test_validation_wrong_value_type(self) -> None:
        """Test that wrong value for type raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDiscriminatedValue(
                value_type=EnumDiscriminatedValueType.STR, int_value=42
            )
        assert "is None" in str(exc_info.value) or "must be set" in str(exc_info.value)

    def test_validation_multiple_values(self) -> None:
        """Test that multiple values raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDiscriminatedValue(
                value_type=EnumDiscriminatedValueType.INT,
                int_value=42,
                str_value="test",
            )
        assert "Exactly one value must be set" in str(exc_info.value)

    def test_dict_json_serializable_validation(self) -> None:
        """Test that dict values must be JSON serializable."""
        # Valid dict
        valid_dict = {"key": "value", "number": 42}
        value = ModelDiscriminatedValue.from_dict(valid_dict)
        assert value.dict_value == valid_dict

        # Dict is validated during model creation
        # Non-serializable objects should raise error
        class NonSerializable:
            pass

        with pytest.raises(ModelOnexError) as exc_info:
            ModelDiscriminatedValue.from_dict({"obj": NonSerializable()})
        assert "not JSON serializable" in str(exc_info.value)

    def test_list_json_serializable_validation(self) -> None:
        """Test that list values must be JSON serializable."""
        # Valid list
        valid_list = [1, "two", 3.0, True]
        value = ModelDiscriminatedValue.from_list(valid_list)
        assert value.list_value == valid_list

        # Non-serializable objects should raise error
        class NonSerializable:
            pass

        with pytest.raises(ModelOnexError) as exc_info:
            ModelDiscriminatedValue.from_list([1, NonSerializable()])
        assert "not JSON serializable" in str(exc_info.value)


@pytest.mark.unit
class TestModelDiscriminatedValueTypeChecking:
    """Tests for ModelDiscriminatedValue type checking methods."""

    def test_get_type_bool(self) -> None:
        """Test get_type for boolean."""
        value = ModelDiscriminatedValue.from_bool(True)
        assert value.get_type() == bool

    def test_get_type_int(self) -> None:
        """Test get_type for integer."""
        value = ModelDiscriminatedValue.from_int(42)
        assert value.get_type() == int

    def test_get_type_float(self) -> None:
        """Test get_type for float."""
        value = ModelDiscriminatedValue.from_float(3.14)
        assert value.get_type() == float

    def test_get_type_str(self) -> None:
        """Test get_type for string."""
        value = ModelDiscriminatedValue.from_str("test")
        assert value.get_type() == str

    def test_get_type_dict(self) -> None:
        """Test get_type for dict."""
        value = ModelDiscriminatedValue.from_dict({"key": "value"})
        assert value.get_type() == dict

    def test_get_type_list(self) -> None:
        """Test get_type for list."""
        value = ModelDiscriminatedValue.from_list([1, 2, 3])
        assert value.get_type() == list

    def test_is_type_matches(self) -> None:
        """Test is_type with matching type."""
        value = ModelDiscriminatedValue.from_int(42)
        assert value.is_type(int) is True
        assert value.is_type(str) is False

    def test_is_type_all_types(self) -> None:
        """Test is_type for all supported types."""
        assert ModelDiscriminatedValue.from_bool(True).is_type(bool) is True
        assert ModelDiscriminatedValue.from_int(42).is_type(int) is True
        assert ModelDiscriminatedValue.from_float(3.14).is_type(float) is True
        assert ModelDiscriminatedValue.from_str("test").is_type(str) is True
        assert ModelDiscriminatedValue.from_dict({}).is_type(dict) is True
        assert ModelDiscriminatedValue.from_list([]).is_type(list) is True


@pytest.mark.unit
class TestModelDiscriminatedValueTypeCategories:
    """Tests for ModelDiscriminatedValue type category methods."""

    def test_is_primitive_true(self) -> None:
        """Test is_primitive for primitive types."""
        assert ModelDiscriminatedValue.from_bool(True).is_primitive() is True
        assert ModelDiscriminatedValue.from_int(42).is_primitive() is True
        assert ModelDiscriminatedValue.from_float(3.14).is_primitive() is True
        assert ModelDiscriminatedValue.from_str("test").is_primitive() is True

    def test_is_primitive_false(self) -> None:
        """Test is_primitive for collection types."""
        assert ModelDiscriminatedValue.from_dict({}).is_primitive() is False
        assert ModelDiscriminatedValue.from_list([]).is_primitive() is False

    def test_is_numeric_true(self) -> None:
        """Test is_numeric for numeric types."""
        assert ModelDiscriminatedValue.from_int(42).is_numeric() is True
        assert ModelDiscriminatedValue.from_float(3.14).is_numeric() is True

    def test_is_numeric_false(self) -> None:
        """Test is_numeric for non-numeric types."""
        assert ModelDiscriminatedValue.from_bool(True).is_numeric() is False
        assert ModelDiscriminatedValue.from_str("test").is_numeric() is False
        assert ModelDiscriminatedValue.from_dict({}).is_numeric() is False
        assert ModelDiscriminatedValue.from_list([]).is_numeric() is False

    def test_is_collection_true(self) -> None:
        """Test is_collection for collection types."""
        assert ModelDiscriminatedValue.from_dict({}).is_collection() is True
        assert ModelDiscriminatedValue.from_list([]).is_collection() is True

    def test_is_collection_false(self) -> None:
        """Test is_collection for non-collection types."""
        assert ModelDiscriminatedValue.from_bool(True).is_collection() is False
        assert ModelDiscriminatedValue.from_int(42).is_collection() is False
        assert ModelDiscriminatedValue.from_float(3.14).is_collection() is False
        assert ModelDiscriminatedValue.from_str("test").is_collection() is False


@pytest.mark.unit
class TestModelDiscriminatedValueComparison:
    """Tests for ModelDiscriminatedValue comparison operations."""

    def test_equality_same_type_same_value(self) -> None:
        """Test equality for same type and value."""
        value1 = ModelDiscriminatedValue.from_int(42)
        value2 = ModelDiscriminatedValue.from_int(42)
        assert value1 == value2

    def test_equality_same_type_different_value(self) -> None:
        """Test equality for same type, different value."""
        value1 = ModelDiscriminatedValue.from_int(42)
        value2 = ModelDiscriminatedValue.from_int(99)
        assert value1 != value2

    def test_equality_different_types(self) -> None:
        """Test equality for different types."""
        value1 = ModelDiscriminatedValue.from_int(42)
        value2 = ModelDiscriminatedValue.from_str("42")
        assert value1 != value2

    def test_equality_with_raw_value(self) -> None:
        """Test equality with raw Python value."""
        value = ModelDiscriminatedValue.from_int(42)
        assert value == 42

    def test_equality_with_raw_string(self) -> None:
        """Test equality with raw string."""
        value = ModelDiscriminatedValue.from_str("test")
        assert value == "test"

    def test_equality_with_raw_bool(self) -> None:
        """Test equality with raw boolean."""
        value = ModelDiscriminatedValue.from_bool(True)
        # Testing __eq__ with raw boolean - cannot use `assert value` since value is not a bool
        assert value == True

    def test_equality_collections(self) -> None:
        """Test equality for collection types."""
        dict_val1 = ModelDiscriminatedValue.from_dict({"key": "value"})
        dict_val2 = ModelDiscriminatedValue.from_dict({"key": "value"})
        assert dict_val1 == dict_val2

        list_val1 = ModelDiscriminatedValue.from_list([1, 2, 3])
        list_val2 = ModelDiscriminatedValue.from_list([1, 2, 3])
        assert list_val1 == list_val2


@pytest.mark.unit
class TestModelDiscriminatedValueStringRepresentation:
    """Tests for ModelDiscriminatedValue string representation."""

    def test_str_representation(self) -> None:
        """Test string representation."""
        value = ModelDiscriminatedValue.from_int(42)
        str_repr = str(value)
        assert "DiscriminatedValue" in str_repr
        assert "42" in str_repr
        assert str(EnumDiscriminatedValueType.INT) in str_repr

    def test_repr_representation(self) -> None:
        """Test repr representation."""
        value = ModelDiscriminatedValue.from_str("test")
        repr_str = repr(value)
        assert "ModelDiscriminatedValue" in repr_str
        assert "test" in repr_str
        assert "value_type" in repr_str

    def test_str_all_types(self) -> None:
        """Test string representation for all types."""
        values = [
            ModelDiscriminatedValue.from_bool(True),
            ModelDiscriminatedValue.from_int(42),
            ModelDiscriminatedValue.from_float(3.14),
            ModelDiscriminatedValue.from_str("test"),
            ModelDiscriminatedValue.from_dict({"k": "v"}),
            ModelDiscriminatedValue.from_list([1, 2]),
        ]
        for value in values:
            str_repr = str(value)
            assert "DiscriminatedValue" in str_repr
            assert len(str_repr) > 0


@pytest.mark.unit
class TestModelDiscriminatedValueEdgeCases:
    """Tests for ModelDiscriminatedValue edge cases."""

    def test_large_integer(self) -> None:
        """Test with large integer value."""
        large_int = 999999999999999999
        value = ModelDiscriminatedValue.from_int(large_int)
        assert value.get_value() == large_int

    def test_scientific_notation_float(self) -> None:
        """Test with scientific notation float."""
        sci_float = 1.23e10
        value = ModelDiscriminatedValue.from_float(sci_float)
        assert value.get_value() == sci_float

    def test_unicode_string(self) -> None:
        """Test with unicode string."""
        unicode_str = "Hello 世界 🌍"
        value = ModelDiscriminatedValue.from_str(unicode_str)
        assert value.get_value() == unicode_str

    def test_multiline_string(self) -> None:
        """Test with multiline string."""
        multiline = "Line 1\nLine 2\nLine 3"
        value = ModelDiscriminatedValue.from_str(multiline)
        assert value.get_value() == multiline

    def test_deeply_nested_dict(self) -> None:
        """Test with deeply nested dictionary."""
        nested = {"a": {"b": {"c": {"d": "value"}}}}
        value = ModelDiscriminatedValue.from_dict(nested)
        assert value.get_value() == nested

    def test_deeply_nested_list(self) -> None:
        """Test with deeply nested list."""
        nested = [[[["value"]]]]
        value = ModelDiscriminatedValue.from_list(nested)
        assert value.get_value() == nested

    def test_dict_with_special_characters_in_keys(self) -> None:
        """Test dictionary with special characters in keys."""
        special_dict = {"key-with-dash": 1, "key.with.dot": 2, "key_with_underscore": 3}
        value = ModelDiscriminatedValue.from_dict(special_dict)
        assert value.get_value() == special_dict

    def test_list_with_none_values(self) -> None:
        """Test list containing None values."""
        list_with_none = [1, None, "three", None, 5]
        value = ModelDiscriminatedValue.from_list(list_with_none)
        assert value.get_value() == list_with_none


@pytest.mark.unit
class TestModelDiscriminatedValueSerialization:
    """Tests for ModelDiscriminatedValue serialization."""

    def test_model_dump(self) -> None:
        """Test model_dump serialization."""
        value = ModelDiscriminatedValue.from_int(42)
        data = value.model_dump()
        assert isinstance(data, dict)
        assert "value_type" in data
        assert "int_value" in data
        assert data["int_value"] == 42

    def test_model_dump_json(self) -> None:
        """Test model_dump_json serialization."""
        value = ModelDiscriminatedValue.from_str("test")
        json_str = value.model_dump_json()
        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["value_type"] == "str"
        assert data["str_value"] == "test"

    def test_round_trip_serialization(self) -> None:
        """Test round-trip serialization and deserialization."""
        original = ModelDiscriminatedValue.from_dict({"key": "value"})
        json_str = original.model_dump_json()
        data = json.loads(json_str)
        restored = ModelDiscriminatedValue(**data)
        assert restored == original


@pytest.mark.unit
class TestModelDiscriminatedValueUnsupportedTypes:
    """Tests for ModelDiscriminatedValue with unsupported types."""

    def test_from_any_unsupported_type(self) -> None:
        """Test from_any with unsupported type raises error."""

        class UnsupportedType:
            pass

        with pytest.raises(ModelOnexError) as exc_info:
            ModelDiscriminatedValue.from_any(UnsupportedType())  # type: ignore[arg-type]
        assert "Unsupported type" in str(exc_info.value)

    def test_from_any_none_raises_error(self) -> None:
        """Test from_any with None raises error (None not supported)."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDiscriminatedValue.from_any(None)  # type: ignore[arg-type]
        assert "Unsupported type" in str(exc_info.value)
