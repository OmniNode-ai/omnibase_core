"""Tests for model_value_union.py"""

import json
import math
from typing import Any

import pytest

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_value_union import ModelValueUnion


class TestModelValueUnionBasics:
    """Test basic functionality of ModelValueUnion."""

    def test_model_initialization_int(self):
        """Test model can be initialized with integer."""
        value = ModelValueUnion(value=42)
        assert value is not None
        assert value.value == 42
        assert value.value_type == "int"
        assert isinstance(value.metadata, dict)
        assert len(value.metadata) == 0

    def test_model_initialization_str(self):
        """Test model can be initialized with string."""
        value = ModelValueUnion(value="hello")
        assert value.value == "hello"
        assert value.value_type == "str"

    def test_model_initialization_bool(self):
        """Test model can be initialized with boolean."""
        value = ModelValueUnion(value=True)
        assert value.value is True
        assert value.value_type == "bool"

    def test_model_initialization_float(self):
        """Test model can be initialized with float."""
        value = ModelValueUnion(value=3.14)
        assert value.value == 3.14
        assert value.value_type == "float"

    def test_model_initialization_list(self):
        """Test model can be initialized with list."""
        value = ModelValueUnion(value=[1, 2, 3])
        assert value.value == [1, 2, 3]
        assert value.value_type == "list"

    def test_model_initialization_dict(self):
        """Test model can be initialized with dict."""
        value = ModelValueUnion(value={"key": "value"})
        assert value.value == {"key": "value"}
        assert value.value_type == "dict"

    def test_model_inheritance(self):
        """Test model inheritance."""
        from pydantic import BaseModel

        assert issubclass(ModelValueUnion, BaseModel)

    def test_model_with_metadata(self):
        """Test model initialization with metadata."""
        metadata = {"source": "test", "version": "1.0"}
        value = ModelValueUnion(value="test", metadata=metadata)

        assert value.value == "test"
        assert value.metadata == metadata


class TestTypeInference:
    """Test automatic type inference."""

    def test_infer_bool_type(self):
        """Test automatic bool type inference."""
        value = ModelValueUnion(value=True)
        assert value.value_type == "bool"

        value = ModelValueUnion(value=False)
        assert value.value_type == "bool"

    def test_infer_int_type(self):
        """Test automatic int type inference."""
        value = ModelValueUnion(value=42)
        assert value.value_type == "int"

        value = ModelValueUnion(value=0)
        assert value.value_type == "int"

        value = ModelValueUnion(value=-100)
        assert value.value_type == "int"

    def test_infer_float_type(self):
        """Test automatic float type inference."""
        value = ModelValueUnion(value=3.14)
        assert value.value_type == "float"

        value = ModelValueUnion(value=0.0)
        assert value.value_type == "float"

        value = ModelValueUnion(value=-2.5)
        assert value.value_type == "float"

    def test_infer_str_type(self):
        """Test automatic str type inference."""
        value = ModelValueUnion(value="hello")
        assert value.value_type == "str"

        value = ModelValueUnion(value="")
        assert value.value_type == "str"

    def test_infer_list_type(self):
        """Test automatic list type inference."""
        value = ModelValueUnion(value=[1, 2, 3])
        assert value.value_type == "list"

        value = ModelValueUnion(value=[])
        assert value.value_type == "list"

    def test_infer_dict_type(self):
        """Test automatic dict type inference."""
        value = ModelValueUnion(value={"key": "value"})
        assert value.value_type == "dict"

        value = ModelValueUnion(value={})
        assert value.value_type == "dict"

    def test_bool_not_confused_with_int(self):
        """Test that bool is not confused with int (bool is subclass of int)."""
        # True should be "bool", not "int"
        value = ModelValueUnion(value=True)
        assert value.value_type == "bool"

        # False should be "bool", not "int"
        value = ModelValueUnion(value=False)
        assert value.value_type == "bool"

        # But actual int should be "int"
        value = ModelValueUnion(value=1)
        assert value.value_type == "int"


class TestExplicitTypeSpecification:
    """Test explicit type specification."""

    def test_explicit_int_type(self):
        """Test explicit int type specification."""
        value = ModelValueUnion(value=42, value_type="int")
        assert value.value_type == "int"

    def test_explicit_str_type(self):
        """Test explicit str type specification."""
        value = ModelValueUnion(value="hello", value_type="str")
        assert value.value_type == "str"

    def test_explicit_bool_type(self):
        """Test explicit bool type specification."""
        value = ModelValueUnion(value=True, value_type="bool")
        assert value.value_type == "bool"

    def test_explicit_float_type(self):
        """Test explicit float type specification."""
        value = ModelValueUnion(value=3.14, value_type="float")
        assert value.value_type == "float"

    def test_explicit_list_type(self):
        """Test explicit list type specification."""
        value = ModelValueUnion(value=[1, 2, 3], value_type="list")
        assert value.value_type == "list"

    def test_explicit_dict_type(self):
        """Test explicit dict type specification."""
        value = ModelValueUnion(value={"key": "value"}, value_type="dict")
        assert value.value_type == "dict"


class TestTypeMismatchValidation:
    """Test type mismatch validation."""

    def test_mismatch_int_as_str(self):
        """Test mismatch when int provided but str type specified."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelValueUnion(value=42, value_type="str")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "type mismatch" in str(exc_info.value).lower()

    def test_mismatch_str_as_int(self):
        """Test mismatch when str provided but int type specified."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelValueUnion(value="hello", value_type="int")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "type mismatch" in str(exc_info.value).lower()

    def test_mismatch_bool_as_int(self):
        """Test mismatch when bool provided but int type specified."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelValueUnion(value=True, value_type="int")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "type mismatch" in str(exc_info.value).lower()

    def test_mismatch_list_as_dict(self):
        """Test mismatch when list provided but dict type specified."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelValueUnion(value=[1, 2, 3], value_type="dict")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "type mismatch" in str(exc_info.value).lower()


class TestFloatValidation:
    """Test float value validation."""

    def test_valid_float(self):
        """Test valid float values."""
        value = ModelValueUnion(value=3.14)
        assert value.value == 3.14
        assert value.value_type == "float"

    def test_reject_nan(self):
        """Test NaN is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelValueUnion(value=float("nan"))

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "nan" in str(exc_info.value).lower()

    def test_reject_positive_infinity(self):
        """Test positive infinity is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelValueUnion(value=float("inf"))

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "infinity" in str(exc_info.value).lower()

    def test_reject_negative_infinity(self):
        """Test negative infinity is rejected."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelValueUnion(value=float("-inf"))

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "infinity" in str(exc_info.value).lower()

    def test_zero_float(self):
        """Test zero float is valid."""
        value = ModelValueUnion(value=0.0)
        assert value.value == 0.0
        assert value.value_type == "float"

    def test_negative_float(self):
        """Test negative float is valid."""
        value = ModelValueUnion(value=-3.14)
        assert value.value == -3.14
        assert value.value_type == "float"


class TestListValidation:
    """Test list value validation."""

    def test_valid_list(self):
        """Test valid list."""
        value = ModelValueUnion(value=[1, 2, 3])
        assert value.value == [1, 2, 3]
        assert value.value_type == "list"

    def test_empty_list(self):
        """Test empty list is valid."""
        value = ModelValueUnion(value=[])
        assert value.value == []
        assert value.value_type == "list"

    def test_nested_list(self):
        """Test nested list."""
        value = ModelValueUnion(value=[[1, 2], [3, 4]])
        assert value.value == [[1, 2], [3, 4]]
        assert value.value_type == "list"

    def test_mixed_type_list(self):
        """Test list with mixed types."""
        value = ModelValueUnion(value=[1, "two", 3.0, True, {"key": "value"}])
        assert len(value.value) == 5
        assert value.value_type == "list"

    def test_large_list_within_limit(self):
        """Test large list within limit."""
        large_list = list(range(10000))  # Exactly at limit
        value = ModelValueUnion(value=large_list)
        assert value.value_type == "list"
        assert len(value.value) == 10000

    def test_large_list_exceeds_limit(self):
        """Test large list exceeding limit is rejected."""
        large_list = list(range(10001))  # Exceeds limit
        with pytest.raises(ModelOnexError) as exc_info:
            ModelValueUnion(value=large_list)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "exceeds maximum size" in str(exc_info.value).lower()


class TestDictValidation:
    """Test dict value validation."""

    def test_valid_dict(self):
        """Test valid dict."""
        value = ModelValueUnion(value={"key": "value"})
        assert value.value == {"key": "value"}
        assert value.value_type == "dict"

    def test_empty_dict(self):
        """Test empty dict is valid."""
        value = ModelValueUnion(value={})
        assert value.value == {}
        assert value.value_type == "dict"

    def test_nested_dict(self):
        """Test nested dict."""
        value = ModelValueUnion(value={"outer": {"inner": "value"}})
        assert value.value == {"outer": {"inner": "value"}}
        assert value.value_type == "dict"

    def test_dict_with_various_values(self):
        """Test dict with various value types."""
        data = {
            "str": "value",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
        }
        value = ModelValueUnion(value=data)
        assert value.value == data
        assert value.value_type == "dict"

    def test_large_dict_within_limit(self):
        """Test large dict within limit."""
        large_dict = {f"key{i}": f"value{i}" for i in range(1000)}  # Exactly at limit
        value = ModelValueUnion(value=large_dict)
        assert value.value_type == "dict"
        assert len(value.value) == 1000

    def test_large_dict_exceeds_limit(self):
        """Test large dict exceeding limit is rejected."""
        large_dict = {f"key{i}": f"value{i}" for i in range(1001)}  # Exceeds limit
        with pytest.raises(ModelOnexError) as exc_info:
            ModelValueUnion(value=large_dict)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "exceeds maximum size" in str(exc_info.value).lower()

    def test_dict_with_non_string_keys_rejected(self):
        """Test dict with non-string keys is rejected."""
        # Pydantic will reject this at the field validation level since we specify dict[str, Any]
        # This is actually good - it enforces type safety before our custom validators even run
        from pydantic import ValidationError

        invalid_dict = {1: "value1", 2: "value2"}
        with pytest.raises(ValidationError) as exc_info:
            ModelValueUnion(value=invalid_dict)

        # Verify Pydantic caught the string key violation
        error_str = str(exc_info.value).lower()
        assert "string" in error_str or "key" in error_str


class TestHelperMethods:
    """Test helper methods."""

    def test_get_value_int(self):
        """Test get_value with int."""
        value = ModelValueUnion(value=42)
        assert value.get_value() == 42

    def test_get_value_str(self):
        """Test get_value with str."""
        value = ModelValueUnion(value="hello")
        assert value.get_value() == "hello"

    def test_get_value_list(self):
        """Test get_value with list."""
        value = ModelValueUnion(value=[1, 2, 3])
        assert value.get_value() == [1, 2, 3]

    def test_get_python_type_int(self):
        """Test get_python_type with int."""
        value = ModelValueUnion(value=42)
        assert value.get_python_type() == int

    def test_get_python_type_str(self):
        """Test get_python_type with str."""
        value = ModelValueUnion(value="hello")
        assert value.get_python_type() == str

    def test_get_python_type_bool(self):
        """Test get_python_type with bool."""
        value = ModelValueUnion(value=True)
        assert value.get_python_type() == bool

    def test_get_python_type_float(self):
        """Test get_python_type with float."""
        value = ModelValueUnion(value=3.14)
        assert value.get_python_type() == float

    def test_get_python_type_list(self):
        """Test get_python_type with list."""
        value = ModelValueUnion(value=[1, 2, 3])
        assert value.get_python_type() == list

    def test_get_python_type_dict(self):
        """Test get_python_type with dict."""
        value = ModelValueUnion(value={"key": "value"})
        assert value.get_python_type() == dict

    def test_as_dict(self):
        """Test as_dict method."""
        value = ModelValueUnion(value=42, metadata={"source": "test"})
        data = value.as_dict()

        assert data["value"] == 42
        assert data["value_type"] == "int"
        assert data["metadata"] == {"source": "test"}

    def test_is_primitive_true(self):
        """Test is_primitive returns True for primitives."""
        assert ModelValueUnion(value=42).is_primitive() is True
        assert ModelValueUnion(value="hello").is_primitive() is True
        assert ModelValueUnion(value=True).is_primitive() is True
        assert ModelValueUnion(value=3.14).is_primitive() is True

    def test_is_primitive_false(self):
        """Test is_primitive returns False for collections."""
        assert ModelValueUnion(value=[1, 2, 3]).is_primitive() is False
        assert ModelValueUnion(value={"key": "value"}).is_primitive() is False

    def test_is_collection_true(self):
        """Test is_collection returns True for collections."""
        assert ModelValueUnion(value=[1, 2, 3]).is_collection() is True
        assert ModelValueUnion(value={"key": "value"}).is_collection() is True

    def test_is_collection_false(self):
        """Test is_collection returns False for primitives."""
        assert ModelValueUnion(value=42).is_collection() is False
        assert ModelValueUnion(value="hello").is_collection() is False
        assert ModelValueUnion(value=True).is_collection() is False
        assert ModelValueUnion(value=3.14).is_collection() is False


class TestSerialization:
    """Test model serialization and deserialization."""

    def test_model_dump(self):
        """Test model_dump."""
        value = ModelValueUnion(value=42, metadata={"key": "value"})
        data = value.model_dump()

        assert "value" in data
        assert "value_type" in data
        assert "metadata" in data
        assert data["value"] == 42
        assert data["value_type"] == "int"
        assert data["metadata"] == {"key": "value"}

    def test_model_validate(self):
        """Test model_validate (deserialization)."""
        data = {"value": 42, "value_type": "int", "metadata": {"key": "value"}}
        value = ModelValueUnion.model_validate(data)

        assert isinstance(value, ModelValueUnion)
        assert value.value == 42
        assert value.value_type == "int"
        assert value.metadata == {"key": "value"}

    def test_model_dump_json(self):
        """Test model_dump_json."""
        value = ModelValueUnion(value=42)
        json_data = value.model_dump_json()

        assert isinstance(json_data, str)
        parsed = json.loads(json_data)
        assert parsed["value"] == 42
        assert parsed["value_type"] == "int"

    def test_model_roundtrip(self):
        """Test roundtrip serialization."""
        original = ModelValueUnion(value="hello", metadata={"source": "test"})

        data = original.model_dump()
        restored = ModelValueUnion.model_validate(data)

        assert restored.value == "hello"
        assert restored.value_type == "str"
        assert restored.metadata == {"source": "test"}

    def test_model_roundtrip_complex(self):
        """Test roundtrip with complex types."""
        complex_value = {
            "nested": {"deep": "value"},
            "list": [1, 2, 3],
            "mixed": [{"key": "value"}, 42, "string"],
        }
        original = ModelValueUnion(value=complex_value)

        data = original.model_dump()
        restored = ModelValueUnion.model_validate(data)

        assert restored.value == complex_value
        assert restored.value_type == "dict"


class TestEdgeCases:
    """Test edge cases and special values."""

    def test_empty_string(self):
        """Test empty string is valid."""
        value = ModelValueUnion(value="")
        assert value.value == ""
        assert value.value_type == "str"

    def test_zero_integer(self):
        """Test zero integer."""
        value = ModelValueUnion(value=0)
        assert value.value == 0
        assert value.value_type == "int"

    def test_zero_float(self):
        """Test zero float."""
        value = ModelValueUnion(value=0.0)
        assert value.value == 0.0
        assert value.value_type == "float"

    def test_negative_integer(self):
        """Test negative integer."""
        value = ModelValueUnion(value=-42)
        assert value.value == -42
        assert value.value_type == "int"

    def test_negative_float(self):
        """Test negative float."""
        value = ModelValueUnion(value=-3.14)
        assert value.value == -3.14
        assert value.value_type == "float"

    def test_unicode_string(self):
        """Test unicode string."""
        unicode_str = "测试字符串 🎉"
        value = ModelValueUnion(value=unicode_str)
        assert value.value == unicode_str
        assert value.value_type == "str"

    def test_multiline_string(self):
        """Test multiline string."""
        multiline = "line1\nline2\nline3"
        value = ModelValueUnion(value=multiline)
        assert value.value == multiline
        assert value.value_type == "str"

    def test_very_large_integer(self):
        """Test very large integer."""
        large_int = 10**100
        value = ModelValueUnion(value=large_int)
        assert value.value == large_int
        assert value.value_type == "int"

    def test_very_small_float(self):
        """Test very small float."""
        small_float = 1e-100
        value = ModelValueUnion(value=small_float)
        assert value.value == small_float
        assert value.value_type == "float"

    def test_empty_nested_structures(self):
        """Test empty nested structures."""
        value = ModelValueUnion(value={"empty_list": [], "empty_dict": {}})
        assert value.value == {"empty_list": [], "empty_dict": {}}
        assert value.value_type == "dict"


class TestStringRepresentation:
    """Test string representation methods."""

    def test_str(self):
        """Test __str__ method."""
        value = ModelValueUnion(value=42)
        str_repr = str(value)

        assert isinstance(str_repr, str)
        assert "int" in str_repr
        assert "42" in str_repr

    def test_repr(self):
        """Test __repr__ method."""
        value = ModelValueUnion(value="hello")
        repr_str = repr(value)

        assert isinstance(repr_str, str)
        assert "ModelValueUnion" in repr_str
        assert "str" in repr_str
        assert "hello" in repr_str


class TestModelOperations:
    """Test model operations like copy, equality."""

    def test_model_copy(self):
        """Test model copying."""
        original = ModelValueUnion(value=42, metadata={"key": "value"})
        copied = original.model_copy()

        assert copied.value == original.value
        assert copied.value_type == original.value_type
        assert copied.metadata == original.metadata
        assert copied is not original  # Different instances

    def test_model_attributes(self):
        """Test model has expected attributes."""
        value = ModelValueUnion(value=42)

        assert hasattr(value, "value")
        assert hasattr(value, "value_type")
        assert hasattr(value, "metadata")
        assert hasattr(value, "get_value")
        assert hasattr(value, "get_python_type")
        assert hasattr(value, "as_dict")
        assert hasattr(value, "is_primitive")
        assert hasattr(value, "is_collection")

    def test_model_metadata_attribute(self):
        """Test model metadata attribute."""
        value = ModelValueUnion(value=42)
        assert hasattr(value, "__class__")
        assert value.__class__.__name__ == "ModelValueUnion"


class TestUnsupportedTypes:
    """Test handling of unsupported types."""

    def test_unsupported_type_raises_error(self):
        """Test that unsupported types raise error."""

        class CustomClass:
            pass

        with pytest.raises(ModelOnexError) as exc_info:
            ModelValueUnion(value=CustomClass())

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "unsupported" in str(exc_info.value).lower()


class TestTypeConsistency:
    """Test type consistency across operations."""

    def test_bool_int_distinction(self):
        """Test that bool and int are properly distinguished."""
        bool_value = ModelValueUnion(value=True)
        int_value = ModelValueUnion(value=1)

        assert bool_value.value_type == "bool"
        assert int_value.value_type == "int"
        assert bool_value.get_python_type() == bool
        assert int_value.get_python_type() == int

    def test_int_float_distinction(self):
        """Test that int and float are properly distinguished."""
        int_value = ModelValueUnion(value=42)
        float_value = ModelValueUnion(value=42.0)

        assert int_value.value_type == "int"
        assert float_value.value_type == "float"
        assert int_value.get_python_type() == int
        assert float_value.get_python_type() == float
