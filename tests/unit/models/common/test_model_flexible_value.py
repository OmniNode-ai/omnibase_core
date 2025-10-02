"""Tests for ModelFlexibleValue."""

from uuid import uuid4

import pytest

from omnibase_core.enums.enum_flexible_value_type import EnumFlexibleValueType
from omnibase_core.errors.error_codes import OnexError
from omnibase_core.models.common.model_flexible_value import ModelFlexibleValue
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class TestModelFlexibleValueInstantiation:
    """Tests for ModelFlexibleValue instantiation."""

    def test_create_from_string(self):
        """Test creating flexible value from string."""
        value = ModelFlexibleValue.from_string("test")
        assert value.value_type == EnumFlexibleValueType.STRING
        assert value.string_value == "test"
        assert value.is_validated is True

    def test_create_from_integer(self):
        """Test creating flexible value from integer."""
        value = ModelFlexibleValue.from_integer(42)
        assert value.value_type == EnumFlexibleValueType.INTEGER
        assert value.integer_value == 42

    def test_create_from_float(self):
        """Test creating flexible value from float."""
        value = ModelFlexibleValue.from_float(3.14)
        assert value.value_type == EnumFlexibleValueType.FLOAT
        assert value.float_value == 3.14

    def test_create_from_boolean(self):
        """Test creating flexible value from boolean."""
        value = ModelFlexibleValue.from_boolean(True)
        assert value.value_type == EnumFlexibleValueType.BOOLEAN
        assert value.boolean_value is True

    def test_create_from_uuid(self):
        """Test creating flexible value from UUID."""
        test_uuid = uuid4()
        value = ModelFlexibleValue.from_uuid(test_uuid)
        assert value.value_type == EnumFlexibleValueType.UUID
        assert value.uuid_value == test_uuid

    def test_create_from_none(self):
        """Test creating flexible value from None."""
        value = ModelFlexibleValue.from_none()
        assert value.value_type == EnumFlexibleValueType.NONE
        assert value.is_none() is True


class TestModelFlexibleValueCollections:
    """Tests for ModelFlexibleValue with collections."""

    def test_create_from_dict_value(self):
        """Test creating flexible value from dict with ModelSchemaValue."""
        dict_val = {
            "key1": ModelSchemaValue.from_value("value1"),
            "key2": ModelSchemaValue.from_value(42),
        }
        value = ModelFlexibleValue.from_dict_value(dict_val)
        assert value.value_type == EnumFlexibleValueType.DICT
        assert len(value.dict_value) == 2
        assert "key1" in value.dict_value
        assert "key2" in value.dict_value
        assert value.dict_value["key1"].to_value() == "value1"
        assert value.dict_value["key2"].to_value() == 42

    def test_create_from_raw_dict(self):
        """Test creating flexible value from raw dict."""
        raw_dict = {"key1": "value1", "key2": 42, "key3": True}
        value = ModelFlexibleValue.from_raw_dict(raw_dict)
        assert value.value_type == EnumFlexibleValueType.DICT
        assert len(value.dict_value) == 3
        assert set(value.dict_value.keys()) == {"key1", "key2", "key3"}
        assert all(isinstance(v, ModelSchemaValue) for v in value.dict_value.values())

    def test_create_from_list(self):
        """Test creating flexible value from list."""
        list_val = ["item1", 42, True, 3.14]
        value = ModelFlexibleValue.from_list(list_val)
        assert value.value_type == EnumFlexibleValueType.LIST
        assert len(value.list_value) == 4
        assert value.list_value[0].to_value() == "item1"
        assert value.list_value[1].to_value() == 42
        assert value.list_value[2].to_value() is True
        assert value.list_value[3].to_value() == 3.14

    def test_list_value_conversion(self):
        """Test that list values are converted to ModelSchemaValue."""
        list_val = [1, 2, 3]
        value = ModelFlexibleValue.from_list(list_val)
        assert all(isinstance(item, ModelSchemaValue) for item in value.list_value)


class TestModelFlexibleValueAutoDetection:
    """Tests for ModelFlexibleValue auto-detection."""

    def test_from_any_string(self):
        """Test from_any with string."""
        value = ModelFlexibleValue.from_any("test")
        assert value.value_type == EnumFlexibleValueType.STRING

    def test_from_any_integer(self):
        """Test from_any with integer."""
        value = ModelFlexibleValue.from_any(42)
        assert value.value_type == EnumFlexibleValueType.INTEGER

    def test_from_any_float(self):
        """Test from_any with float."""
        value = ModelFlexibleValue.from_any(3.14)
        assert value.value_type == EnumFlexibleValueType.FLOAT

    def test_from_any_boolean(self):
        """Test from_any with boolean (must be checked before int)."""
        value = ModelFlexibleValue.from_any(True)
        assert value.value_type == EnumFlexibleValueType.BOOLEAN

    def test_from_any_dict(self):
        """Test from_any with dict."""
        value = ModelFlexibleValue.from_any({"key": "value"})
        assert value.value_type == EnumFlexibleValueType.DICT

    def test_from_any_list(self):
        """Test from_any with list."""
        value = ModelFlexibleValue.from_any([1, 2, 3])
        assert value.value_type == EnumFlexibleValueType.LIST

    def test_from_any_uuid(self):
        """Test from_any with UUID."""
        test_uuid = uuid4()
        value = ModelFlexibleValue.from_any(test_uuid)
        assert value.value_type == EnumFlexibleValueType.UUID

    def test_from_any_none(self):
        """Test from_any with None."""
        value = ModelFlexibleValue.from_any(None)
        assert value.value_type == EnumFlexibleValueType.NONE


class TestModelFlexibleValueRetrieval:
    """Tests for retrieving values from ModelFlexibleValue."""

    def test_get_value_string(self):
        """Test get_value for string."""
        value = ModelFlexibleValue.from_string("test")
        assert value.get_value() == "test"

    def test_get_value_integer(self):
        """Test get_value for integer."""
        value = ModelFlexibleValue.from_integer(42)
        assert value.get_value() == 42

    def test_get_value_float(self):
        """Test get_value for float."""
        value = ModelFlexibleValue.from_float(3.14)
        assert value.get_value() == 3.14

    def test_get_value_boolean(self):
        """Test get_value for boolean."""
        value = ModelFlexibleValue.from_boolean(True)
        assert value.get_value() is True

    def test_get_value_none(self):
        """Test get_value for None."""
        value = ModelFlexibleValue.from_none()
        assert value.get_value() is None

    def test_get_python_type(self):
        """Test get_python_type for various types."""
        assert ModelFlexibleValue.from_string("test").get_python_type() == str
        assert ModelFlexibleValue.from_integer(42).get_python_type() == int
        assert ModelFlexibleValue.from_float(3.14).get_python_type() == float
        assert ModelFlexibleValue.from_boolean(True).get_python_type() == bool
        assert ModelFlexibleValue.from_none().get_python_type() == type(None)


class TestModelFlexibleValueValidation:
    """Tests for ModelFlexibleValue validation."""

    def test_validation_single_value(self):
        """Test that only one value can be set."""
        # Valid: only string_value is set
        value = ModelFlexibleValue(
            value_type=EnumFlexibleValueType.STRING, string_value="test"
        )
        assert value.string_value == "test"

    def test_validation_none_type_with_values(self):
        """Test that NONE type cannot have values."""
        with pytest.raises(OnexError) as exc_info:
            ModelFlexibleValue(
                value_type=EnumFlexibleValueType.NONE, string_value="test"
            )
        assert "No values should be set" in str(exc_info.value)

    def test_validation_missing_required_value(self):
        """Test that required value must be set for type."""
        with pytest.raises(OnexError) as exc_info:
            ModelFlexibleValue(value_type=EnumFlexibleValueType.STRING)
        assert "must be set" in str(exc_info.value)

    def test_validation_wrong_value_type(self):
        """Test that wrong value for type raises error."""
        with pytest.raises(OnexError) as exc_info:
            ModelFlexibleValue(
                value_type=EnumFlexibleValueType.STRING, integer_value=42
            )
        assert "Required value for type" in str(exc_info.value) or "must be set" in str(
            exc_info.value
        )


class TestModelFlexibleValueComparison:
    """Tests for ModelFlexibleValue comparison."""

    def test_compare_value_same_type(self):
        """Test comparing values of same type."""
        value1 = ModelFlexibleValue.from_string("test")
        value2 = ModelFlexibleValue.from_string("test")
        assert value1.compare_value(value2) is True

    def test_compare_value_different_values(self):
        """Test comparing different values."""
        value1 = ModelFlexibleValue.from_string("test1")
        value2 = ModelFlexibleValue.from_string("test2")
        assert value1.compare_value(value2) is False

    def test_compare_value_with_raw_value(self):
        """Test comparing with raw value."""
        value = ModelFlexibleValue.from_integer(42)
        assert value.compare_value(42) is True

    def test_equality_operator(self):
        """Test equality operator."""
        value1 = ModelFlexibleValue.from_integer(42)
        value2 = ModelFlexibleValue.from_integer(42)
        assert value1 == value2

    def test_equality_with_raw_value(self):
        """Test equality with raw value."""
        value = ModelFlexibleValue.from_string("test")
        assert value == "test"


class TestModelFlexibleValueTypeChecks:
    """Tests for ModelFlexibleValue type checking methods."""

    def test_is_none(self):
        """Test is_none method."""
        assert ModelFlexibleValue.from_none().is_none() is True
        assert ModelFlexibleValue.from_string("test").is_none() is False

    def test_is_primitive(self):
        """Test is_primitive method."""
        assert ModelFlexibleValue.from_string("test").is_primitive() is True
        assert ModelFlexibleValue.from_integer(42).is_primitive() is True
        assert ModelFlexibleValue.from_float(3.14).is_primitive() is True
        assert ModelFlexibleValue.from_boolean(True).is_primitive() is True
        assert ModelFlexibleValue.from_list([1, 2]).is_primitive() is False

    def test_is_collection(self):
        """Test is_collection method."""
        assert ModelFlexibleValue.from_list([1, 2]).is_collection() is True
        assert ModelFlexibleValue.from_raw_dict({"k": "v"}).is_collection() is True
        assert ModelFlexibleValue.from_string("test").is_collection() is False


class TestModelFlexibleValueConversion:
    """Tests for ModelFlexibleValue conversion methods."""

    def test_to_schema_value(self):
        """Test to_schema_value conversion."""
        value = ModelFlexibleValue.from_string("test")
        schema_value = value.to_schema_value()
        assert isinstance(schema_value, ModelSchemaValue)
        assert schema_value.to_value() == "test"


class TestModelFlexibleValueStringRepresentation:
    """Tests for ModelFlexibleValue string representation."""

    def test_str_representation(self):
        """Test string representation."""
        value = ModelFlexibleValue.from_string("test")
        str_repr = str(value)
        assert "FlexibleValue" in str_repr
        assert "test" in str_repr

    def test_repr_representation(self):
        """Test repr representation."""
        value = ModelFlexibleValue.from_integer(42, source="test_source")
        repr_str = repr(value)
        assert "ModelFlexibleValue" in repr_str
        assert "42" in repr_str
        assert "test_source" in repr_str


class TestModelFlexibleValueSerialization:
    """Tests for ModelFlexibleValue serialization."""

    def test_serialize(self):
        """Test serialize method."""
        value = ModelFlexibleValue.from_string("test")
        data = value.serialize()
        assert isinstance(data, dict)
        assert "value_type" in data

    def test_validate_instance(self):
        """Test validate_instance method."""
        value = ModelFlexibleValue.from_integer(42)
        assert value.validate_instance() is True


class TestModelFlexibleValueEdgeCases:
    """Tests for ModelFlexibleValue edge cases."""

    def test_empty_string(self):
        """Test flexible value with empty string."""
        value = ModelFlexibleValue.from_string("")
        assert value.get_value() == ""

    def test_zero_integer(self):
        """Test flexible value with zero integer."""
        value = ModelFlexibleValue.from_integer(0)
        assert value.get_value() == 0

    def test_negative_integer(self):
        """Test flexible value with negative integer."""
        value = ModelFlexibleValue.from_integer(-42)
        assert value.get_value() == -42

    def test_empty_list(self):
        """Test flexible value with empty list."""
        value = ModelFlexibleValue.from_list([])
        assert len(value.list_value) == 0

    def test_empty_dict(self):
        """Test flexible value with empty dict."""
        value = ModelFlexibleValue.from_raw_dict({})
        assert len(value.dict_value) == 0

    def test_source_field(self):
        """Test source field is preserved."""
        value = ModelFlexibleValue.from_string("test", source="unit_test")
        assert value.source == "unit_test"

    def test_nested_collections(self):
        """Test nested collections."""
        nested_list = [[1, 2], [3, 4]]
        value = ModelFlexibleValue.from_list(nested_list)
        assert value.value_type == EnumFlexibleValueType.LIST
        retrieved_list = value.get_value()
        assert len(retrieved_list) == 2
        assert isinstance(retrieved_list[0], list)
        assert isinstance(retrieved_list[1], list)
        assert retrieved_list[0] == [1, 2]
        assert retrieved_list[1] == [3, 4]
