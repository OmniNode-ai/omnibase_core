# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for model_policy_value.py - SECURITY-CRITICAL"""

import json

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.security.model_policy_value import ModelPolicyValue

# Default version for test instances - required field after removing default_factory
DEFAULT_VERSION = ModelSemVer(major=1, minor=0, patch=0)


@pytest.mark.unit
class TestModelPolicyValueBasics:
    """Test basic functionality of ModelPolicyValue."""

    def test_model_initialization_none(self):
        """Test model can be initialized with None (CRITICAL for optional policies)."""
        value = ModelPolicyValue(value=None)
        assert value is not None
        assert value.value is None
        assert value.value_type == "none"
        assert value.is_sensitive is False
        assert isinstance(value.metadata, dict)
        assert len(value.metadata) == 0

    def test_model_initialization_int(self):
        """Test model can be initialized with integer."""
        value = ModelPolicyValue(value=42)
        assert value.value == 42
        assert value.value_type == "int"
        assert value.is_sensitive is False

    def test_model_initialization_str(self):
        """Test model can be initialized with string."""
        value = ModelPolicyValue(value="hello")
        assert value.value == "hello"
        assert value.value_type == "str"
        assert value.is_sensitive is False

    def test_model_initialization_bool(self):
        """Test model can be initialized with boolean."""
        value = ModelPolicyValue(value=True)
        assert value.value is True
        assert value.value_type == "bool"
        assert value.is_sensitive is False

    def test_model_initialization_float(self):
        """Test model can be initialized with float."""
        value = ModelPolicyValue(value=3.14)
        assert value.value == 3.14
        assert value.value_type == "float"
        assert value.is_sensitive is False

    def test_model_initialization_list(self):
        """Test model can be initialized with list."""
        value = ModelPolicyValue(value=[1, 2, 3])
        assert value.value == [1, 2, 3]
        assert value.value_type == "list"
        assert value.is_sensitive is False

    def test_model_initialization_dict(self):
        """Test model can be initialized with dict."""
        value = ModelPolicyValue(value={"key": "value"})
        assert value.value == {"key": "value"}
        assert value.value_type == "dict"
        assert value.is_sensitive is False

    def test_model_inheritance(self):
        """Test model inheritance."""
        from pydantic import BaseModel

        assert issubclass(ModelPolicyValue, BaseModel)

    def test_model_with_metadata(self):
        """Test model initialization with metadata."""
        metadata = {"source": "test", "version": "1.0"}
        value = ModelPolicyValue(value="test", metadata=metadata)

        assert value.value == "test"
        assert value.metadata == metadata
        assert value.is_sensitive is False


@pytest.mark.unit
class TestSensitiveDataMarking:
    """Test sensitive data marking functionality (SECURITY-CRITICAL)."""

    def test_sensitive_flag_default_false(self):
        """Test is_sensitive defaults to False."""
        value = ModelPolicyValue(value="password")
        assert value.is_sensitive is False

    def test_sensitive_flag_explicit_true(self):
        """Test is_sensitive can be set to True."""
        value = ModelPolicyValue(value="password123", is_sensitive=True)
        assert value.is_sensitive is True
        assert value.value == "password123"

    def test_sensitive_flag_explicit_false(self):
        """Test is_sensitive can be explicitly set to False."""
        value = ModelPolicyValue(value="public_data", is_sensitive=False)
        assert value.is_sensitive is False

    def test_sensitive_with_string(self):
        """Test sensitive marking with string (common use case)."""
        secret = ModelPolicyValue(value="api_key_12345", is_sensitive=True)
        assert secret.is_sensitive is True
        assert secret.value_type == "str"

    def test_sensitive_with_dict(self):
        """Test sensitive marking with dict (credentials, config)."""
        credentials = ModelPolicyValue(
            value={"username": "admin", "password": "secret"},
            is_sensitive=True,
        )
        assert credentials.is_sensitive is True
        assert credentials.value_type == "dict"

    def test_sensitive_with_list(self):
        """Test sensitive marking with list (token list, key list)."""
        tokens = ModelPolicyValue(
            value=["token1", "token2", "token3"],
            is_sensitive=True,
        )
        assert tokens.is_sensitive is True
        assert tokens.value_type == "list"

    def test_sensitive_with_none(self):
        """Test sensitive marking with None."""
        value = ModelPolicyValue(value=None, is_sensitive=True)
        assert value.is_sensitive is True
        assert value.value_type == "none"

    def test_sensitive_flag_in_str_representation(self):
        """Test sensitive values are masked in __str__."""
        sensitive = ModelPolicyValue(value="secret123", is_sensitive=True)
        str_repr = str(sensitive)

        assert "[SENSITIVE]" in str_repr
        assert "secret123" not in str_repr

    def test_sensitive_flag_in_repr_representation(self):
        """Test sensitive values are masked in __repr__."""
        sensitive = ModelPolicyValue(value="secret123", is_sensitive=True)
        repr_str = repr(sensitive)

        assert "[REDACTED]" in repr_str
        assert "secret123" not in repr_str
        assert "is_sensitive=True" in repr_str

    def test_non_sensitive_in_str_representation(self):
        """Test non-sensitive values are shown in __str__."""
        public = ModelPolicyValue(value="public_data", is_sensitive=False)
        str_repr = str(public)

        assert "public_data" in str_repr
        assert "[SENSITIVE]" not in str_repr


@pytest.mark.unit
class TestTypeInference:
    """Test automatic type inference."""

    def test_infer_none_type(self):
        """Test automatic None type inference (CRITICAL)."""
        value = ModelPolicyValue(value=None)
        assert value.value_type == "none"

    def test_infer_bool_type(self):
        """Test automatic bool type inference."""
        value = ModelPolicyValue(value=True)
        assert value.value_type == "bool"

        value = ModelPolicyValue(value=False)
        assert value.value_type == "bool"

    def test_infer_int_type(self):
        """Test automatic int type inference."""
        value = ModelPolicyValue(value=42)
        assert value.value_type == "int"

        value = ModelPolicyValue(value=0)
        assert value.value_type == "int"

        value = ModelPolicyValue(value=-100)
        assert value.value_type == "int"

    def test_infer_float_type(self):
        """Test automatic float type inference."""
        value = ModelPolicyValue(value=3.14)
        assert value.value_type == "float"

        value = ModelPolicyValue(value=0.0)
        assert value.value_type == "float"

        value = ModelPolicyValue(value=-2.5)
        assert value.value_type == "float"

    def test_infer_str_type(self):
        """Test automatic str type inference."""
        value = ModelPolicyValue(value="hello")
        assert value.value_type == "str"

        value = ModelPolicyValue(value="")
        assert value.value_type == "str"

    def test_infer_list_type(self):
        """Test automatic list type inference."""
        value = ModelPolicyValue(value=[1, 2, 3])
        assert value.value_type == "list"

        value = ModelPolicyValue(value=[])
        assert value.value_type == "list"

    def test_infer_dict_type(self):
        """Test automatic dict type inference."""
        value = ModelPolicyValue(value={"key": "value"})
        assert value.value_type == "dict"

        value = ModelPolicyValue(value={})
        assert value.value_type == "dict"

    def test_bool_not_confused_with_int(self):
        """Test that bool is not confused with int (bool is subclass of int)."""
        # True should be "bool", not "int"
        value = ModelPolicyValue(value=True)
        assert value.value_type == "bool"

        # False should be "bool", not "int"
        value = ModelPolicyValue(value=False)
        assert value.value_type == "bool"

        # But actual int should be "int"
        value = ModelPolicyValue(value=1)
        assert value.value_type == "int"


@pytest.mark.unit
class TestExplicitTypeSpecification:
    """Test explicit type specification."""

    def test_explicit_none_type(self):
        """Test explicit none type specification."""
        value = ModelPolicyValue(value=None, value_type="none")
        assert value.value_type == "none"

    def test_explicit_int_type(self):
        """Test explicit int type specification."""
        value = ModelPolicyValue(value=42, value_type="int")
        assert value.value_type == "int"

    def test_explicit_str_type(self):
        """Test explicit str type specification."""
        value = ModelPolicyValue(value="hello", value_type="str")
        assert value.value_type == "str"

    def test_explicit_bool_type(self):
        """Test explicit bool type specification."""
        value = ModelPolicyValue(value=True, value_type="bool")
        assert value.value_type == "bool"

    def test_explicit_float_type(self):
        """Test explicit float type specification."""
        value = ModelPolicyValue(value=3.14, value_type="float")
        assert value.value_type == "float"

    def test_explicit_list_type(self):
        """Test explicit list type specification."""
        value = ModelPolicyValue(value=[1, 2, 3], value_type="list")
        assert value.value_type == "list"

    def test_explicit_dict_type(self):
        """Test explicit dict type specification."""
        value = ModelPolicyValue(value={"key": "value"}, value_type="dict")
        assert value.value_type == "dict"


@pytest.mark.unit
class TestTypeMismatchValidation:
    """Test type mismatch validation."""

    def test_mismatch_int_as_str(self):
        """Test mismatch when int provided but str type specified."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelPolicyValue(value=42, value_type="str")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "type mismatch" in str(exc_info.value).lower()

    def test_mismatch_str_as_int(self):
        """Test mismatch when str provided but int type specified."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelPolicyValue(value="hello", value_type="int")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "type mismatch" in str(exc_info.value).lower()

    def test_mismatch_bool_as_int(self):
        """Test mismatch when bool provided but int type specified."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelPolicyValue(value=True, value_type="int")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "type mismatch" in str(exc_info.value).lower()

    def test_mismatch_none_as_str(self):
        """Test mismatch when None provided but str type specified."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelPolicyValue(value=None, value_type="str")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "type mismatch" in str(exc_info.value).lower()

    def test_mismatch_list_as_dict(self):
        """Test mismatch when list provided but dict type specified."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelPolicyValue(value=[1, 2, 3], value_type="dict")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "type mismatch" in str(exc_info.value).lower()


@pytest.mark.unit
class TestNoneHandling:
    """Test None value handling (CRITICAL for optional policies)."""

    def test_none_value(self):
        """Test None value is properly handled."""
        value = ModelPolicyValue(value=None)
        assert value.value is None
        assert value.value_type == "none"

    def test_is_none_true(self):
        """Test is_none() returns True for None value."""
        value = ModelPolicyValue(value=None)
        assert value.is_none() is True

    def test_is_none_false_for_int(self):
        """Test is_none() returns False for non-None value."""
        value = ModelPolicyValue(value=42)
        assert value.is_none() is False

    def test_is_none_false_for_str(self):
        """Test is_none() returns False for string."""
        value = ModelPolicyValue(value="test")
        assert value.is_none() is False

    def test_is_none_false_for_empty_string(self):
        """Test is_none() returns False for empty string."""
        value = ModelPolicyValue(value="")
        assert value.is_none() is False

    def test_is_none_false_for_zero(self):
        """Test is_none() returns False for zero."""
        value = ModelPolicyValue(value=0)
        assert value.is_none() is False

    def test_is_none_false_for_false(self):
        """Test is_none() returns False for False boolean."""
        value = ModelPolicyValue(value=False)
        assert value.is_none() is False

    def test_is_none_false_for_empty_list(self):
        """Test is_none() returns False for empty list."""
        value = ModelPolicyValue(value=[])
        assert value.is_none() is False

    def test_is_none_false_for_empty_dict(self):
        """Test is_none() returns False for empty dict."""
        value = ModelPolicyValue(value={})
        assert value.is_none() is False

    def test_get_python_type_for_none(self):
        """Test get_python_type returns type(None) for None value."""
        value = ModelPolicyValue(value=None)
        assert value.get_python_type() == type(None)


@pytest.mark.unit
class TestFloatValidation:
    """Test float value validation (SECURITY)."""

    def test_valid_float(self):
        """Test valid float values."""
        value = ModelPolicyValue(value=3.14)
        assert value.value == 3.14
        assert value.value_type == "float"

    def test_reject_nan(self):
        """Test NaN is rejected (SECURITY - prevents calculation errors)."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelPolicyValue(value=float("nan"))

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "nan" in str(exc_info.value).lower()

    def test_reject_positive_infinity(self):
        """Test positive infinity is rejected (SECURITY)."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelPolicyValue(value=float("inf"))

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "infinity" in str(exc_info.value).lower()

    def test_reject_negative_infinity(self):
        """Test negative infinity is rejected (SECURITY)."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelPolicyValue(value=float("-inf"))

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "infinity" in str(exc_info.value).lower()

    def test_zero_float(self):
        """Test zero float is valid."""
        value = ModelPolicyValue(value=0.0)
        assert value.value == 0.0
        assert value.value_type == "float"

    def test_negative_float(self):
        """Test negative float is valid."""
        value = ModelPolicyValue(value=-3.14)
        assert value.value == -3.14
        assert value.value_type == "float"


@pytest.mark.unit
class TestListValidation:
    """Test list value validation (SECURITY - DoS protection)."""

    def test_valid_list(self):
        """Test valid list."""
        value = ModelPolicyValue(value=[1, 2, 3])
        assert value.value == [1, 2, 3]
        assert value.value_type == "list"

    def test_empty_list(self):
        """Test empty list is valid."""
        value = ModelPolicyValue(value=[])
        assert value.value == []
        assert value.value_type == "list"

    def test_nested_list(self):
        """Test nested list."""
        value = ModelPolicyValue(value=[[1, 2], [3, 4]])
        assert value.value == [[1, 2], [3, 4]]
        assert value.value_type == "list"

    def test_mixed_type_list(self):
        """Test list with mixed types."""
        value = ModelPolicyValue(value=[1, "two", 3.0, True, {"key": "value"}])
        assert len(value.value) == 5
        assert value.value_type == "list"

    def test_large_list_within_limit(self):
        """Test large list within limit."""
        large_list = list(range(10000))  # Exactly at limit
        value = ModelPolicyValue(value=large_list)
        assert value.value_type == "list"
        assert len(value.value) == 10000

    def test_large_list_exceeds_limit(self):
        """Test large list exceeding limit is rejected (SECURITY - DoS protection)."""
        large_list = list(range(10001))  # Exceeds limit
        with pytest.raises(ModelOnexError) as exc_info:
            ModelPolicyValue(value=large_list)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "exceeds maximum size" in str(exc_info.value).lower()


@pytest.mark.unit
class TestDictValidation:
    """Test dict value validation (SECURITY - DoS protection)."""

    def test_valid_dict(self):
        """Test valid dict."""
        value = ModelPolicyValue(value={"key": "value"})
        assert value.value == {"key": "value"}
        assert value.value_type == "dict"

    def test_empty_dict(self):
        """Test empty dict is valid."""
        value = ModelPolicyValue(value={})
        assert value.value == {}
        assert value.value_type == "dict"

    def test_nested_dict(self):
        """Test nested dict."""
        value = ModelPolicyValue(value={"outer": {"inner": "value"}})
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
        value = ModelPolicyValue(value=data)
        assert value.value == data
        assert value.value_type == "dict"

    def test_large_dict_within_limit(self):
        """Test large dict within limit."""
        large_dict = {f"key{i}": f"value{i}" for i in range(1000)}  # Exactly at limit
        value = ModelPolicyValue(value=large_dict)
        assert value.value_type == "dict"
        assert len(value.value) == 1000

    def test_large_dict_exceeds_limit(self):
        """Test large dict exceeding limit is rejected (SECURITY - DoS protection)."""
        large_dict = {f"key{i}": f"value{i}" for i in range(1001)}  # Exceeds limit
        with pytest.raises(ModelOnexError) as exc_info:
            ModelPolicyValue(value=large_dict)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "exceeds maximum size" in str(exc_info.value).lower()

    def test_dict_with_non_string_keys_rejected(self):
        """Test dict with non-string keys is rejected (SECURITY)."""
        # Pydantic will reject this at the field validation level since we specify dict[str, Any]
        from pydantic import ValidationError

        invalid_dict = {1: "value1", 2: "value2"}
        with pytest.raises(ValidationError) as exc_info:
            ModelPolicyValue(value=invalid_dict)

        # Verify Pydantic caught the string key violation
        error_str = str(exc_info.value).lower()
        assert "string" in error_str or "key" in error_str


@pytest.mark.unit
class TestHelperMethods:
    """Test helper methods."""

    def test_get_value_none(self):
        """Test get_value with None."""
        value = ModelPolicyValue(value=None)
        assert value.get_value() is None

    def test_get_value_int(self):
        """Test get_value with int."""
        value = ModelPolicyValue(value=42)
        assert value.get_value() == 42

    def test_get_value_str(self):
        """Test get_value with str."""
        value = ModelPolicyValue(value="hello")
        assert value.get_value() == "hello"

    def test_get_value_list(self):
        """Test get_value with list."""
        value = ModelPolicyValue(value=[1, 2, 3])
        assert value.get_value() == [1, 2, 3]

    def test_get_type(self):
        """Test get_type method."""
        value = ModelPolicyValue(value="test")
        assert value.get_type() == "str"

        value = ModelPolicyValue(value=None)
        assert value.get_type() == "none"

    def test_get_python_type_int(self):
        """Test get_python_type with int."""
        value = ModelPolicyValue(value=42)
        assert value.get_python_type() == int

    def test_get_python_type_str(self):
        """Test get_python_type with str."""
        value = ModelPolicyValue(value="hello")
        assert value.get_python_type() == str

    def test_get_python_type_bool(self):
        """Test get_python_type with bool."""
        value = ModelPolicyValue(value=True)
        assert value.get_python_type() == bool

    def test_get_python_type_float(self):
        """Test get_python_type with float."""
        value = ModelPolicyValue(value=3.14)
        assert value.get_python_type() == float

    def test_get_python_type_list(self):
        """Test get_python_type with list."""
        value = ModelPolicyValue(value=[1, 2, 3])
        assert value.get_python_type() == list

    def test_get_python_type_dict(self):
        """Test get_python_type with dict."""
        value = ModelPolicyValue(value={"key": "value"})
        assert value.get_python_type() == dict

    def test_as_dict(self):
        """Test as_dict method."""
        value = ModelPolicyValue(
            value=42,
            is_sensitive=True,
            metadata={"source": "test"},
        )
        data = value.as_dict()

        assert data["value"] == 42
        assert data["value_type"] == "int"
        assert data["is_sensitive"] is True
        assert data["metadata"] == {"source": "test"}

    def test_as_dict_with_none(self):
        """Test as_dict with None value."""
        value = ModelPolicyValue(value=None)
        data = value.as_dict()

        assert data["value"] is None
        assert data["value_type"] == "none"
        assert data["is_sensitive"] is False

    def test_is_primitive_true(self):
        """Test is_primitive returns True for primitives."""
        assert ModelPolicyValue(value=None).is_primitive() is True
        assert ModelPolicyValue(value=42).is_primitive() is True
        assert ModelPolicyValue(value="hello").is_primitive() is True
        assert ModelPolicyValue(value=True).is_primitive() is True
        assert ModelPolicyValue(value=3.14).is_primitive() is True

    def test_is_primitive_false(self):
        """Test is_primitive returns False for collections."""
        assert ModelPolicyValue(value=[1, 2, 3]).is_primitive() is False
        assert ModelPolicyValue(value={"key": "value"}).is_primitive() is False

    def test_is_collection_true(self):
        """Test is_collection returns True for collections."""
        assert ModelPolicyValue(value=[1, 2, 3]).is_collection() is True
        assert ModelPolicyValue(value={"key": "value"}).is_collection() is True

    def test_is_collection_false(self):
        """Test is_collection returns False for primitives."""
        assert ModelPolicyValue(value=None).is_collection() is False
        assert ModelPolicyValue(value=42).is_collection() is False
        assert ModelPolicyValue(value="hello").is_collection() is False
        assert ModelPolicyValue(value=True).is_collection() is False
        assert ModelPolicyValue(value=3.14).is_collection() is False


@pytest.mark.unit
class TestSerialization:
    """Test model serialization and deserialization."""

    def test_model_dump(self):
        """Test model_dump."""
        value = ModelPolicyValue(
            value=42,
            is_sensitive=True,
            metadata={"key": "value"},
        )
        data = value.model_dump()

        assert "value" in data
        assert "value_type" in data
        assert "is_sensitive" in data
        assert "metadata" in data
        assert data["value"] == 42
        assert data["value_type"] == "int"
        assert data["is_sensitive"] is True
        assert data["metadata"] == {"key": "value"}

    def test_model_dump_with_none(self):
        """Test model_dump with None value."""
        value = ModelPolicyValue(value=None)
        data = value.model_dump()

        assert data["value"] is None
        assert data["value_type"] == "none"
        assert data["is_sensitive"] is False

    def test_model_validate(self):
        """Test model_validate (deserialization)."""
        data = {
            "value": 42,
            "value_type": "int",
            "is_sensitive": True,
            "metadata": {"key": "value"},
        }
        value = ModelPolicyValue.model_validate(data)

        assert isinstance(value, ModelPolicyValue)
        assert value.value == 42
        assert value.value_type == "int"
        assert value.is_sensitive is True
        assert value.metadata == {"key": "value"}

    def test_model_dump_json(self):
        """Test model_dump_json."""
        value = ModelPolicyValue(value=42, is_sensitive=True)
        json_data = value.model_dump_json()

        assert isinstance(json_data, str)
        parsed = json.loads(json_data)
        assert parsed["value"] == 42
        assert parsed["value_type"] == "int"
        assert parsed["is_sensitive"] is True

    def test_model_roundtrip(self):
        """Test roundtrip serialization."""
        original = ModelPolicyValue(
            value="hello",
            is_sensitive=True,
            metadata={"source": "test"},
        )

        data = original.model_dump()
        restored = ModelPolicyValue.model_validate(data)

        assert restored.value == "hello"
        assert restored.value_type == "str"
        assert restored.is_sensitive is True
        assert restored.metadata == {"source": "test"}

    def test_model_roundtrip_none(self):
        """Test roundtrip with None value."""
        original = ModelPolicyValue(value=None, is_sensitive=False)

        data = original.model_dump()
        restored = ModelPolicyValue.model_validate(data)

        assert restored.value is None
        assert restored.value_type == "none"
        assert restored.is_sensitive is False

    def test_model_roundtrip_complex(self):
        """Test roundtrip with complex types."""
        complex_value = {
            "nested": {"deep": "value"},
            "list": [1, 2, 3],
            "mixed": [{"key": "value"}, 42, "string"],
        }
        original = ModelPolicyValue(value=complex_value, is_sensitive=True)

        data = original.model_dump()
        restored = ModelPolicyValue.model_validate(data)

        assert restored.value == complex_value
        assert restored.value_type == "dict"
        assert restored.is_sensitive is True


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and special values."""

    def test_empty_string(self):
        """Test empty string is valid."""
        value = ModelPolicyValue(value="")
        assert value.value == ""
        assert value.value_type == "str"

    def test_zero_integer(self):
        """Test zero integer."""
        value = ModelPolicyValue(value=0)
        assert value.value == 0
        assert value.value_type == "int"

    def test_zero_float(self):
        """Test zero float."""
        value = ModelPolicyValue(value=0.0)
        assert value.value == 0.0
        assert value.value_type == "float"

    def test_negative_integer(self):
        """Test negative integer."""
        value = ModelPolicyValue(value=-42)
        assert value.value == -42
        assert value.value_type == "int"

    def test_negative_float(self):
        """Test negative float."""
        value = ModelPolicyValue(value=-3.14)
        assert value.value == -3.14
        assert value.value_type == "float"

    def test_unicode_string(self):
        """Test unicode string."""
        unicode_str = "测试字符串 🎉"
        value = ModelPolicyValue(value=unicode_str)
        assert value.value == unicode_str
        assert value.value_type == "str"

    def test_multiline_string(self):
        """Test multiline string."""
        multiline = "line1\nline2\nline3"
        value = ModelPolicyValue(value=multiline)
        assert value.value == multiline
        assert value.value_type == "str"

    def test_very_large_integer(self):
        """Test very large integer."""
        large_int = 10**100
        value = ModelPolicyValue(value=large_int)
        assert value.value == large_int
        assert value.value_type == "int"

    def test_very_small_float(self):
        """Test very small float."""
        small_float = 1e-100
        value = ModelPolicyValue(value=small_float)
        assert value.value == small_float
        assert value.value_type == "float"

    def test_empty_nested_structures(self):
        """Test empty nested structures."""
        value = ModelPolicyValue(value={"empty_list": [], "empty_dict": {}})
        assert value.value == {"empty_list": [], "empty_dict": {}}
        assert value.value_type == "dict"


@pytest.mark.unit
class TestStringRepresentation:
    """Test string representation methods."""

    def test_str_non_sensitive(self):
        """Test __str__ method for non-sensitive values."""
        value = ModelPolicyValue(value=42, is_sensitive=False)
        str_repr = str(value)

        assert isinstance(str_repr, str)
        assert "int" in str_repr
        assert "42" in str_repr

    def test_str_sensitive(self):
        """Test __str__ method masks sensitive values."""
        value = ModelPolicyValue(value="password123", is_sensitive=True)
        str_repr = str(value)

        assert isinstance(str_repr, str)
        assert "[SENSITIVE]" in str_repr
        assert "password123" not in str_repr

    def test_repr_non_sensitive(self):
        """Test __repr__ method for non-sensitive values."""
        value = ModelPolicyValue(value="hello", is_sensitive=False)
        repr_str = repr(value)

        assert isinstance(repr_str, str)
        assert "ModelPolicyValue" in repr_str
        assert "str" in repr_str
        assert "hello" in repr_str
        assert "is_sensitive=False" in repr_str

    def test_repr_sensitive(self):
        """Test __repr__ method masks sensitive values."""
        value = ModelPolicyValue(value="password123", is_sensitive=True)
        repr_str = repr(value)

        assert isinstance(repr_str, str)
        assert "ModelPolicyValue" in repr_str
        assert "[REDACTED]" in repr_str
        assert "password123" not in repr_str
        assert "is_sensitive=True" in repr_str


@pytest.mark.unit
class TestModelOperations:
    """Test model operations like copy, equality."""

    def test_model_copy(self):
        """Test model copying."""
        original = ModelPolicyValue(
            value=42,
            is_sensitive=True,
            metadata={"key": "value"},
        )
        copied = original.model_copy()

        assert copied.value == original.value
        assert copied.value_type == original.value_type
        assert copied.is_sensitive == original.is_sensitive
        assert copied.metadata == original.metadata
        assert copied is not original  # Different instances

    def test_model_copy_with_none(self):
        """Test model copying with None value."""
        original = ModelPolicyValue(value=None)
        copied = original.model_copy()

        assert copied.value is None
        assert copied.value_type == "none"
        assert copied is not original

    def test_model_attributes(self):
        """Test model has expected attributes."""
        value = ModelPolicyValue(value=42)

        assert hasattr(value, "value")
        assert hasattr(value, "value_type")
        assert hasattr(value, "is_sensitive")
        assert hasattr(value, "metadata")
        assert hasattr(value, "get_value")
        assert hasattr(value, "get_type")
        assert hasattr(value, "is_none")
        assert hasattr(value, "get_python_type")
        assert hasattr(value, "as_dict")
        assert hasattr(value, "is_primitive")
        assert hasattr(value, "is_collection")

    def test_model_metadata_attribute(self):
        """Test model metadata attribute."""
        value = ModelPolicyValue(value=42)
        assert hasattr(value, "__class__")
        assert value.__class__.__name__ == "ModelPolicyValue"


@pytest.mark.unit
class TestUnsupportedTypes:
    """Test handling of unsupported types."""

    def test_unsupported_type_raises_error(self):
        """Test that unsupported types raise error."""

        class CustomClass:
            pass

        with pytest.raises(ModelOnexError) as exc_info:
            ModelPolicyValue(value=CustomClass())

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "unsupported" in str(exc_info.value).lower()


@pytest.mark.unit
class TestTypeConsistency:
    """Test type consistency across operations."""

    def test_bool_int_distinction(self):
        """Test that bool and int are properly distinguished."""
        bool_value = ModelPolicyValue(value=True)
        int_value = ModelPolicyValue(value=1)

        assert bool_value.value_type == "bool"
        assert int_value.value_type == "int"
        assert bool_value.get_python_type() == bool
        assert int_value.get_python_type() == int

    def test_int_float_distinction(self):
        """Test that int and float are properly distinguished."""
        int_value = ModelPolicyValue(value=42)
        float_value = ModelPolicyValue(value=42.0)

        assert int_value.value_type == "int"
        assert float_value.value_type == "float"
        assert int_value.get_python_type() == int
        assert float_value.get_python_type() == float

    def test_none_zero_distinction(self):
        """Test that None and zero are properly distinguished."""
        none_value = ModelPolicyValue(value=None)
        zero_value = ModelPolicyValue(value=0)

        assert none_value.value_type == "none"
        assert zero_value.value_type == "int"
        assert none_value.is_none() is True
        assert zero_value.is_none() is False


@pytest.mark.unit
class TestSecurityEdgeCases:
    """Test security-critical edge cases and attack vectors."""

    def test_sensitive_flag_persists_through_serialization(self):
        """Test sensitive flag survives serialization roundtrip."""
        original = ModelPolicyValue(value="secret", is_sensitive=True)
        data = original.model_dump()
        restored = ModelPolicyValue.model_validate(data)

        assert restored.is_sensitive is True

    def test_large_string_accepted(self):
        """Test large strings are accepted (no size limit on strings)."""
        large_string = "x" * 100000
        value = ModelPolicyValue(value=large_string)
        assert len(value.value) == 100000
        assert value.value_type == "str"

    def test_deeply_nested_dict(self):
        """Test deeply nested dict structures."""
        nested = {"level1": {"level2": {"level3": {"level4": "value"}}}}
        value = ModelPolicyValue(value=nested)
        assert value.value_type == "dict"
        assert value.value["level1"]["level2"]["level3"]["level4"] == "value"

    def test_special_characters_in_string(self):
        """Test special characters in strings."""
        special = '!@#$%^&*()_+-={}[]|\\:";<>?,./~`'
        value = ModelPolicyValue(value=special)
        assert value.value == special
        assert value.value_type == "str"

    def test_metadata_with_special_characters(self):
        """Test metadata with special characters."""
        metadata = {"key": "value with special chars: !@#$%"}
        value = ModelPolicyValue(value=42, metadata=metadata)
        assert value.metadata == metadata

    def test_sql_injection_like_string(self):
        """Test SQL injection-like strings are handled safely."""
        sql_like = "'; DROP TABLE users; --"
        value = ModelPolicyValue(value=sql_like, is_sensitive=True)
        assert value.value == sql_like
        assert value.value_type == "str"
        assert value.is_sensitive is True

    def test_xss_like_string(self):
        """Test XSS-like strings are handled safely."""
        xss_like = "<script>alert('XSS')</script>"
        value = ModelPolicyValue(value=xss_like, is_sensitive=False)
        assert value.value == xss_like
        assert value.value_type == "str"

    def test_json_bomb_prevention_list(self):
        """Test JSON bomb prevention via list size limit."""
        # This would be a JSON bomb if we allowed unlimited nesting
        with pytest.raises(ModelOnexError) as exc_info:
            ModelPolicyValue(value=list(range(10001)))

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "exceeds maximum size" in str(exc_info.value).lower()

    def test_json_bomb_prevention_dict(self):
        """Test JSON bomb prevention via dict size limit."""
        # This would be a JSON bomb if we allowed unlimited size
        with pytest.raises(ModelOnexError) as exc_info:
            ModelPolicyValue(value={f"key{i}": f"value{i}" for i in range(1001)})

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "exceeds maximum size" in str(exc_info.value).lower()


@pytest.mark.unit
class TestPolicySpecificUseCases:
    """Test policy-specific use cases."""

    def test_max_attempts_policy(self):
        """Test max attempts policy value."""
        policy = ModelPolicyValue(value=3, metadata={"policy": "max_login_attempts"})
        assert policy.value == 3
        assert policy.value_type == "int"

    def test_timeout_policy(self):
        """Test timeout policy value."""
        policy = ModelPolicyValue(value=30.0, metadata={"policy": "session_timeout"})
        assert policy.value == 30.0
        assert policy.value_type == "float"

    def test_allowed_ips_policy(self):
        """Test allowed IPs policy value."""
        ips = ["192.168.1.1", "192.168.1.2", "10.0.0.1"]
        policy = ModelPolicyValue(value=ips, metadata={"policy": "allowed_ips"})
        assert policy.value == ips
        assert policy.value_type == "list"

    def test_security_config_policy(self):
        """Test security configuration policy value."""
        config = {
            "require_2fa": True,
            "max_attempts": 3,
            "lockout_duration": 300,
        }
        policy = ModelPolicyValue(
            value=config,
            is_sensitive=False,
            metadata={"policy": "security_config"},
        )
        assert policy.value == config
        assert policy.value_type == "dict"

    def test_api_key_policy(self):
        """Test API key policy value (sensitive)."""
        policy = ModelPolicyValue(
            value="sk-proj-1234567890abcdef",
            is_sensitive=True,
            metadata={"policy": "api_key"},
        )
        assert policy.is_sensitive is True
        assert policy.value_type == "str"
        # Value should be masked in string representation
        assert "[SENSITIVE]" in str(policy)

    def test_optional_policy_not_set(self):
        """Test optional policy that is not set (None)."""
        policy = ModelPolicyValue(
            value=None,
            metadata={"policy": "optional_webhook_url"},
        )
        assert policy.is_none() is True
        assert policy.value is None
