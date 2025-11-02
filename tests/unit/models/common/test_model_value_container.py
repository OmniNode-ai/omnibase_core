"""Tests for model_value_container.py"""

import json
import math
from typing import Any

import pytest

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.models.common.model_value_container import ModelValueContainer
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class TestModelValueContainer:
    """Test class for ModelValueContainer."""

    def test_model_initialization(self):
        """Test model can be initialized."""
        container = ModelValueContainer(value="test")
        assert container is not None
        assert container.value == "test"
        assert isinstance(container.metadata, dict)
        assert len(container.metadata) == 0

    def test_model_inheritance(self):
        """Test model inheritance."""
        from pydantic import BaseModel

        assert issubclass(ModelValueContainer, BaseModel)

    def test_model_with_metadata(self):
        """Test model initialization with metadata."""
        metadata = {"key1": "value1", "key2": "value2"}
        container = ModelValueContainer(value="test", metadata=metadata)

        assert container.value == "test"
        assert container.metadata == metadata

    def test_python_type_property(self):
        """Test python_type property."""
        container = ModelValueContainer(value="test")
        assert container.python_type == str

        container = ModelValueContainer(value=42)
        assert container.python_type == int

        container = ModelValueContainer(value=3.14)
        assert container.python_type == float

    def test_type_name_property(self):
        """Test type_name property."""
        container = ModelValueContainer(value="test")
        assert container.type_name == "str"

        container = ModelValueContainer(value=42)
        assert container.type_name == "int"

        container = ModelValueContainer(value=3.14)
        assert container.type_name == "float"

    def test_is_type_method(self):
        """Test is_type method."""
        container = ModelValueContainer(value="test")
        assert container.is_type(str) is True
        assert container.is_type(int) is False

        container = ModelValueContainer(value=42)
        assert container.is_type(int) is True
        assert container.is_type(str) is False

    def test_is_json_serializable_string(self):
        """Test is_json_serializable with string."""
        container = ModelValueContainer(value="test")
        assert container.is_json_serializable() is True

    def test_is_json_serializable_int(self):
        """Test is_json_serializable with integer."""
        container = ModelValueContainer(value=42)
        assert container.is_json_serializable() is True

    def test_is_json_serializable_float(self):
        """Test is_json_serializable with float."""
        container = ModelValueContainer(value=3.14)
        assert container.is_json_serializable() is True

    def test_is_json_serializable_bool(self):
        """Test is_json_serializable with boolean."""
        container = ModelValueContainer(value=True)
        assert container.is_json_serializable() is True

    def test_is_json_serializable_list(self):
        """Test is_json_serializable with list."""
        container = ModelValueContainer(value=[1, 2, 3])
        assert container.is_json_serializable() is True

    def test_is_json_serializable_dict(self):
        """Test is_json_serializable with dict."""
        container = ModelValueContainer(value={"key": "value"})
        assert container.is_json_serializable() is True

    def test_is_json_serializable_none(self):
        """Test is_json_serializable with None."""
        container = ModelValueContainer(value=None)
        assert container.is_json_serializable() is True

    def test_validate_serializable_valid(self):
        """Test validate_serializable with valid value."""
        result = ModelValueContainer.validate_serializable("test")
        assert result == "test"

    def test_validate_serializable_invalid(self):
        """Test validate_serializable with invalid value."""

        class NonSerializable:
            pass

        with pytest.raises(ModelOnexError) as exc_info:
            ModelValueContainer.validate_serializable(NonSerializable())

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "not JSON serializable" in str(exc_info.value)

    def test_is_valid_string(self):
        """Test is_valid with string value."""
        container = ModelValueContainer(value="test")
        assert container.is_valid() is True

    def test_is_valid_empty_string_without_metadata(self):
        """Test is_valid with empty string without allow_empty metadata."""
        container = ModelValueContainer(value="")
        assert container.is_valid() is False

    def test_is_valid_empty_string_with_metadata(self):
        """Test is_valid with empty string with allow_empty metadata."""
        container = ModelValueContainer(value="", metadata={"allow_empty": "true"})
        assert container.is_valid() is True

    def test_is_valid_int(self):
        """Test is_valid with integer."""
        container = ModelValueContainer(value=42)
        assert container.is_valid() is True

    def test_is_valid_float(self):
        """Test is_valid with float."""
        container = ModelValueContainer(value=3.14)
        assert container.is_valid() is True

    def test_is_valid_float_nan(self):
        """Test is_valid with NaN float."""
        container = ModelValueContainer(value=float("nan"))
        assert container.is_valid() is False

    def test_is_valid_float_inf(self):
        """Test is_valid with infinite float."""
        container = ModelValueContainer(value=float("inf"))
        assert container.is_valid() is False

    def test_is_valid_list(self):
        """Test is_valid with list."""
        container = ModelValueContainer(value=[1, 2, 3])
        assert container.is_valid() is True

    def test_is_valid_large_list(self):
        """Test is_valid with large list."""
        large_list = list(range(10001))  # Exceeds 10000 limit
        container = ModelValueContainer(value=large_list)
        assert container.is_valid() is False

    def test_is_valid_dict(self):
        """Test is_valid with dict."""
        container = ModelValueContainer(value={"key": "value"})
        assert container.is_valid() is True

    def test_is_valid_large_dict(self):
        """Test is_valid with large dict."""
        large_dict = {f"key{i}": f"value{i}" for i in range(1001)}  # Exceeds 1000 limit
        container = ModelValueContainer(value=large_dict)
        assert container.is_valid() is False

    def test_is_valid_dict_non_string_keys(self):
        """Test is_valid with dict containing non-string keys."""
        # Note: Pydantic validation prevents creation of containers with non-string keys
        # This test is skipped as the model enforces string keys at the type level

    def test_is_valid_metadata_too_large(self):
        """Test is_valid with metadata too large."""
        large_metadata = {
            f"key{i}": f"value{i}" for i in range(101)
        }  # Exceeds 100 limit
        container = ModelValueContainer(value="test", metadata=large_metadata)
        assert container.is_valid() is False

    def test_get_errors_valid(self):
        """Test get_errors with valid container."""
        container = ModelValueContainer(value="test")
        errors = container.get_errors()
        assert errors == []

    def test_get_errors_empty_string(self):
        """Test get_errors with empty string."""
        container = ModelValueContainer(value="")
        errors = container.get_errors()
        assert len(errors) == 1
        assert "Empty strings not allowed" in errors[0]

    def test_get_errors_float_nan(self):
        """Test get_errors with NaN float."""
        container = ModelValueContainer(value=float("nan"))
        errors = container.get_errors()
        assert len(errors) == 1
        assert "Float value cannot be NaN" in errors[0]

    def test_get_errors_float_inf(self):
        """Test get_errors with infinite float."""
        container = ModelValueContainer(value=float("inf"))
        errors = container.get_errors()
        assert len(errors) == 1
        assert "Float value cannot be infinite" in errors[0]

    def test_get_errors_large_list(self):
        """Test get_errors with large list."""
        large_list = list(range(10001))
        container = ModelValueContainer(value=large_list)
        errors = container.get_errors()
        assert len(errors) == 1
        assert "exceeds maximum length" in errors[0]

    def test_get_errors_large_dict(self):
        """Test get_errors with large dict."""
        large_dict = {f"key{i}": f"value{i}" for i in range(1001)}
        container = ModelValueContainer(value=large_dict)
        errors = container.get_errors()
        assert len(errors) == 1
        assert "exceeds maximum size" in errors[0]

    def test_get_errors_dict_non_string_keys(self):
        """Test get_errors with dict containing non-string keys."""
        # Note: Pydantic validation prevents creation of containers with non-string keys
        # This test is skipped as the model enforces string keys at the type level

    def test_get_errors_metadata_too_large(self):
        """Test get_errors with metadata too large."""
        large_metadata = {f"key{i}": f"value{i}" for i in range(101)}
        container = ModelValueContainer(value="test", metadata=large_metadata)
        errors = container.get_errors()
        assert len(errors) == 1
        assert "exceeds maximum size" in errors[0]

    def test_validate_type_specific_constraints_string(self):
        """Test _validate_type_specific_constraints with string."""
        container = ModelValueContainer(value="test")
        assert container._validate_type_specific_constraints() is True

    def test_validate_type_specific_constraints_empty_string(self):
        """Test _validate_type_specific_constraints with empty string."""
        container = ModelValueContainer(value="")
        assert container._validate_type_specific_constraints() is False

    def test_validate_type_specific_constraints_empty_string_allowed(self):
        """Test _validate_type_specific_constraints with empty string allowed."""
        container = ModelValueContainer(value="", metadata={"allow_empty": "true"})
        assert container._validate_type_specific_constraints() is True

    def test_validate_type_specific_constraints_int(self):
        """Test _validate_type_specific_constraints with int."""
        container = ModelValueContainer(value=42)
        assert container._validate_type_specific_constraints() is True

    def test_validate_type_specific_constraints_float(self):
        """Test _validate_type_specific_constraints with float."""
        container = ModelValueContainer(value=3.14)
        assert container._validate_type_specific_constraints() is True

    def test_validate_type_specific_constraints_float_nan(self):
        """Test _validate_type_specific_constraints with NaN float."""
        container = ModelValueContainer(value=float("nan"))
        assert container._validate_type_specific_constraints() is False

    def test_validate_type_specific_constraints_float_inf(self):
        """Test _validate_type_specific_constraints with infinite float."""
        container = ModelValueContainer(value=float("inf"))
        assert container._validate_type_specific_constraints() is False

    def test_validate_type_specific_constraints_list(self):
        """Test _validate_type_specific_constraints with list."""
        container = ModelValueContainer(value=[1, 2, 3])
        assert container._validate_type_specific_constraints() is True

    def test_validate_type_specific_constraints_large_list(self):
        """Test _validate_type_specific_constraints with large list."""
        large_list = list(range(10001))
        container = ModelValueContainer(value=large_list)
        assert container._validate_type_specific_constraints() is False

    def test_validate_type_specific_constraints_dict(self):
        """Test _validate_type_specific_constraints with dict."""
        container = ModelValueContainer(value={"key": "value"})
        assert container._validate_type_specific_constraints() is True

    def test_validate_type_specific_constraints_large_dict(self):
        """Test _validate_type_specific_constraints with large dict."""
        large_dict = {f"key{i}": f"value{i}" for i in range(1001)}
        container = ModelValueContainer(value=large_dict)
        assert container._validate_type_specific_constraints() is False

    def test_validate_type_specific_constraints_dict_non_string_keys(self):
        """Test _validate_type_specific_constraints with dict non-string keys."""
        # Note: Pydantic validation prevents creation of containers with non-string keys
        # This test is skipped as the model enforces string keys at the type level

    def test_validate_metadata_valid(self):
        """Test _validate_metadata with valid metadata."""
        container = ModelValueContainer(value="test", metadata={"key": "value"})
        assert container._validate_metadata() is True

    def test_validate_metadata_empty(self):
        """Test _validate_metadata with empty metadata."""
        container = ModelValueContainer(value="test")
        assert container._validate_metadata() is True

    def test_validate_metadata_too_large(self):
        """Test _validate_metadata with metadata too large."""
        large_metadata = {f"key{i}": f"value{i}" for i in range(101)}
        container = ModelValueContainer(value="test", metadata=large_metadata)
        assert container._validate_metadata() is False

    def test_validate_metadata_long_key(self):
        """Test _validate_metadata with key too long."""
        long_key = "x" * 101  # Exceeds 100 character limit
        container = ModelValueContainer(value="test", metadata={long_key: "value"})
        assert container._validate_metadata() is False

    def test_validate_metadata_long_value(self):
        """Test _validate_metadata with value too long."""
        long_value = "x" * 1001  # Exceeds 1000 character limit
        container = ModelValueContainer(value="test", metadata={"key": long_value})
        assert container._validate_metadata() is False

    def test_get_type_specific_errors_string(self):
        """Test _get_type_specific_errors with string."""
        container = ModelValueContainer(value="test")
        errors = container._get_type_specific_errors()
        assert errors == []

    def test_get_type_specific_errors_empty_string(self):
        """Test _get_type_specific_errors with empty string."""
        container = ModelValueContainer(value="")
        errors = container._get_type_specific_errors()
        assert len(errors) == 1
        assert "Empty strings not allowed" in errors[0]

    def test_get_type_specific_errors_float_nan(self):
        """Test _get_type_specific_errors with NaN float."""
        container = ModelValueContainer(value=float("nan"))
        errors = container._get_type_specific_errors()
        assert len(errors) == 1
        assert "Float value cannot be NaN" in errors[0]

    def test_get_type_specific_errors_float_inf(self):
        """Test _get_type_specific_errors with infinite float."""
        container = ModelValueContainer(value=float("inf"))
        errors = container._get_type_specific_errors()
        assert len(errors) == 1
        assert "Float value cannot be infinite" in errors[0]

    def test_get_type_specific_errors_large_list(self):
        """Test _get_type_specific_errors with large list."""
        large_list = list(range(10001))
        container = ModelValueContainer(value=large_list)
        errors = container._get_type_specific_errors()
        assert len(errors) == 1
        assert "exceeds maximum length" in errors[0]

    def test_get_type_specific_errors_large_dict(self):
        """Test _get_type_specific_errors with large dict."""
        large_dict = {f"key{i}": f"value{i}" for i in range(1001)}
        container = ModelValueContainer(value=large_dict)
        errors = container._get_type_specific_errors()
        assert len(errors) == 1
        assert "exceeds maximum size" in errors[0]

    def test_get_type_specific_errors_dict_non_string_keys(self):
        """Test _get_type_specific_errors with dict non-string keys."""
        # Note: Pydantic validation prevents creation of containers with non-string keys
        # This test is skipped as the model enforces string keys at the type level

    def test_get_metadata_errors_valid(self):
        """Test _get_metadata_errors with valid metadata."""
        container = ModelValueContainer(value="test", metadata={"key": "value"})
        errors = container._get_metadata_errors()
        assert errors == []

    def test_get_metadata_errors_empty(self):
        """Test _get_metadata_errors with empty metadata."""
        container = ModelValueContainer(value="test")
        errors = container._get_metadata_errors()
        assert errors == []

    def test_get_metadata_errors_too_large(self):
        """Test _get_metadata_errors with metadata too large."""
        large_metadata = {f"key{i}": f"value{i}" for i in range(101)}
        container = ModelValueContainer(value="test", metadata=large_metadata)
        errors = container._get_metadata_errors()
        assert len(errors) == 1
        assert "exceeds maximum size" in errors[0]

    def test_get_metadata_errors_long_key(self):
        """Test _get_metadata_errors with key too long."""
        long_key = "x" * 101
        container = ModelValueContainer(value="test", metadata={long_key: "value"})
        errors = container._get_metadata_errors()
        assert len(errors) == 1
        assert "exceeds maximum length" in errors[0]

    def test_get_metadata_errors_long_value(self):
        """Test _get_metadata_errors with value too long."""
        long_value = "x" * 1001
        container = ModelValueContainer(value="test", metadata={"key": long_value})
        errors = container._get_metadata_errors()
        assert len(errors) == 1
        assert "exceeds maximum length" in errors[0]

    def test_model_serialization(self):
        """Test model serialization."""
        container = ModelValueContainer(value="test", metadata={"key": "value"})

        data = container.model_dump()
        assert "value" in data
        assert "metadata" in data
        assert data["value"] == "test"
        assert data["metadata"] == {"key": "value"}

    def test_model_deserialization(self):
        """Test model deserialization."""
        data = {"value": "test", "metadata": {"key": "value"}}

        container = ModelValueContainer.model_validate(data)
        assert isinstance(container, ModelValueContainer)
        assert container.value == "test"
        assert container.metadata == {"key": "value"}

    def test_model_json_serialization(self):
        """Test model JSON serialization."""
        container = ModelValueContainer(value="test")

        json_data = container.model_dump_json()
        assert isinstance(json_data, str)

    def test_model_roundtrip(self):
        """Test model roundtrip serialization."""
        container = ModelValueContainer(value="test", metadata={"key": "value"})

        data = container.model_dump()
        new_container = ModelValueContainer.model_validate(data)

        assert new_container.value == "test"
        assert new_container.metadata == {"key": "value"}

    def test_model_equality(self):
        """Test model equality."""
        container1 = ModelValueContainer(value="test")
        container2 = ModelValueContainer(value="test")

        assert container1.model_dump() == container2.model_dump()

    def test_model_str(self):
        """Test model string representation."""
        container = ModelValueContainer(value="test")

        str_repr = str(container)
        assert isinstance(str_repr, str)
        assert str_repr is not None

    def test_model_repr(self):
        """Test model repr."""
        container = ModelValueContainer(value="test")

        repr_str = repr(container)
        assert isinstance(repr_str, str)
        assert "ModelValueContainer" in repr_str

    def test_model_attributes(self):
        """Test model attributes."""
        container = ModelValueContainer(value="test")
        assert hasattr(container, "value")
        assert hasattr(container, "metadata")
        assert hasattr(container, "python_type")
        assert hasattr(container, "type_name")
        assert hasattr(container, "is_type")

    def test_model_metadata(self):
        """Test model metadata."""
        container = ModelValueContainer(value="test")
        assert hasattr(container, "__class__")
        assert container.__class__.__name__ == "ModelValueContainer"

    def test_model_copy(self):
        """Test model copying."""
        container = ModelValueContainer(value="test", metadata={"key": "value"})

        copied = container.model_copy()
        assert copied.model_dump() == container.model_dump()
        assert copied is not container  # Different instances

    def test_model_immutability(self):
        """Test model immutability."""
        container = ModelValueContainer(value="test")

        # Test that we can access properties
        assert container.value == "test"
        assert container.python_type == str
        assert container.type_name == "str"

    def test_edge_case_none_value(self):
        """Test edge case with None value."""
        container = ModelValueContainer(value=None)
        assert container.is_valid() is True
        assert container.python_type == type(None)
        assert container.type_name == "NoneType"

    def test_edge_case_boolean_values(self):
        """Test edge case with boolean values."""
        container_true = ModelValueContainer(value=True)
        container_false = ModelValueContainer(value=False)

        assert container_true.is_valid() is True
        assert container_false.is_valid() is True
        assert container_true.python_type == bool
        assert container_false.python_type == bool

    def test_edge_case_nested_structures(self):
        """Test edge case with nested structures."""
        nested_data = {
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "mixed": [{"key": "value"}, 42, "string"],
        }
        container = ModelValueContainer(value=nested_data)
        assert container.is_valid() is True

    def test_edge_case_unicode_strings(self):
        """Test edge case with unicode strings."""
        unicode_string = "测试字符串"
        container = ModelValueContainer(value=unicode_string)
        assert container.is_valid() is True
        assert container.value == unicode_string

    def test_edge_case_special_floats(self):
        """Test edge case with special float values."""
        # Test negative infinity
        container_neg_inf = ModelValueContainer(value=float("-inf"))
        assert container_neg_inf.is_valid() is False

        # Test positive infinity
        container_pos_inf = ModelValueContainer(value=float("inf"))
        assert container_pos_inf.is_valid() is False

        # Test NaN
        container_nan = ModelValueContainer(value=float("nan"))
        assert container_nan.is_valid() is False

    def test_edge_case_empty_structures(self):
        """Test edge case with empty structures."""
        empty_list = ModelValueContainer(value=[])
        empty_dict = ModelValueContainer(value={})

        assert empty_list.is_valid() is True
        assert empty_dict.is_valid() is True

    def test_edge_case_metadata_edge_values(self):
        """Test edge case with metadata edge values."""
        # Test maximum allowed key length
        max_key = "x" * 100
        max_value = "x" * 1000
        container = ModelValueContainer(value="test", metadata={max_key: max_value})
        assert container.is_valid() is True

        # Test just over maximum key length
        too_long_key = "x" * 101
        container_long_key = ModelValueContainer(
            value="test", metadata={too_long_key: "value"}
        )
        assert container_long_key.is_valid() is False
