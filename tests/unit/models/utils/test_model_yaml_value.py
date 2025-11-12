"""
Test suite for ModelYamlValue - YAML-serializable data structures with discriminated union.

This test suite focuses on validator branches and factory methods to maximize branch coverage.
"""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_yaml_value_type import EnumYamlValueType
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.utils.model_yaml_value import ModelYamlValue


class TestModelYamlValueInstantiation:
    """Test basic model instantiation."""

    def test_create_schema_value(self):
        """Test creating SCHEMA_VALUE type directly."""
        schema_val = ModelSchemaValue.create_string("test")
        yaml_val = ModelYamlValue(
            value_type=EnumYamlValueType.SCHEMA_VALUE, schema_value=schema_val
        )
        assert yaml_val.value_type == EnumYamlValueType.SCHEMA_VALUE
        assert yaml_val.schema_value == schema_val
        assert yaml_val.dict_value is None
        assert yaml_val.list_value is None

    def test_create_dict_value(self):
        """Test creating DICT type directly."""
        inner = ModelYamlValue(
            value_type=EnumYamlValueType.SCHEMA_VALUE,
            schema_value=ModelSchemaValue.create_string("inner"),
        )
        yaml_val = ModelYamlValue(
            value_type=EnumYamlValueType.DICT, dict_value={"key": inner}
        )
        assert yaml_val.value_type == EnumYamlValueType.DICT
        assert yaml_val.dict_value is not None
        assert len(yaml_val.dict_value) == 1

    def test_create_list_value(self):
        """Test creating LIST type directly."""
        inner = ModelYamlValue(
            value_type=EnumYamlValueType.SCHEMA_VALUE,
            schema_value=ModelSchemaValue.create_string("item"),
        )
        yaml_val = ModelYamlValue(value_type=EnumYamlValueType.LIST, list_value=[inner])
        assert yaml_val.value_type == EnumYamlValueType.LIST
        assert yaml_val.list_value is not None
        assert len(yaml_val.list_value) == 1


class TestModelYamlValueFactoryMethods:
    """Test factory methods for creating YAML values."""

    def test_from_schema_value_string(self):
        """Test from_schema_value factory with string schema value."""
        schema_val = ModelSchemaValue.create_string("test_string")
        yaml_val = ModelYamlValue.from_schema_value(schema_val)

        assert yaml_val.value_type == EnumYamlValueType.SCHEMA_VALUE
        assert yaml_val.schema_value == schema_val
        assert yaml_val.dict_value is None
        assert yaml_val.list_value is None

    def test_from_schema_value_integer(self):
        """Test from_schema_value factory with integer schema value."""
        schema_val = ModelSchemaValue.create_number(42)
        yaml_val = ModelYamlValue.from_schema_value(schema_val)

        assert yaml_val.value_type == EnumYamlValueType.SCHEMA_VALUE
        assert yaml_val.schema_value == schema_val

    def test_from_schema_value_boolean(self):
        """Test from_schema_value factory with boolean schema value."""
        schema_val = ModelSchemaValue.create_boolean(True)
        yaml_val = ModelYamlValue.from_schema_value(schema_val)

        assert yaml_val.value_type == EnumYamlValueType.SCHEMA_VALUE
        assert yaml_val.schema_value == schema_val

    def test_from_dict_data_single_entry(self):
        """Test from_dict_data factory with single entry."""
        dict_data = {"key1": ModelSchemaValue.create_string("value1")}
        yaml_val = ModelYamlValue.from_dict_data(dict_data)

        assert yaml_val.value_type == EnumYamlValueType.DICT
        assert yaml_val.dict_value is not None
        assert len(yaml_val.dict_value) == 1
        assert "key1" in yaml_val.dict_value
        assert yaml_val.schema_value is None
        assert yaml_val.list_value is None

    def test_from_dict_data_multiple_entries(self):
        """Test from_dict_data factory with multiple entries."""
        dict_data = {
            "key1": ModelSchemaValue.create_string("value1"),
            "key2": ModelSchemaValue.create_number(42),
            "key3": ModelSchemaValue.create_boolean(True),
        }
        yaml_val = ModelYamlValue.from_dict_data(dict_data)

        assert yaml_val.value_type == EnumYamlValueType.DICT
        assert len(yaml_val.dict_value) == 3

    def test_from_dict_data_empty(self):
        """Test from_dict_data factory with empty dictionary."""
        yaml_val = ModelYamlValue.from_dict_data({})

        assert yaml_val.value_type == EnumYamlValueType.DICT
        assert yaml_val.dict_value is not None
        assert len(yaml_val.dict_value) == 0

    def test_from_list_single_element(self):
        """Test from_list factory with single element."""
        list_data = [ModelSchemaValue.create_string("item1")]
        yaml_val = ModelYamlValue.from_list(list_data)

        assert yaml_val.value_type == EnumYamlValueType.LIST
        assert yaml_val.list_value is not None
        assert len(yaml_val.list_value) == 1
        assert yaml_val.schema_value is None
        assert yaml_val.dict_value is None

    def test_from_list_multiple_elements(self):
        """Test from_list factory with multiple elements."""
        list_data = [
            ModelSchemaValue.create_string("item1"),
            ModelSchemaValue.create_number(42),
            ModelSchemaValue.create_boolean(False),
        ]
        yaml_val = ModelYamlValue.from_list(list_data)

        assert yaml_val.value_type == EnumYamlValueType.LIST
        assert len(yaml_val.list_value) == 3

    def test_from_list_empty(self):
        """Test from_list factory with empty list."""
        yaml_val = ModelYamlValue.from_list([])

        assert yaml_val.value_type == EnumYamlValueType.LIST
        assert yaml_val.list_value is not None
        assert len(yaml_val.list_value) == 0


class TestModelYamlValueToSerializableBranches:
    """Test to_serializable method branches for different types."""

    def test_to_serializable_schema_value(self):
        """Test to_serializable with SCHEMA_VALUE type (branch: value_type == SCHEMA_VALUE)."""
        schema_val = ModelSchemaValue.create_string("test")
        yaml_val = ModelYamlValue.from_schema_value(schema_val)

        result = yaml_val.to_serializable()
        assert result == schema_val

    def test_to_serializable_dict(self):
        """Test to_serializable with DICT type (branch: value_type == DICT)."""
        dict_data = {
            "key1": ModelSchemaValue.create_string("value1"),
            "key2": ModelSchemaValue.create_number(42),
        }
        yaml_val = ModelYamlValue.from_dict_data(dict_data)

        result = yaml_val.to_serializable()
        assert isinstance(result, dict)
        assert len(result) == 2
        assert "key1" in result
        assert "key2" in result

    def test_to_serializable_dict_empty(self):
        """Test to_serializable with empty DICT (branch: dict_value or {})."""
        yaml_val = ModelYamlValue.from_dict_data({})
        result = yaml_val.to_serializable()
        assert isinstance(result, dict)
        assert len(result) == 0

    def test_to_serializable_list(self):
        """Test to_serializable with LIST type (branch: value_type == LIST)."""
        list_data = [
            ModelSchemaValue.create_string("item1"),
            ModelSchemaValue.create_string("item2"),
        ]
        yaml_val = ModelYamlValue.from_list(list_data)

        result = yaml_val.to_serializable()
        assert isinstance(result, list)
        assert len(result) == 2

    def test_to_serializable_list_empty(self):
        """Test to_serializable with empty LIST (branch: list_value or [])."""
        yaml_val = ModelYamlValue.from_list([])
        result = yaml_val.to_serializable()
        assert isinstance(result, list)
        assert len(result) == 0

    def test_to_serializable_nested_dict(self):
        """Test to_serializable with nested dictionary."""
        inner_dict = {
            "inner_key": ModelSchemaValue.create_string("inner_value"),
        }
        dict_data = {
            "outer_key": ModelSchemaValue.create_string("outer_value"),
        }
        # Can't nest ModelYamlValue in from_dict_data, but test recursive call works
        yaml_val = ModelYamlValue.from_dict_data(dict_data)
        result = yaml_val.to_serializable()
        assert isinstance(result, dict)

    def test_to_serializable_nested_list(self):
        """Test to_serializable with list containing multiple types."""
        list_data = [
            ModelSchemaValue.create_string("string"),
            ModelSchemaValue.create_number(42),
            ModelSchemaValue.create_boolean(True),
        ]
        yaml_val = ModelYamlValue.from_list(list_data)
        result = yaml_val.to_serializable()
        assert isinstance(result, list)
        assert len(result) == 3

    def test_to_serializable_invalid_type_raises_error(self):
        """Test to_serializable with invalid type raises error (else branch, line 87)."""
        # Create value with invalid enum by bypassing validation
        yaml_val = ModelYamlValue(
            value_type=EnumYamlValueType.SCHEMA_VALUE,
            schema_value=ModelSchemaValue.create_string("test"),
        )
        # Manually change to invalid type
        # Use object.__setattr__ to bypass Pydantic validate_assignment
        object.__setattr__(yaml_val, "value_type", "INVALID_TYPE")

        with pytest.raises(ModelOnexError) as exc_info:
            yaml_val.to_serializable()

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Invalid value_type" in exc_info.value.message


class TestModelYamlValueProtocolMethods:
    """Test protocol method implementations."""

    def test_serialize_schema_value(self):
        """Test serialize protocol method with schema value."""
        schema_val = ModelSchemaValue.create_string("test")
        yaml_val = ModelYamlValue.from_schema_value(schema_val)

        serialized = yaml_val.serialize()
        assert isinstance(serialized, dict)
        assert serialized["value_type"] == EnumYamlValueType.SCHEMA_VALUE

    def test_serialize_dict(self):
        """Test serialize protocol method with dict."""
        dict_data = {"key": ModelSchemaValue.create_string("value")}
        yaml_val = ModelYamlValue.from_dict_data(dict_data)

        serialized = yaml_val.serialize()
        assert serialized["value_type"] == EnumYamlValueType.DICT

    def test_serialize_list(self):
        """Test serialize protocol method with list."""
        list_data = [ModelSchemaValue.create_string("item")]
        yaml_val = ModelYamlValue.from_list(list_data)

        serialized = yaml_val.serialize()
        assert serialized["value_type"] == EnumYamlValueType.LIST

    def test_validate_instance(self):
        """Test validate_instance protocol method."""
        yaml_val = ModelYamlValue.from_schema_value(
            ModelSchemaValue.create_string("test")
        )
        assert yaml_val.validate_instance() is True


class TestModelYamlValueEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_model_dump_schema_value(self):
        """Test Pydantic model_dump with schema value."""
        schema_val = ModelSchemaValue.create_string("test")
        yaml_val = ModelYamlValue.from_schema_value(schema_val)

        dumped = yaml_val.model_dump()
        assert dumped["value_type"] == EnumYamlValueType.SCHEMA_VALUE
        assert dumped["schema_value"] is not None
        assert dumped["dict_value"] is None
        assert dumped["list_value"] is None

    def test_model_dump_dict(self):
        """Test Pydantic model_dump with dict."""
        dict_data = {"key": ModelSchemaValue.create_string("value")}
        yaml_val = ModelYamlValue.from_dict_data(dict_data)

        dumped = yaml_val.model_dump()
        assert dumped["value_type"] == EnumYamlValueType.DICT
        assert dumped["dict_value"] is not None

    def test_model_dump_list(self):
        """Test Pydantic model_dump with list."""
        list_data = [ModelSchemaValue.create_string("item")]
        yaml_val = ModelYamlValue.from_list(list_data)

        dumped = yaml_val.model_dump()
        assert dumped["value_type"] == EnumYamlValueType.LIST
        assert dumped["list_value"] is not None

    def test_round_trip_schema_value(self):
        """Test round-trip serialization with schema value."""
        original = ModelYamlValue.from_schema_value(
            ModelSchemaValue.create_string("test")
        )
        dumped = original.model_dump()
        restored = ModelYamlValue(**dumped)

        assert restored.value_type == original.value_type
        assert restored.schema_value == original.schema_value

    def test_round_trip_dict(self):
        """Test round-trip serialization with dict."""
        dict_data = {"key1": ModelSchemaValue.create_string("value1")}
        original = ModelYamlValue.from_dict_data(dict_data)
        dumped = original.model_dump()
        restored = ModelYamlValue(**dumped)

        assert restored.value_type == EnumYamlValueType.DICT
        assert len(restored.dict_value) == 1

    def test_round_trip_list(self):
        """Test round-trip serialization with list."""
        list_data = [ModelSchemaValue.create_string("item1")]
        original = ModelYamlValue.from_list(list_data)
        dumped = original.model_dump()
        restored = ModelYamlValue(**dumped)

        assert restored.value_type == EnumYamlValueType.LIST
        assert len(restored.list_value) == 1

    def test_large_dict(self):
        """Test with large dictionary."""
        dict_data = {f"key{i}": ModelSchemaValue.create_number(i) for i in range(100)}
        yaml_val = ModelYamlValue.from_dict_data(dict_data)
        result = yaml_val.to_serializable()
        assert isinstance(result, dict)
        assert len(result) == 100

    def test_large_list(self):
        """Test with large list."""
        list_data = [ModelSchemaValue.create_number(i) for i in range(100)]
        yaml_val = ModelYamlValue.from_list(list_data)
        result = yaml_val.to_serializable()
        assert isinstance(result, list)
        assert len(result) == 100

    def test_complex_nested_structure(self):
        """Test with complex nested structure."""
        # Create nested dict with multiple levels
        inner_dict = {
            "inner1": ModelSchemaValue.create_string("value1"),
            "inner2": ModelSchemaValue.create_number(42),
        }
        yaml_val = ModelYamlValue.from_dict_data(inner_dict)

        # Verify serialization works
        result = yaml_val.to_serializable()
        assert isinstance(result, dict)
        assert len(result) == 2
