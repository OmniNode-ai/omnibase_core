"""
Tests for ModelDictValueUnion - Dict-containing union patterns.

This test suite ensures comprehensive coverage of the ModelDictValueUnion model,
which provides type-safe wrappers for Union[bool, dict, float, int, list, str] patterns.
"""

import json

import pytest

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_dict_value_union import ModelDictValueUnion

# === Basic Creation Tests (15 tests) ===


class TestBasicCreation:
    """Test basic creation of ModelDictValueUnion for all supported types."""

    def test_create_bool_value(self) -> None:
        """Test creating a boolean value."""
        value = ModelDictValueUnion(value=True, value_type="bool")
        assert value.value_type == "bool"
        assert value.value is True

    def test_create_dict_value(self) -> None:
        """Test creating a dict value."""
        value = ModelDictValueUnion(value={"key": "value"}, value_type="dict")
        assert value.value_type == "dict"
        assert value.value == {"key": "value"}

    def test_create_float_value(self) -> None:
        """Test creating a float value."""
        value = ModelDictValueUnion(value=3.14, value_type="float")
        assert value.value_type == "float"
        assert value.value == 3.14

    def test_create_int_value(self) -> None:
        """Test creating an int value."""
        value = ModelDictValueUnion(value=42, value_type="int")
        assert value.value_type == "int"
        assert value.value == 42

    def test_create_list_value(self) -> None:
        """Test creating a list value."""
        value = ModelDictValueUnion(value=[1, 2, 3], value_type="list")
        assert value.value_type == "list"
        assert value.value == [1, 2, 3]

    def test_create_str_value(self) -> None:
        """Test creating a string value."""
        value = ModelDictValueUnion(value="hello", value_type="str")
        assert value.value_type == "str"
        assert value.value == "hello"

    def test_create_with_metadata(self) -> None:
        """Test creating value with metadata."""
        value = ModelDictValueUnion(
            value=42, value_type="int", metadata={"source": "api"}
        )
        assert value.metadata == {"source": "api"}

    def test_create_empty_dict(self) -> None:
        """Test creating empty dict value."""
        value = ModelDictValueUnion(value={}, value_type="dict")
        assert value.value_type == "dict"
        assert value.value == {}

    def test_create_empty_list(self) -> None:
        """Test creating empty list value."""
        value = ModelDictValueUnion(value=[], value_type="list")
        assert value.value_type == "list"
        assert value.value == []

    def test_create_empty_string(self) -> None:
        """Test creating empty string value."""
        value = ModelDictValueUnion(value="", value_type="str")
        assert value.value_type == "str"
        assert value.value == ""

    def test_create_bool_false(self) -> None:
        """Test creating False bool value."""
        value = ModelDictValueUnion(value=False, value_type="bool")
        assert value.value_type == "bool"
        assert value.value is False

    def test_create_zero_int(self) -> None:
        """Test creating zero int value."""
        value = ModelDictValueUnion(value=0, value_type="int")
        assert value.value_type == "int"
        assert value.value == 0

    def test_create_zero_float(self) -> None:
        """Test creating zero float value."""
        value = ModelDictValueUnion(value=0.0, value_type="float")
        assert value.value_type == "float"
        assert value.value == 0.0

    def test_create_negative_int(self) -> None:
        """Test creating negative int value."""
        value = ModelDictValueUnion(value=-42, value_type="int")
        assert value.value_type == "int"
        assert value.value == -42

    def test_create_negative_float(self) -> None:
        """Test creating negative float value."""
        value = ModelDictValueUnion(value=-3.14, value_type="float")
        assert value.value_type == "float"
        assert value.value == -3.14


# === Type Discrimination Tests (10 tests) ===


class TestTypeDiscrimination:
    """Test automatic type discrimination."""

    def test_infer_bool_type(self) -> None:
        """Test automatic bool type inference."""
        value = ModelDictValueUnion(value=True)
        assert value.value_type == "bool"

    def test_infer_dict_type(self) -> None:
        """Test automatic dict type inference."""
        value = ModelDictValueUnion(value={"key": "value"})
        assert value.value_type == "dict"

    def test_infer_float_type(self) -> None:
        """Test automatic float type inference."""
        value = ModelDictValueUnion(value=3.14)
        assert value.value_type == "float"

    def test_infer_int_type(self) -> None:
        """Test automatic int type inference."""
        value = ModelDictValueUnion(value=42)
        assert value.value_type == "int"

    def test_infer_list_type(self) -> None:
        """Test automatic list type inference."""
        value = ModelDictValueUnion(value=[1, 2, 3])
        assert value.value_type == "list"

    def test_infer_str_type(self) -> None:
        """Test automatic string type inference."""
        value = ModelDictValueUnion(value="hello")
        assert value.value_type == "str"

    def test_bool_not_coerced_to_int(self) -> None:
        """Test that bool is not coerced to int."""
        value = ModelDictValueUnion(value=True)
        assert value.value_type == "bool"
        assert value.value_type != "int"

    def test_dict_takes_precedence_over_list(self) -> None:
        """Test that dict is detected before list."""
        value = ModelDictValueUnion(value={"a": [1, 2, 3]})
        assert value.value_type == "dict"

    def test_infer_from_dict_input(self) -> None:
        """Test inference from dict input."""
        value = ModelDictValueUnion.model_validate({"value": 42})
        assert value.value_type == "int"

    def test_explicit_type_overrides_inference(self) -> None:
        """Test that explicit type is respected."""
        value = ModelDictValueUnion(value=42, value_type="int")
        assert value.value_type == "int"


# === Type Guard Tests (15 tests) ===


class TestTypeGuards:
    """Test type guard methods."""

    def test_is_bool_returns_true_for_bool(self) -> None:
        """Test is_bool() returns True for bool value."""
        value = ModelDictValueUnion(value=True)
        assert value.is_bool()

    def test_is_bool_returns_false_for_non_bool(self) -> None:
        """Test is_bool() returns False for non-bool value."""
        value = ModelDictValueUnion(value=42)
        assert not value.is_bool()

    def test_is_dict_returns_true_for_dict(self) -> None:
        """Test is_dict() returns True for dict value."""
        value = ModelDictValueUnion(value={"key": "value"})
        assert value.is_dict()

    def test_is_dict_returns_false_for_non_dict(self) -> None:
        """Test is_dict() returns False for non-dict value."""
        value = ModelDictValueUnion(value=42)
        assert not value.is_dict()

    def test_is_float_returns_true_for_float(self) -> None:
        """Test is_float() returns True for float value."""
        value = ModelDictValueUnion(value=3.14)
        assert value.is_float()

    def test_is_float_returns_false_for_non_float(self) -> None:
        """Test is_float() returns False for non-float value."""
        value = ModelDictValueUnion(value=42)
        assert not value.is_float()

    def test_is_int_returns_true_for_int(self) -> None:
        """Test is_int() returns True for int value."""
        value = ModelDictValueUnion(value=42)
        assert value.is_int()

    def test_is_int_returns_false_for_non_int(self) -> None:
        """Test is_int() returns False for non-int value."""
        value = ModelDictValueUnion(value="hello")
        assert not value.is_int()

    def test_is_list_returns_true_for_list(self) -> None:
        """Test is_list() returns True for list value."""
        value = ModelDictValueUnion(value=[1, 2, 3])
        assert value.is_list()

    def test_is_list_returns_false_for_non_list(self) -> None:
        """Test is_list() returns False for non-list value."""
        value = ModelDictValueUnion(value=42)
        assert not value.is_list()

    def test_is_string_returns_true_for_string(self) -> None:
        """Test is_string() returns True for string value."""
        value = ModelDictValueUnion(value="hello")
        assert value.is_string()

    def test_is_string_returns_false_for_non_string(self) -> None:
        """Test is_string() returns False for non-string value."""
        value = ModelDictValueUnion(value=42)
        assert not value.is_string()

    def test_multiple_type_guards(self) -> None:
        """Test that only one type guard is true at a time."""
        value = ModelDictValueUnion(value={"key": "value"})
        assert value.is_dict()
        assert not value.is_bool()
        assert not value.is_float()
        assert not value.is_int()
        assert not value.is_list()
        assert not value.is_string()

    def test_type_guards_for_empty_dict(self) -> None:
        """Test type guards work for empty dict."""
        value = ModelDictValueUnion(value={})
        assert value.is_dict()
        assert not value.is_list()

    def test_type_guards_for_false_bool(self) -> None:
        """Test type guards work for False bool."""
        value = ModelDictValueUnion(value=False)
        assert value.is_bool()
        assert not value.is_int()


# === Type Getter Tests (20 tests) ===


class TestTypeGetters:
    """Test type getter methods."""

    def test_get_as_bool_success(self) -> None:
        """Test get_as_bool() returns correct value."""
        value = ModelDictValueUnion(value=True)
        assert value.get_as_bool() is True

    def test_get_as_bool_failure(self) -> None:
        """Test get_as_bool() raises error for wrong type."""
        value = ModelDictValueUnion(value=42)
        with pytest.raises(ModelOnexError) as exc_info:
            value.get_as_bool()
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_get_as_dict_success(self) -> None:
        """Test get_as_dict() returns correct value."""
        value = ModelDictValueUnion(value={"key": "value"})
        assert value.get_as_dict() == {"key": "value"}

    def test_get_as_dict_returns_empty_for_non_dict(self) -> None:
        """Test get_as_dict() returns empty dict for non-dict value."""
        value = ModelDictValueUnion(value=42)
        assert value.get_as_dict() == {}

    def test_get_as_float_success(self) -> None:
        """Test get_as_float() returns correct value."""
        value = ModelDictValueUnion(value=3.14)
        assert value.get_as_float() == 3.14

    def test_get_as_float_failure(self) -> None:
        """Test get_as_float() raises error for wrong type."""
        value = ModelDictValueUnion(value=42)
        with pytest.raises(ModelOnexError) as exc_info:
            value.get_as_float()
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_get_as_int_success(self) -> None:
        """Test get_as_int() returns correct value."""
        value = ModelDictValueUnion(value=42)
        assert value.get_as_int() == 42

    def test_get_as_int_failure(self) -> None:
        """Test get_as_int() raises error for wrong type."""
        value = ModelDictValueUnion(value="hello")
        with pytest.raises(ModelOnexError) as exc_info:
            value.get_as_int()
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_get_as_list_success(self) -> None:
        """Test get_as_list() returns correct value."""
        value = ModelDictValueUnion(value=[1, 2, 3])
        assert value.get_as_list() == [1, 2, 3]

    def test_get_as_list_failure(self) -> None:
        """Test get_as_list() raises error for wrong type."""
        value = ModelDictValueUnion(value=42)
        with pytest.raises(ModelOnexError) as exc_info:
            value.get_as_list()
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_get_as_str_success(self) -> None:
        """Test get_as_str() returns correct value."""
        value = ModelDictValueUnion(value="hello")
        assert value.get_as_str() == "hello"

    def test_get_as_str_failure(self) -> None:
        """Test get_as_str() raises error for wrong type."""
        value = ModelDictValueUnion(value=42)
        with pytest.raises(ModelOnexError) as exc_info:
            value.get_as_str()
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_get_value_returns_correct_type(self) -> None:
        """Test get_value() returns value with correct type."""
        value = ModelDictValueUnion(value={"key": "value"})
        result = value.get_value()
        assert isinstance(result, dict)
        assert result == {"key": "value"}

    def test_get_python_type_for_dict(self) -> None:
        """Test get_python_type() returns correct type for dict."""
        value = ModelDictValueUnion(value={"key": "value"})
        assert value.get_python_type() == dict

    def test_get_python_type_for_int(self) -> None:
        """Test get_python_type() returns correct type for int."""
        value = ModelDictValueUnion(value=42)
        assert value.get_python_type() == int

    def test_get_python_type_for_bool(self) -> None:
        """Test get_python_type() returns correct type for bool."""
        value = ModelDictValueUnion(value=True)
        assert value.get_python_type() == bool

    def test_get_python_type_for_float(self) -> None:
        """Test get_python_type() returns correct type for float."""
        value = ModelDictValueUnion(value=3.14)
        assert value.get_python_type() == float

    def test_get_python_type_for_list(self) -> None:
        """Test get_python_type() returns correct type for list."""
        value = ModelDictValueUnion(value=[1, 2, 3])
        assert value.get_python_type() == list

    def test_get_python_type_for_str(self) -> None:
        """Test get_python_type() returns correct type for str."""
        value = ModelDictValueUnion(value="hello")
        assert value.get_python_type() == str

    def test_get_as_bool_with_false(self) -> None:
        """Test get_as_bool() works with False."""
        value = ModelDictValueUnion(value=False)
        assert value.get_as_bool() is False


# === Dict Handling Tests (20 tests) ===


class TestDictHandling:
    """Test dict-specific handling."""

    def test_nested_dict(self) -> None:
        """Test handling of nested dict."""
        nested = {"level1": {"level2": {"level3": "value"}}}
        value = ModelDictValueUnion(value=nested)
        assert value.is_dict()
        assert value.get_as_dict() == nested

    def test_dict_with_various_types(self) -> None:
        """Test dict with various value types."""
        data = {
            "bool": True,
            "int": 42,
            "float": 3.14,
            "str": "hello",
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
        }
        value = ModelDictValueUnion(value=data)
        assert value.is_dict()
        assert value.get_as_dict() == data

    def test_dict_with_list_values(self) -> None:
        """Test dict containing list values."""
        data = {"items": [1, 2, 3], "more": [4, 5, 6]}
        value = ModelDictValueUnion(value=data)
        assert value.get_as_dict() == data

    def test_dict_with_nested_lists(self) -> None:
        """Test dict with nested lists."""
        data = {"nested_lists": [[1, 2], [3, 4], [5, 6]]}
        value = ModelDictValueUnion(value=data)
        assert value.get_as_dict() == data

    def test_empty_dict_handling(self) -> None:
        """Test empty dict is handled correctly."""
        value = ModelDictValueUnion(value={})
        assert value.is_dict()
        assert value.get_as_dict() == {}

    def test_dict_with_unicode_keys(self) -> None:
        """Test dict with unicode string keys."""
        data = {
            "key_à": "a_grave",
            "key_é": "e_acute",
            "key_ñ": "n_tilde",
        }
        value = ModelDictValueUnion(value=data)
        assert value.get_as_dict() == data

    def test_dict_with_numeric_string_keys(self) -> None:
        """Test dict with numeric string keys."""
        data = {"1": "one", "2": "two", "3": "three"}
        value = ModelDictValueUnion(value=data)
        assert value.get_as_dict() == data

    def test_dict_size_limit_not_exceeded(self) -> None:
        """Test dict within size limit is accepted."""
        data = {f"key_{i}": i for i in range(100)}
        value = ModelDictValueUnion(value=data)
        assert value.is_dict()
        assert len(value.get_as_dict()) == 100

    def test_dict_size_limit_exceeded(self) -> None:
        """Test dict exceeding size limit is rejected."""
        data = {f"key_{i}": i for i in range(1001)}
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDictValueUnion(value=data)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "maximum size" in exc_info.value.message.lower()

    def test_dict_with_special_characters_in_keys(self) -> None:
        """Test dict with special characters in keys."""
        data = {"key-with-dash": 1, "key.with.dot": 2, "key_with_underscore": 3}
        value = ModelDictValueUnion(value=data)
        assert value.get_as_dict() == data

    def test_dict_with_empty_string_key(self) -> None:
        """Test dict with empty string key."""
        data = {"": "empty_key", "normal": "value"}
        value = ModelDictValueUnion(value=data)
        assert value.get_as_dict() == data

    def test_deeply_nested_dict(self) -> None:
        """Test deeply nested dict structure."""
        data = {"l1": {"l2": {"l3": {"l4": {"l5": "deep_value"}}}}}
        value = ModelDictValueUnion(value=data)
        assert value.get_as_dict() == data

    def test_dict_preserves_structure(self) -> None:
        """Test that dict structure is preserved."""
        data = {"a": {"b": [1, 2, {"c": 3}]}}
        value = ModelDictValueUnion(value=data)
        result = value.get_as_dict()
        assert result["a"]["b"][2]["c"] == 3

    def test_dict_with_none_values(self) -> None:
        """Test dict with None values."""
        data = {"key1": None, "key2": "value", "key3": None}
        value = ModelDictValueUnion(value=data)
        assert value.get_as_dict() == data

    def test_dict_with_mixed_list_values(self) -> None:
        """Test dict with mixed type list values."""
        data = {"mixed": [1, "two", 3.0, True, {"nested": "dict"}]}
        value = ModelDictValueUnion(value=data)
        assert value.get_as_dict() == data

    def test_dict_with_boolean_values(self) -> None:
        """Test dict with boolean values."""
        data = {"flag1": True, "flag2": False, "flag3": True}
        value = ModelDictValueUnion(value=data)
        assert value.get_as_dict() == data

    def test_dict_with_float_values(self) -> None:
        """Test dict with float values."""
        data = {"pi": 3.14159, "e": 2.71828, "phi": 1.61803}
        value = ModelDictValueUnion(value=data)
        assert value.get_as_dict() == data

    def test_dict_with_empty_nested_dicts(self) -> None:
        """Test dict with empty nested dicts."""
        data = {"outer": {}, "inner": {"nested": {}}}
        value = ModelDictValueUnion(value=data)
        assert value.get_as_dict() == data

    def test_dict_with_empty_lists(self) -> None:
        """Test dict with empty list values."""
        data = {"list1": [], "list2": [], "list3": []}
        value = ModelDictValueUnion(value=data)
        assert value.get_as_dict() == data

    def test_dict_json_serializable(self) -> None:
        """Test that dict value is JSON serializable."""
        data = {"key": "value", "number": 42, "list": [1, 2, 3]}
        value = ModelDictValueUnion(value=data)
        # Should not raise
        json.dumps(value.get_as_dict())


# === Dict Access Tests (15 tests) ===


class TestDictAccess:
    """Test dict-specific access methods."""

    def test_has_key_returns_true_for_existing_key(self) -> None:
        """Test has_key() returns True for existing key."""
        value = ModelDictValueUnion(value={"a": 1, "b": 2})
        assert value.has_key("a")

    def test_has_key_returns_false_for_missing_key(self) -> None:
        """Test has_key() returns False for missing key."""
        value = ModelDictValueUnion(value={"a": 1, "b": 2})
        assert not value.has_key("c")

    def test_has_key_returns_false_for_non_dict(self) -> None:
        """Test has_key() returns False when value is not dict."""
        value = ModelDictValueUnion(value=42)
        assert not value.has_key("any")

    def test_get_dict_value_returns_value(self) -> None:
        """Test get_dict_value() returns correct value."""
        value = ModelDictValueUnion(value={"a": 1, "b": 2})
        assert value.get_dict_value("a") == 1

    def test_get_dict_value_returns_default_for_missing_key(self) -> None:
        """Test get_dict_value() returns default for missing key."""
        value = ModelDictValueUnion(value={"a": 1, "b": 2})
        assert value.get_dict_value("c", 99) == 99

    def test_get_dict_value_returns_none_default(self) -> None:
        """Test get_dict_value() returns None by default."""
        value = ModelDictValueUnion(value={"a": 1})
        assert value.get_dict_value("b") is None

    def test_get_dict_value_returns_default_for_non_dict(self) -> None:
        """Test get_dict_value() returns default when value is not dict."""
        value = ModelDictValueUnion(value=42)
        assert value.get_dict_value("any", 99) == 99

    def test_has_key_with_nested_dict(self) -> None:
        """Test has_key() works with nested dict."""
        value = ModelDictValueUnion(value={"outer": {"inner": "value"}})
        assert value.has_key("outer")
        assert not value.has_key("inner")  # inner is nested, not top-level

    def test_get_dict_value_with_nested_dict(self) -> None:
        """Test get_dict_value() returns nested dict."""
        value = ModelDictValueUnion(value={"outer": {"inner": "value"}})
        result = value.get_dict_value("outer")
        assert isinstance(result, dict)
        assert result == {"inner": "value"}

    def test_has_key_with_empty_dict(self) -> None:
        """Test has_key() with empty dict."""
        value = ModelDictValueUnion(value={})
        assert not value.has_key("any")

    def test_get_dict_value_with_empty_dict(self) -> None:
        """Test get_dict_value() with empty dict."""
        value = ModelDictValueUnion(value={})
        assert value.get_dict_value("any", 99) == 99

    def test_has_key_with_none_value(self) -> None:
        """Test has_key() when dict has None value."""
        value = ModelDictValueUnion(value={"key": None})
        assert value.has_key("key")

    def test_get_dict_value_returns_none_value(self) -> None:
        """Test get_dict_value() returns None when value is None."""
        value = ModelDictValueUnion(value={"key": None})
        assert value.get_dict_value("key") is None

    def test_has_key_case_sensitive(self) -> None:
        """Test has_key() is case sensitive."""
        value = ModelDictValueUnion(value={"Key": 1})
        assert value.has_key("Key")
        assert not value.has_key("key")

    def test_get_dict_value_with_complex_default(self) -> None:
        """Test get_dict_value() with complex default value."""
        value = ModelDictValueUnion(value={"a": 1})
        default = {"nested": "default"}
        result = value.get_dict_value("b", default)
        assert result == default


# === List Handling Tests (10 tests) ===


class TestListHandling:
    """Test list-specific handling."""

    def test_list_with_dicts(self) -> None:
        """Test list containing dicts."""
        data = [{"a": 1}, {"b": 2}, {"c": 3}]
        value = ModelDictValueUnion(value=data)
        assert value.is_list()
        assert value.get_as_list() == data

    def test_list_with_mixed_types(self) -> None:
        """Test list with mixed types."""
        data = [1, "two", 3.0, True, {"key": "value"}, [5, 6]]
        value = ModelDictValueUnion(value=data)
        assert value.get_as_list() == data

    def test_nested_lists(self) -> None:
        """Test nested lists."""
        data = [[1, 2], [3, 4], [5, 6]]
        value = ModelDictValueUnion(value=data)
        assert value.get_as_list() == data

    def test_list_size_limit_not_exceeded(self) -> None:
        """Test list within size limit is accepted."""
        data = list(range(1000))
        value = ModelDictValueUnion(value=data)
        assert len(value.get_as_list()) == 1000

    def test_list_size_limit_exceeded(self) -> None:
        """Test list exceeding size limit is rejected."""
        data = list(range(10001))
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDictValueUnion(value=data)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "maximum size" in exc_info.value.message.lower()

    def test_empty_list(self) -> None:
        """Test empty list handling."""
        value = ModelDictValueUnion(value=[])
        assert value.is_list()
        assert value.get_as_list() == []

    def test_list_with_nested_dicts(self) -> None:
        """Test list with nested dicts."""
        data = [{"outer": {"inner": "value"}}]
        value = ModelDictValueUnion(value=data)
        assert value.get_as_list() == data

    def test_list_preserves_order(self) -> None:
        """Test list preserves order."""
        data = [3, 1, 4, 1, 5, 9, 2, 6]
        value = ModelDictValueUnion(value=data)
        assert value.get_as_list() == data

    def test_list_with_none_values(self) -> None:
        """Test list with None values."""
        data = [1, None, 3, None, 5]
        value = ModelDictValueUnion(value=data)
        assert value.get_as_list() == data

    def test_list_with_duplicate_dicts(self) -> None:
        """Test list with duplicate dict values."""
        data = [{"a": 1}, {"a": 1}, {"b": 2}]
        value = ModelDictValueUnion(value=data)
        assert value.get_as_list() == data


# === Validation Tests (10 tests) ===


class TestValidation:
    """Test validation and error handling."""

    def test_invalid_type_raises_error(self) -> None:
        """Test unsupported type raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDictValueUnion(value=object())  # type: ignore[arg-type]
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_type_mismatch_raises_error(self) -> None:
        """Test type mismatch raises error."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDictValueUnion(value="hello", value_type="int")
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_nan_float_rejected(self) -> None:
        """Test NaN float is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDictValueUnion(value=float("nan"))
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "nan" in exc_info.value.message.lower()

    def test_infinity_float_rejected(self) -> None:
        """Test infinity float is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDictValueUnion(value=float("inf"))
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "infinity" in exc_info.value.message.lower()

    def test_negative_infinity_rejected(self) -> None:
        """Test negative infinity is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDictValueUnion(value=float("-inf"))
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_dict_with_non_string_keys_rejected(self) -> None:
        """Test dict with non-string keys is rejected."""
        # Pydantic catches this at field validation level before our validator
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc_info:
            ModelDictValueUnion(value={1: "value", 2: "value"})  # type: ignore[dict-item]
        assert "string" in str(exc_info.value).lower()

    def test_invalid_value_type_literal_rejected(self) -> None:
        """Test invalid value_type literal is rejected."""
        with pytest.raises(Exception):  # Pydantic validation error
            ModelDictValueUnion(value=42, value_type="invalid")  # type: ignore[arg-type]

    def test_bool_not_confused_with_int(self) -> None:
        """Test bool is not confused with int in validation."""
        # Bool value with int type should fail
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDictValueUnion(value=True, value_type="int")
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_int_not_confused_with_bool(self) -> None:
        """Test int is not confused with bool in validation."""
        # Int value with bool type should fail
        with pytest.raises(ModelOnexError) as exc_info:
            ModelDictValueUnion(value=1, value_type="bool")
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_metadata_must_be_dict(self) -> None:
        """Test metadata must be string dict."""
        # This should work
        value = ModelDictValueUnion(value=42, metadata={"key": "value"})
        assert value.metadata == {"key": "value"}


# === JSON Serialization Tests (10 tests) ===


class TestJSONSerialization:
    """Test JSON serialization and deserialization."""

    def test_model_dump_dict(self) -> None:
        """Test model_dump() for dict value."""
        value = ModelDictValueUnion(value={"key": "value"})
        data = value.model_dump()
        assert data["value"] == {"key": "value"}
        assert data["value_type"] == "dict"

    def test_model_dump_int(self) -> None:
        """Test model_dump() for int value."""
        value = ModelDictValueUnion(value=42)
        data = value.model_dump()
        assert data["value"] == 42
        assert data["value_type"] == "int"

    def test_model_dump_json(self) -> None:
        """Test model_dump_json() serialization."""
        value = ModelDictValueUnion(value={"key": "value"})
        json_str = value.model_dump_json()
        assert '"value_type":"dict"' in json_str or '"value_type": "dict"' in json_str

    def test_model_validate_from_dict(self) -> None:
        """Test model_validate() from dict."""
        data = {"value": {"key": "value"}, "value_type": "dict"}
        value = ModelDictValueUnion.model_validate(data)
        assert value.value == {"key": "value"}
        assert value.value_type == "dict"

    def test_model_validate_json(self) -> None:
        """Test model_validate_json() deserialization."""
        json_str = '{"value": {"key": "value"}, "value_type": "dict"}'
        value = ModelDictValueUnion.model_validate_json(json_str)
        assert value.value == {"key": "value"}

    def test_as_dict_method(self) -> None:
        """Test as_dict() helper method."""
        value = ModelDictValueUnion(value=42, metadata={"source": "test"})
        data = value.as_dict()
        assert data["value"] == 42
        assert data["value_type"] == "int"
        assert data["metadata"] == {"source": "test"}

    def test_round_trip_serialization(self) -> None:
        """Test round-trip serialization."""
        original = ModelDictValueUnion(value={"nested": {"data": 42}})
        json_str = original.model_dump_json()
        restored = ModelDictValueUnion.model_validate_json(json_str)
        assert restored.value == original.value
        assert restored.value_type == original.value_type

    def test_serialization_with_metadata(self) -> None:
        """Test serialization preserves metadata."""
        value = ModelDictValueUnion(value=42, metadata={"key": "val"})
        json_str = value.model_dump_json()
        restored = ModelDictValueUnion.model_validate_json(json_str)
        assert restored.metadata == {"key": "val"}

    def test_nested_dict_serialization(self) -> None:
        """Test nested dict serialization."""
        nested = {"l1": {"l2": {"l3": "value"}}}
        value = ModelDictValueUnion(value=nested)
        json_str = value.model_dump_json()
        restored = ModelDictValueUnion.model_validate_json(json_str)
        assert restored.value == nested

    def test_list_with_dicts_serialization(self) -> None:
        """Test list with dicts serialization."""
        data = [{"a": 1}, {"b": 2}]
        value = ModelDictValueUnion(value=data)
        json_str = value.model_dump_json()
        restored = ModelDictValueUnion.model_validate_json(json_str)
        assert restored.value == data


# === Edge Cases Tests (5 tests) ===


class TestEdgeCases:
    """Test edge cases and corner scenarios."""

    def test_empty_collections_allowed(self) -> None:
        """Test empty collections are allowed."""
        dict_value = ModelDictValueUnion(value={})
        list_value = ModelDictValueUnion(value=[])
        str_value = ModelDictValueUnion(value="")

        assert dict_value.value == {}
        assert list_value.value == []
        assert str_value.value == ""

    def test_deeply_nested_dict_structure(self) -> None:
        """Test deeply nested dict (5+ levels)."""
        data = {"l1": {"l2": {"l3": {"l4": {"l5": {"l6": "deep"}}}}}}
        value = ModelDictValueUnion(value=data)
        assert value.get_as_dict() == data

    def test_is_primitive_for_all_types(self) -> None:
        """Test is_primitive() for all types."""
        assert ModelDictValueUnion(value=True).is_primitive()
        assert not ModelDictValueUnion(value={"a": 1}).is_primitive()
        assert ModelDictValueUnion(value=3.14).is_primitive()
        assert ModelDictValueUnion(value=42).is_primitive()
        assert not ModelDictValueUnion(value=[1, 2]).is_primitive()
        assert ModelDictValueUnion(value="hi").is_primitive()

    def test_is_collection_for_all_types(self) -> None:
        """Test is_collection() for all types."""
        assert not ModelDictValueUnion(value=True).is_collection()
        assert ModelDictValueUnion(value={"a": 1}).is_collection()
        assert not ModelDictValueUnion(value=3.14).is_collection()
        assert not ModelDictValueUnion(value=42).is_collection()
        assert ModelDictValueUnion(value=[1, 2]).is_collection()
        assert not ModelDictValueUnion(value="hi").is_collection()

    def test_string_representation(self) -> None:
        """Test string representations."""
        value = ModelDictValueUnion(value={"key": "value"})
        str_repr = str(value)
        repr_repr = repr(value)

        assert "dict" in str_repr.lower()
        assert "ModelDictValueUnion" in repr_repr


# === Additional Coverage Tests ===


class TestAdditionalCoverage:
    """Additional tests for comprehensive coverage."""

    def test_large_dict_within_limit(self) -> None:
        """Test large dict within limit is accepted."""
        data = {f"key_{i}": f"value_{i}" for i in range(500)}
        value = ModelDictValueUnion(value=data)
        assert len(value.get_as_dict()) == 500

    def test_large_list_within_limit(self) -> None:
        """Test large list within limit is accepted."""
        data = list(range(5000))
        value = ModelDictValueUnion(value=data)
        assert len(value.get_as_list()) == 5000

    def test_dict_with_all_primitive_types(self) -> None:
        """Test dict containing all primitive types."""
        data = {
            "bool_val": True,
            "int_val": 42,
            "float_val": 3.14,
            "str_val": "hello",
        }
        value = ModelDictValueUnion(value=data)
        result = value.get_as_dict()
        assert result["bool_val"] is True
        assert result["int_val"] == 42
        assert result["float_val"] == 3.14
        assert result["str_val"] == "hello"

    def test_list_of_dicts_with_nested_lists(self) -> None:
        """Test complex nested structure."""
        data = [{"items": [1, 2, {"nested": [3, 4]}]}]
        value = ModelDictValueUnion(value=data)
        assert value.get_as_list() == data

    def test_metadata_isolation(self) -> None:
        """Test metadata doesn't interfere with value."""
        value = ModelDictValueUnion(
            value={"data": "value"}, metadata={"source": "test"}
        )
        assert "source" not in value.get_as_dict()
        assert value.metadata["source"] == "test"
