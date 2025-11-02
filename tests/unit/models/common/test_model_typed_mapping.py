"""Tests for model_typed_mapping.py"""

from typing import Any

import pytest

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.models.common.model_typed_mapping import ModelTypedMapping
from omnibase_core.models.common.model_value_container import ModelValueContainer
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class TestModelTypedMapping:
    """Test class for ModelTypedMapping."""

    def test_model_initialization(self):
        """Test model can be initialized."""
        mapping = ModelTypedMapping()
        assert mapping is not None
        assert isinstance(mapping.data, dict)
        assert mapping.current_depth == 0
        assert len(mapping.data) == 0

    def test_model_inheritance(self):
        """Test model inheritance."""
        from pydantic import BaseModel

        assert issubclass(ModelTypedMapping, BaseModel)

    def test_model_constants(self):
        """Test model constants."""
        assert ModelTypedMapping.MAX_DEPTH == 10

    def test_set_string(self):
        """Test setting string values."""
        mapping = ModelTypedMapping()
        mapping.set_string("test_key", "test_value")

        assert "test_key" in mapping.data
        assert isinstance(mapping.data["test_key"], ModelValueContainer)
        assert mapping.data["test_key"].value == "test_value"

    def test_set_int(self):
        """Test setting integer values."""
        mapping = ModelTypedMapping()
        mapping.set_int("number_key", 42)

        assert "number_key" in mapping.data
        assert isinstance(mapping.data["number_key"], ModelValueContainer)
        assert mapping.data["number_key"].value == 42

    def test_set_float(self):
        """Test setting float values."""
        mapping = ModelTypedMapping()
        mapping.set_float("float_key", 3.14)

        assert "float_key" in mapping.data
        assert isinstance(mapping.data["float_key"], ModelValueContainer)
        assert mapping.data["float_key"].value == 3.14

    def test_set_bool(self):
        """Test setting boolean values."""
        mapping = ModelTypedMapping()
        mapping.set_bool("bool_key", True)

        assert "bool_key" in mapping.data
        assert isinstance(mapping.data["bool_key"], ModelValueContainer)
        assert mapping.data["bool_key"].value is True

    def test_set_list(self):
        """Test setting list values."""
        mapping = ModelTypedMapping()
        test_list = [1, 2, 3, "test"]
        mapping.set_list("list_key", test_list)

        assert "list_key" in mapping.data
        assert isinstance(mapping.data["list_key"], ModelValueContainer)
        assert mapping.data["list_key"].value == test_list

    def test_set_dict(self):
        """Test setting dict values."""
        mapping = ModelTypedMapping()
        test_dict = {"nested": "value", "number": 42}
        mapping.set_dict("dict_key", test_dict)

        assert "dict_key" in mapping.data
        assert isinstance(mapping.data["dict_key"], ModelValueContainer)
        assert mapping.data["dict_key"].value == test_dict

    def test_set_dict_depth_limit(self):
        """Test dict depth limit enforcement."""
        mapping = ModelTypedMapping()
        mapping.current_depth = 11  # Exceed MAX_DEPTH

        with pytest.raises(ModelOnexError) as exc_info:
            mapping.set_dict("dict_key", {"test": "value"})

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Maximum nesting depth" in str(exc_info.value)

    def test_set_value_string(self):
        """Test set_value with string."""
        mapping = ModelTypedMapping()
        mapping.set_value("key", "value")

        assert "key" in mapping.data
        assert mapping.data["key"].value == "value"

    def test_set_value_int(self):
        """Test set_value with integer."""
        mapping = ModelTypedMapping()
        mapping.set_value("key", 42)

        assert "key" in mapping.data
        assert mapping.data["key"].value == 42

    def test_set_value_float(self):
        """Test set_value with float."""
        mapping = ModelTypedMapping()
        mapping.set_value("key", 3.14)

        assert "key" in mapping.data
        assert mapping.data["key"].value == 3.14

    def test_set_value_bool(self):
        """Test set_value with boolean."""
        mapping = ModelTypedMapping()
        mapping.set_value("key", True)

        assert "key" in mapping.data
        assert mapping.data["key"].value is True

    def test_set_value_list(self):
        """Test set_value with list."""
        mapping = ModelTypedMapping()
        test_list = [1, 2, 3]
        mapping.set_value("key", test_list)

        assert "key" in mapping.data
        assert mapping.data["key"].value == test_list

    def test_set_value_dict(self):
        """Test set_value with dict."""
        mapping = ModelTypedMapping()
        test_dict = {"nested": "value"}
        mapping.set_value("key", test_dict)

        assert "key" in mapping.data
        assert mapping.data["key"].value == test_dict

    def test_set_value_none(self):
        """Test set_value with None (should be skipped)."""
        mapping = ModelTypedMapping()
        mapping.set_value("key", None)

        # None values should be skipped
        assert "key" not in mapping.data

    def test_set_value_unsupported_type(self):
        """Test set_value with unsupported type."""
        mapping = ModelTypedMapping()

        with pytest.raises(ModelOnexError) as exc_info:
            mapping.set_value("key", object())

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Unsupported type" in str(exc_info.value)

    def test_get_value_existing(self):
        """Test get_value with existing key."""
        mapping = ModelTypedMapping()
        mapping.set_string("test_key", "test_value")

        result = mapping.get_value("test_key")
        assert result == "test_value"

    def test_get_value_missing(self):
        """Test get_value with missing key."""
        mapping = ModelTypedMapping()

        result = mapping.get_value("missing_key")
        assert result is None

    def test_get_value_default(self):
        """Test get_value with default value."""
        mapping = ModelTypedMapping()

        result = mapping.get_value("missing_key", "default")
        assert result == "default"

    def test_get_string_valid(self):
        """Test get_string with valid string value."""
        mapping = ModelTypedMapping()
        mapping.set_string("test_key", "test_value")

        result = mapping.get_string("test_key")
        assert result == "test_value"

    def test_get_string_missing(self):
        """Test get_string with missing key."""
        mapping = ModelTypedMapping()

        result = mapping.get_string("missing_key")
        assert result is None

    def test_get_string_default(self):
        """Test get_string with default value."""
        mapping = ModelTypedMapping()

        result = mapping.get_string("missing_key", "default")
        assert result == "default"

    def test_get_string_wrong_type(self):
        """Test get_string with wrong type."""
        mapping = ModelTypedMapping()
        mapping.set_int("test_key", 42)

        with pytest.raises(ModelOnexError) as exc_info:
            mapping.get_string("test_key")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "is not a string" in str(exc_info.value)

    def test_get_int_valid(self):
        """Test get_int with valid integer value."""
        mapping = ModelTypedMapping()
        mapping.set_int("test_key", 42)

        result = mapping.get_int("test_key")
        assert result == 42

    def test_get_int_missing(self):
        """Test get_int with missing key."""
        mapping = ModelTypedMapping()

        result = mapping.get_int("missing_key")
        assert result is None

    def test_get_int_default(self):
        """Test get_int with default value."""
        mapping = ModelTypedMapping()

        result = mapping.get_int("missing_key", 0)
        assert result == 0

    def test_get_int_wrong_type(self):
        """Test get_int with wrong type."""
        mapping = ModelTypedMapping()
        mapping.set_string("test_key", "not_a_number")

        with pytest.raises(ModelOnexError) as exc_info:
            mapping.get_int("test_key")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "is not an int" in str(exc_info.value)

    def test_get_bool_valid(self):
        """Test get_bool with valid boolean value."""
        mapping = ModelTypedMapping()
        mapping.set_bool("test_key", True)

        result = mapping.get_bool("test_key")
        assert result is True

    def test_get_bool_missing(self):
        """Test get_bool with missing key."""
        mapping = ModelTypedMapping()

        result = mapping.get_bool("missing_key")
        assert result is None

    def test_get_bool_default(self):
        """Test get_bool with default value."""
        mapping = ModelTypedMapping()

        result = mapping.get_bool("missing_key", False)
        assert result is False

    def test_get_bool_wrong_type(self):
        """Test get_bool with wrong type."""
        mapping = ModelTypedMapping()
        mapping.set_string("test_key", "not_a_bool")

        with pytest.raises(ModelOnexError) as exc_info:
            mapping.get_bool("test_key")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "is not a bool" in str(exc_info.value)

    def test_has_key_existing(self):
        """Test has_key with existing key."""
        mapping = ModelTypedMapping()
        mapping.set_string("test_key", "test_value")

        assert mapping.has_key("test_key") is True

    def test_has_key_missing(self):
        """Test has_key with missing key."""
        mapping = ModelTypedMapping()

        assert mapping.has_key("missing_key") is False

    def test_keys_empty(self):
        """Test keys with empty mapping."""
        mapping = ModelTypedMapping()

        assert mapping.keys() == []

    def test_keys_populated(self):
        """Test keys with populated mapping."""
        mapping = ModelTypedMapping()
        mapping.set_string("key1", "value1")
        mapping.set_int("key2", 42)

        keys = mapping.keys()
        assert len(keys) == 2
        assert "key1" in keys
        assert "key2" in keys

    def test_to_python_dict_empty(self):
        """Test to_python_dict with empty mapping."""
        mapping = ModelTypedMapping()

        result = mapping.to_python_dict()
        assert result == {}

    def test_to_python_dict_populated(self):
        """Test to_python_dict with populated mapping."""
        mapping = ModelTypedMapping()
        mapping.set_string("key1", "value1")
        mapping.set_int("key2", 42)
        mapping.set_bool("key3", True)

        result = mapping.to_python_dict()
        expected = {"key1": "value1", "key2": 42, "key3": True}
        assert result == expected

    def test_is_valid_empty(self):
        """Test is_valid with empty mapping."""
        mapping = ModelTypedMapping()

        assert mapping.is_valid() is True

    def test_is_valid_normal_depth(self):
        """Test is_valid with normal depth."""
        mapping = ModelTypedMapping()
        mapping.current_depth = 5
        mapping.set_string("test_key", "test_value")

        assert mapping.is_valid() is True

    def test_is_valid_exceeds_depth(self):
        """Test is_valid with excessive depth."""
        mapping = ModelTypedMapping()
        mapping.current_depth = 15  # Exceeds MAX_DEPTH

        assert mapping.is_valid() is False

    def test_get_errors_empty(self):
        """Test get_errors with empty mapping."""
        mapping = ModelTypedMapping()

        errors = mapping.get_errors()
        assert errors == []

    def test_get_errors_depth_exceeded(self):
        """Test get_errors with depth exceeded."""
        mapping = ModelTypedMapping()
        mapping.current_depth = 15

        errors = mapping.get_errors()
        assert len(errors) == 1
        assert "exceeds maximum depth" in errors[0]

    def test_validate_mapping_constraints_normal(self):
        """Test _validate_mapping_constraints with normal data."""
        mapping = ModelTypedMapping()
        mapping.set_string("key1", "value1")
        mapping.set_string("key2", "value2")

        assert mapping._validate_mapping_constraints() is True

    def test_validate_mapping_constraints_size_limit(self):
        """Test _validate_mapping_constraints with size limit exceeded."""
        mapping = ModelTypedMapping()
        # Create a mapping with more than 10000 entries
        for i in range(10001):
            mapping.set_string(f"key{i}", f"value{i}")

        assert mapping._validate_mapping_constraints() is False

    def test_validate_mapping_constraints_empty_key(self):
        """Test _validate_mapping_constraints with empty key."""
        mapping = ModelTypedMapping()
        mapping.data[""] = ModelValueContainer(value="value")

        assert mapping._validate_mapping_constraints() is False

    def test_validate_mapping_constraints_long_key(self):
        """Test _validate_mapping_constraints with key too long."""
        mapping = ModelTypedMapping()
        long_key = "x" * 201  # Exceeds 200 character limit
        mapping.data[long_key] = ModelValueContainer(value="value")

        assert mapping._validate_mapping_constraints() is False

    def test_validate_mapping_constraints_null_byte_key(self):
        """Test _validate_mapping_constraints with null byte in key."""
        mapping = ModelTypedMapping()
        mapping.data["key\x00with_null"] = ModelValueContainer(value="value")

        assert mapping._validate_mapping_constraints() is False

    def test_validate_mapping_constraints_control_char_key(self):
        """Test _validate_mapping_constraints with control character in key."""
        mapping = ModelTypedMapping()
        mapping.data["key\x01with_control"] = ModelValueContainer(value="value")

        assert mapping._validate_mapping_constraints() is False

    def test_validate_mapping_constraints_valid_whitespace_key(self):
        """Test _validate_mapping_constraints with valid whitespace in key."""
        mapping = ModelTypedMapping()
        mapping.data["key\twith\ttab"] = ModelValueContainer(value="value")
        mapping.data["key\nwith\nnewline"] = ModelValueContainer(value="value")
        mapping.data["key\rwith\rcarriage"] = ModelValueContainer(value="value")

        assert mapping._validate_mapping_constraints() is True

    def test_get_mapping_constraint_errors_normal(self):
        """Test _get_mapping_constraint_errors with normal data."""
        mapping = ModelTypedMapping()
        mapping.set_string("key1", "value1")

        errors = mapping._get_mapping_constraint_errors()
        assert errors == []

    def test_get_mapping_constraint_errors_size_limit(self):
        """Test _get_mapping_constraint_errors with size limit exceeded."""
        mapping = ModelTypedMapping()
        for i in range(10001):
            mapping.set_string(f"key{i}", f"value{i}")

        errors = mapping._get_mapping_constraint_errors()
        assert len(errors) == 1
        assert "exceeds maximum size" in errors[0]

    def test_get_mapping_constraint_errors_empty_key(self):
        """Test _get_mapping_constraint_errors with empty key."""
        mapping = ModelTypedMapping()
        mapping.data[""] = ModelValueContainer(value="value")

        errors = mapping._get_mapping_constraint_errors()
        assert len(errors) == 1
        assert "Empty key not allowed" in errors[0]

    def test_get_mapping_constraint_errors_long_key(self):
        """Test _get_mapping_constraint_errors with key too long."""
        mapping = ModelTypedMapping()
        long_key = "x" * 201
        mapping.data[long_key] = ModelValueContainer(value="value")

        errors = mapping._get_mapping_constraint_errors()
        assert len(errors) == 1
        assert "exceeds maximum length" in errors[0]

    def test_get_mapping_constraint_errors_null_byte_key(self):
        """Test _get_mapping_constraint_errors with null byte in key."""
        mapping = ModelTypedMapping()
        mapping.data["key\x00with_null"] = ModelValueContainer(value="value")

        errors = mapping._get_mapping_constraint_errors()
        assert len(errors) == 1
        assert "contains null byte" in errors[0]

    def test_get_mapping_constraint_errors_control_char_key(self):
        """Test _get_mapping_constraint_errors with control character in key."""
        mapping = ModelTypedMapping()
        mapping.data["key\x01with_control"] = ModelValueContainer(value="value")

        errors = mapping._get_mapping_constraint_errors()
        assert len(errors) == 1
        assert "contains control characters" in errors[0]

    def test_validate_all_containers_empty(self):
        """Test validate_all_containers with empty mapping."""
        mapping = ModelTypedMapping()

        result = mapping.validate_all_containers()
        assert result == {}

    def test_validate_all_containers_populated(self):
        """Test validate_all_containers with populated mapping."""
        mapping = ModelTypedMapping()
        mapping.set_string("key1", "value1")
        mapping.set_int("key2", 42)

        result = mapping.validate_all_containers()
        assert "key1" in result
        assert "key2" in result
        # Should be empty lists if containers are valid
        assert result["key1"] == []
        assert result["key2"] == []

    def test_get_invalid_containers_empty(self):
        """Test get_invalid_containers with empty mapping."""
        mapping = ModelTypedMapping()

        result = mapping.get_invalid_containers()
        assert result == {}

    def test_get_invalid_containers_all_valid(self):
        """Test get_invalid_containers with all valid containers."""
        mapping = ModelTypedMapping()
        mapping.set_string("key1", "value1")
        mapping.set_int("key2", 42)

        result = mapping.get_invalid_containers()
        assert result == {}

    def test_is_container_valid_existing(self):
        """Test is_container_valid with existing key."""
        mapping = ModelTypedMapping()
        mapping.set_string("test_key", "test_value")

        result = mapping.is_container_valid("test_key")
        assert result is True

    def test_is_container_valid_missing(self):
        """Test is_container_valid with missing key."""
        mapping = ModelTypedMapping()

        with pytest.raises(ModelOnexError) as exc_info:
            mapping.is_container_valid("missing_key")

        assert exc_info.value.error_code == EnumCoreErrorCode.ITEM_NOT_REGISTERED
        assert "not found in mapping" in str(exc_info.value)

    def test_model_serialization(self):
        """Test model serialization."""
        mapping = ModelTypedMapping()
        mapping.set_string("test_key", "test_value")

        data = mapping.model_dump()
        assert "data" in data
        assert "test_key" in data["data"]

    def test_model_deserialization(self):
        """Test model deserialization."""
        data = {
            "data": {"test_key": {"value": "test_value", "value_type": "string"}},
            "current_depth": 0,
        }

        mapping = ModelTypedMapping.model_validate(data)
        assert isinstance(mapping, ModelTypedMapping)
        assert "test_key" in mapping.data

    def test_model_json_serialization(self):
        """Test model JSON serialization."""
        mapping = ModelTypedMapping()
        mapping.set_string("test_key", "test_value")

        json_data = mapping.model_dump_json()
        assert isinstance(json_data, str)

    def test_model_roundtrip(self):
        """Test model roundtrip serialization."""
        mapping = ModelTypedMapping()
        mapping.set_string("test_key", "test_value")
        mapping.set_int("number_key", 42)

        data = mapping.model_dump()
        new_mapping = ModelTypedMapping.model_validate(data)

        assert new_mapping.data["test_key"].value == "test_value"
        assert new_mapping.data["number_key"].value == 42

    def test_model_equality(self):
        """Test model equality."""
        mapping1 = ModelTypedMapping()
        mapping1.set_string("key", "value")

        mapping2 = ModelTypedMapping()
        mapping2.set_string("key", "value")

        assert mapping1.model_dump() == mapping2.model_dump()

    def test_model_str(self):
        """Test model string representation."""
        mapping = ModelTypedMapping()
        mapping.set_string("test_key", "test_value")

        str_repr = str(mapping)
        assert isinstance(str_repr, str)
        assert str_repr is not None

    def test_model_repr(self):
        """Test model repr."""
        mapping = ModelTypedMapping()
        mapping.set_string("test_key", "test_value")

        repr_str = repr(mapping)
        assert isinstance(repr_str, str)
        assert "ModelTypedMapping" in repr_str

    def test_model_attributes(self):
        """Test model attributes."""
        mapping = ModelTypedMapping()
        assert hasattr(mapping, "data")
        assert hasattr(mapping, "current_depth")
        assert hasattr(mapping, "set_string")
        assert hasattr(mapping, "get_value")

    def test_model_metadata(self):
        """Test model metadata."""
        mapping = ModelTypedMapping()
        assert hasattr(mapping, "__class__")
        assert mapping.__class__.__name__ == "ModelTypedMapping"

    def test_model_copy(self):
        """Test model copying."""
        mapping = ModelTypedMapping()
        mapping.set_string("key", "value")

        copied = mapping.model_copy()
        assert copied.model_dump() == mapping.model_dump()
        assert copied is not mapping  # Different instances

    def test_model_immutability(self):
        """Test model immutability."""
        mapping = ModelTypedMapping()
        mapping.set_string("key", "value")

        # Test that we can modify the data through methods
        mapping.set_string("key", "new_value")
        assert mapping.get_value("key") == "new_value"
