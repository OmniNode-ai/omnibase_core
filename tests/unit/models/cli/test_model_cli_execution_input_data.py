"""
Comprehensive tests for ModelCliExecutionInputData.

Tests cover:
- Value type validation (validate_value_matches_type)
- Factory methods (from_string, from_integer, from_float, from_boolean, from_path, from_uuid, from_string_list)
- Helper methods (get_string_value, get_typed_value, is_path_value, is_uuid_value)
- Protocol implementations (serialize, get_name, set_name, validate_instance)
- Edge cases and error scenarios
- Kwargs parameter handling and type validation
"""

import tempfile
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_cli_input_value_type import EnumCliInputValueType
from omnibase_core.enums.enum_data_type import EnumDataType
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.cli.model_cli_execution_input_data import (
    ModelCliExecutionInputData,
)


class TestModelCliExecutionInputDataValueValidation:
    """Test value type validation."""

    def test_validate_string_value_type_valid(self):
        """Test validation passes for matching string value type."""
        data = ModelCliExecutionInputData(
            key="test_key",
            value_type=EnumCliInputValueType.STRING,
            value="test_value",
            data_type=EnumDataType.TEXT,
        )
        assert data.value == "test_value"

    def test_validate_string_value_type_invalid(self):
        """Test validation fails for non-string value with STRING type."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelCliExecutionInputData(
                key="test_key",
                value_type=EnumCliInputValueType.STRING,
                value=123,  # Invalid: integer instead of string
                data_type=EnumDataType.TEXT,
            )
        assert "String value type must contain str data" in str(exc_info.value)

    def test_validate_integer_value_type_valid(self):
        """Test validation passes for matching integer value type."""
        data = ModelCliExecutionInputData(
            key="test_key",
            value_type=EnumCliInputValueType.INTEGER,
            value=42,
            data_type=EnumDataType.TEXT,
        )
        assert data.value == 42

    def test_validate_integer_value_type_invalid(self):
        """Test validation fails for non-integer value with INTEGER type."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelCliExecutionInputData(
                key="test_key",
                value_type=EnumCliInputValueType.INTEGER,
                value="not_an_int",  # Invalid: string instead of int
                data_type=EnumDataType.TEXT,
            )
        assert "Integer value type must contain int data" in str(exc_info.value)

    def test_validate_float_value_type_valid(self):
        """Test validation passes for matching float value type."""
        data = ModelCliExecutionInputData(
            key="test_key",
            value_type=EnumCliInputValueType.FLOAT,
            value=3.14,
            data_type=EnumDataType.TEXT,
        )
        assert data.value == 3.14

    def test_validate_float_value_type_invalid(self):
        """Test validation fails for non-float value with FLOAT type."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelCliExecutionInputData(
                key="test_key",
                value_type=EnumCliInputValueType.FLOAT,
                value="not_a_float",  # Invalid: string instead of float
                data_type=EnumDataType.TEXT,
            )
        assert "Float value type must contain float data" in str(exc_info.value)

    def test_validate_boolean_value_type_valid(self):
        """Test validation passes for matching boolean value type."""
        data = ModelCliExecutionInputData(
            key="test_key",
            value_type=EnumCliInputValueType.BOOLEAN,
            value=True,
            data_type=EnumDataType.TEXT,
        )
        assert data.value is True

    def test_validate_boolean_value_type_invalid(self):
        """Test validation fails for non-boolean value with BOOLEAN type."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelCliExecutionInputData(
                key="test_key",
                value_type=EnumCliInputValueType.BOOLEAN,
                value=1,  # Invalid: int instead of bool
                data_type=EnumDataType.TEXT,
            )
        assert "Boolean value type must contain bool data" in str(exc_info.value)

    def test_validate_path_value_type_valid(self):
        """Test validation passes for matching Path value type."""
        path = Path(f"{tempfile.gettempdir()}/test")
        data = ModelCliExecutionInputData(
            key="test_key",
            value_type=EnumCliInputValueType.PATH,
            value=path,
            data_type=EnumDataType.TEXT,
        )
        assert data.value == path

    def test_validate_path_value_type_invalid(self):
        """Test validation fails for non-Path value with PATH type."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelCliExecutionInputData(
                key="test_key",
                value_type=EnumCliInputValueType.PATH,
                value=f"{tempfile.gettempdir()}/test",
                data_type=EnumDataType.TEXT,
            )
        assert "Path value type must contain Path data" in str(exc_info.value)

    def test_validate_uuid_value_type_valid(self):
        """Test validation passes for matching UUID value type."""
        test_uuid = uuid4()
        data = ModelCliExecutionInputData(
            key="test_key",
            value_type=EnumCliInputValueType.UUID,
            value=test_uuid,
            data_type=EnumDataType.TEXT,
        )
        assert data.value == test_uuid

    def test_validate_uuid_value_type_invalid(self):
        """Test validation fails for non-UUID value with UUID type."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelCliExecutionInputData(
                key="test_key",
                value_type=EnumCliInputValueType.UUID,
                value="not-a-uuid",  # Invalid: string instead of UUID
                data_type=EnumDataType.TEXT,
            )
        assert "UUID value type must contain UUID data" in str(exc_info.value)

    def test_validate_string_list_value_type_valid(self):
        """Test validation passes for matching string list value type."""
        data = ModelCliExecutionInputData(
            key="test_key",
            value_type=EnumCliInputValueType.STRING_LIST,
            value=["item1", "item2", "item3"],
            data_type=EnumDataType.TEXT,
        )
        assert data.value == ["item1", "item2", "item3"]

    def test_validate_string_list_value_type_invalid_not_list(self):
        """Test validation fails for non-list value with STRING_LIST type."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelCliExecutionInputData(
                key="test_key",
                value_type=EnumCliInputValueType.STRING_LIST,
                value="not_a_list",  # Invalid: string instead of list
                data_type=EnumDataType.TEXT,
            )
        assert "StringList value type must contain list[str] data" in str(
            exc_info.value
        )

    def test_validate_string_list_value_type_invalid_non_string_items(self):
        """Test validation fails for list with non-string items."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelCliExecutionInputData(
                key="test_key",
                value_type=EnumCliInputValueType.STRING_LIST,
                value=["item1", 123, "item3"],  # Invalid: contains non-string
                data_type=EnumDataType.TEXT,
            )
        assert "StringList value type must contain list[str] data" in str(
            exc_info.value
        )


class TestModelCliExecutionInputDataFactoryMethods:
    """Test factory methods for creating input data."""

    def test_from_string_minimal(self):
        """Test creating input data from string with minimal parameters."""
        data = ModelCliExecutionInputData.from_string("test_key", "test_value")

        assert data.key == "test_key"
        assert data.value == "test_value"
        assert data.value_type == EnumCliInputValueType.STRING
        assert data.data_type == EnumDataType.TEXT
        assert data.is_sensitive is False
        assert data.is_required is False
        assert data.description == ""
        assert data.validation_pattern == ""

    def test_from_string_with_kwargs(self):
        """Test creating input data from string with all kwargs."""
        data = ModelCliExecutionInputData.from_string(
            "test_key",
            "test_value",
            data_type=EnumDataType.TEXT,
            is_sensitive=True,
            is_required=True,
            description="Test description",
            validation_pattern=r"^[a-z]+$",
        )

        assert data.key == "test_key"
        assert data.value == "test_value"
        assert data.data_type == EnumDataType.TEXT
        assert data.is_sensitive is True
        assert data.is_required is True
        assert data.description == "Test description"
        assert data.validation_pattern == r"^[a-z]+$"

    def test_from_string_kwargs_type_validation(self):
        """Test that invalid kwargs types are handled gracefully."""
        data = ModelCliExecutionInputData.from_string(
            "test_key",
            "test_value",
            data_type="invalid",  # Wrong type - should default
            is_sensitive="not_a_bool",  # Wrong type - should default to False
            is_required=123,  # Wrong type - should default to False
            description=None,  # Wrong type - should default to ""
            validation_pattern=42,  # Wrong type - should default to ""
        )

        assert data.data_type == EnumDataType.TEXT
        assert data.is_sensitive is False
        assert data.is_required is False
        assert data.description == ""
        assert data.validation_pattern == ""

    def test_from_integer_minimal(self):
        """Test creating input data from integer with minimal parameters."""
        data = ModelCliExecutionInputData.from_integer("test_key", 42)

        assert data.key == "test_key"
        assert data.value == 42
        assert data.value_type == EnumCliInputValueType.INTEGER
        assert data.data_type == EnumDataType.TEXT

    def test_from_integer_with_kwargs(self):
        """Test creating input data from integer with all kwargs."""
        data = ModelCliExecutionInputData.from_integer(
            "test_key",
            42,
            data_type=EnumDataType.TEXT,
            is_sensitive=False,
            is_required=True,
            description="Test integer",
            validation_pattern=r"^\d+$",
        )

        assert data.value == 42
        assert data.is_required is True
        assert data.description == "Test integer"

    def test_from_float_minimal(self):
        """Test creating input data from float with minimal parameters."""
        data = ModelCliExecutionInputData.from_float("test_key", 3.14)

        assert data.key == "test_key"
        assert data.value == 3.14
        assert data.value_type == EnumCliInputValueType.FLOAT

    def test_from_float_with_kwargs(self):
        """Test creating input data from float with all kwargs."""
        data = ModelCliExecutionInputData.from_float(
            "test_key",
            3.14,
            data_type=EnumDataType.TEXT,
            is_sensitive=False,
            is_required=False,
            description="Test float",
            validation_pattern=r"^\d+\.\d+$",
        )

        assert data.value == 3.14
        assert data.description == "Test float"

    def test_from_boolean_minimal(self):
        """Test creating input data from boolean with minimal parameters."""
        data = ModelCliExecutionInputData.from_boolean("test_key", True)

        assert data.key == "test_key"
        assert data.value is True
        assert data.value_type == EnumCliInputValueType.BOOLEAN

    def test_from_boolean_with_kwargs(self):
        """Test creating input data from boolean with all kwargs."""
        data = ModelCliExecutionInputData.from_boolean(
            "test_key",
            False,
            data_type=EnumDataType.TEXT,
            is_sensitive=False,
            is_required=True,
            description="Test boolean",
            validation_pattern="",
        )

        assert data.value is False
        assert data.is_required is True

    def test_from_path_minimal(self):
        """Test creating input data from Path with minimal parameters."""
        path = Path(f"{tempfile.gettempdir()}/test")
        data = ModelCliExecutionInputData.from_path("test_key", path)

        assert data.key == "test_key"
        assert data.value == path
        assert data.value_type == EnumCliInputValueType.PATH

    def test_from_path_with_kwargs(self):
        """Test creating input data from Path with all kwargs."""
        path = Path(f"{tempfile.gettempdir()}/test")
        data = ModelCliExecutionInputData.from_path(
            "test_key",
            path,
            data_type=EnumDataType.TEXT,
            is_sensitive=False,
            is_required=True,
            description="Test path",
            validation_pattern=r"^/tmp/.*$",
        )

        assert data.value == path
        assert data.description == "Test path"

    def test_from_uuid_minimal(self):
        """Test creating input data from UUID with minimal parameters."""
        test_uuid = uuid4()
        data = ModelCliExecutionInputData.from_uuid("test_key", test_uuid)

        assert data.key == "test_key"
        assert data.value == test_uuid
        assert data.value_type == EnumCliInputValueType.UUID

    def test_from_uuid_with_kwargs(self):
        """Test creating input data from UUID with all kwargs."""
        test_uuid = uuid4()
        data = ModelCliExecutionInputData.from_uuid(
            "test_key",
            test_uuid,
            data_type=EnumDataType.TEXT,
            is_sensitive=True,
            is_required=True,
            description="Test UUID",
            validation_pattern="",
        )

        assert data.value == test_uuid
        assert data.is_sensitive is True

    def test_from_string_list_minimal(self):
        """Test creating input data from string list with minimal parameters."""
        items = ["item1", "item2", "item3"]
        data = ModelCliExecutionInputData.from_string_list("test_key", items)

        assert data.key == "test_key"
        assert data.value == items
        assert data.value_type == EnumCliInputValueType.STRING_LIST

    def test_from_string_list_with_kwargs(self):
        """Test creating input data from string list with all kwargs."""
        items = ["item1", "item2"]
        data = ModelCliExecutionInputData.from_string_list(
            "test_key",
            items,
            data_type=EnumDataType.TEXT,
            is_sensitive=False,
            is_required=True,
            description="Test string list",
            validation_pattern="",
        )

        assert data.value == items
        assert data.description == "Test string list"

    def test_from_string_list_empty(self):
        """Test creating input data from empty string list."""
        data = ModelCliExecutionInputData.from_string_list("test_key", [])

        assert data.value == []
        assert data.value_type == EnumCliInputValueType.STRING_LIST


class TestModelCliExecutionInputDataHelperMethods:
    """Test helper methods."""

    def test_get_string_value_from_string(self):
        """Test getting string representation of string value."""
        data = ModelCliExecutionInputData.from_string("test_key", "test_value")
        assert data.get_string_value() == "test_value"

    def test_get_string_value_from_integer(self):
        """Test getting string representation of integer value."""
        data = ModelCliExecutionInputData.from_integer("test_key", 42)
        assert data.get_string_value() == "42"

    def test_get_string_value_from_float(self):
        """Test getting string representation of float value."""
        data = ModelCliExecutionInputData.from_float("test_key", 3.14)
        assert data.get_string_value() == "3.14"

    def test_get_string_value_from_boolean(self):
        """Test getting string representation of boolean value."""
        data = ModelCliExecutionInputData.from_boolean("test_key", True)
        assert data.get_string_value() == "True"

    def test_get_string_value_from_path(self):
        """Test getting string representation of Path value."""
        path = Path(f"{tempfile.gettempdir()}/test")
        data = ModelCliExecutionInputData.from_path("test_key", path)
        assert data.get_string_value() == f"{tempfile.gettempdir()}/test"

    def test_get_string_value_from_uuid(self):
        """Test getting string representation of UUID value."""
        test_uuid = uuid4()
        data = ModelCliExecutionInputData.from_uuid("test_key", test_uuid)
        assert data.get_string_value() == str(test_uuid)

    def test_get_string_value_from_string_list(self):
        """Test getting string representation of string list value."""
        items = ["item1", "item2", "item3"]
        data = ModelCliExecutionInputData.from_string_list("test_key", items)
        assert data.get_string_value() == "item1,item2,item3"

    def test_get_string_value_from_empty_list(self):
        """Test getting string representation of empty list."""
        data = ModelCliExecutionInputData.from_string_list("test_key", [])
        assert data.get_string_value() == ""

    def test_get_typed_value(self):
        """Test getting typed value returns the actual value."""
        test_uuid = uuid4()
        data = ModelCliExecutionInputData.from_uuid("test_key", test_uuid)
        assert data.get_typed_value() == test_uuid
        assert isinstance(data.get_typed_value(), UUID)

    def test_is_path_value_true(self):
        """Test is_path_value returns True for Path values."""
        path = Path(f"{tempfile.gettempdir()}/test")
        data = ModelCliExecutionInputData.from_path("test_key", path)
        assert data.is_path_value() is True

    def test_is_path_value_false(self):
        """Test is_path_value returns False for non-Path values."""
        data = ModelCliExecutionInputData.from_string(
            "test_key", f"{tempfile.gettempdir()}/test"
        )
        assert data.is_path_value() is False

    def test_is_uuid_value_true(self):
        """Test is_uuid_value returns True for UUID values."""
        test_uuid = uuid4()
        data = ModelCliExecutionInputData.from_uuid("test_key", test_uuid)
        assert data.is_uuid_value() is True

    def test_is_uuid_value_false(self):
        """Test is_uuid_value returns False for non-UUID values."""
        data = ModelCliExecutionInputData.from_string("test_key", "not-a-uuid")
        assert data.is_uuid_value() is False


class TestModelCliExecutionInputDataProtocols:
    """Test protocol method implementations."""

    def test_serialize(self):
        """Test serializing to dictionary."""
        data = ModelCliExecutionInputData.from_string("test_key", "test_value")
        serialized = data.serialize()

        assert isinstance(serialized, dict)
        assert "key" in serialized
        assert "value" in serialized
        assert "value_type" in serialized
        assert "data_type" in serialized

    def test_get_name_default(self):
        """Test getting name returns default when no name fields exist."""
        data = ModelCliExecutionInputData.from_string("test_key", "test_value")
        name = data.get_name()

        assert "ModelCliExecutionInputData" in name

    def test_validate_instance(self):
        """Test validating instance."""
        data = ModelCliExecutionInputData.from_string("test_key", "test_value")
        is_valid = data.validate_instance()

        assert is_valid is True


class TestModelCliExecutionInputDataEdgeCases:
    """Test edge cases and error scenarios."""

    def test_sensitive_data_flag(self):
        """Test sensitive data flag."""
        data = ModelCliExecutionInputData.from_string(
            "password",
            "secret123",
            is_sensitive=True,
        )

        assert data.is_sensitive is True
        assert data.value == "secret123"

    def test_required_data_flag(self):
        """Test required data flag."""
        data = ModelCliExecutionInputData.from_string(
            "username",
            "john_doe",
            is_required=True,
        )

        assert data.is_required is True

    def test_validation_pattern(self):
        """Test validation pattern is stored."""
        pattern = r"^[a-zA-Z0-9]+$"
        data = ModelCliExecutionInputData.from_string(
            "test_key",
            "test_value",
            validation_pattern=pattern,
        )

        assert data.validation_pattern == pattern

    def test_description_field(self):
        """Test description field is stored."""
        description = "This is a test field"
        data = ModelCliExecutionInputData.from_string(
            "test_key",
            "test_value",
            description=description,
        )

        assert data.description == description

    def test_integer_negative_value(self):
        """Test negative integer values."""
        data = ModelCliExecutionInputData.from_integer("test_key", -42)
        assert data.value == -42

    def test_float_negative_value(self):
        """Test negative float values."""
        data = ModelCliExecutionInputData.from_float("test_key", -3.14)
        assert data.value == -3.14

    def test_float_zero_value(self):
        """Test zero float value."""
        data = ModelCliExecutionInputData.from_float("test_key", 0.0)
        assert data.value == 0.0

    def test_string_list_single_item(self):
        """Test string list with single item."""
        data = ModelCliExecutionInputData.from_string_list("test_key", ["single"])
        assert data.value == ["single"]
        assert data.get_string_value() == "single"

    def test_path_relative(self):
        """Test relative path."""
        path = Path("relative/path")
        data = ModelCliExecutionInputData.from_path("test_key", path)
        assert data.value == path
        assert "relative/path" in data.get_string_value()

    def test_path_absolute(self):
        """Test absolute path."""
        path = Path("/absolute/path")
        data = ModelCliExecutionInputData.from_path("test_key", path)
        assert data.value == path
        assert "/absolute/path" in data.get_string_value()

    def test_all_data_types_enum(self):
        """Test with different EnumDataType values."""
        for data_type in [
            EnumDataType.TEXT,
            EnumDataType.BINARY,
            EnumDataType.JSON,
            EnumDataType.XML,
        ]:
            data = ModelCliExecutionInputData.from_string(
                "test_key",
                "test_value",
                data_type=data_type,
            )
            assert data.data_type == data_type

    def test_model_config_extra_ignore(self):
        """Test that extra fields are ignored."""
        data = ModelCliExecutionInputData(
            key="test_key",
            value_type=EnumCliInputValueType.STRING,
            value="test_value",
            data_type=EnumDataType.TEXT,
            extra_field="should_be_ignored",  # Extra field
        )
        assert data.key == "test_key"
        assert not hasattr(data, "extra_field")

    def test_string_with_special_characters(self):
        """Test string with special characters."""
        special_value = "test!@#$%^&*()_+-=[]{}|;:',.<>?/~`"
        data = ModelCliExecutionInputData.from_string("test_key", special_value)
        assert data.value == special_value
        assert data.get_string_value() == special_value

    def test_string_with_unicode(self):
        """Test string with unicode characters."""
        unicode_value = "Hello 世界 🌍"
        data = ModelCliExecutionInputData.from_string("test_key", unicode_value)
        assert data.value == unicode_value
        assert data.get_string_value() == unicode_value

    def test_empty_string_value(self):
        """Test empty string value."""
        data = ModelCliExecutionInputData.from_string("test_key", "")
        assert data.value == ""
        assert data.get_string_value() == ""

    def test_string_list_with_empty_strings(self):
        """Test string list containing empty strings."""
        items = ["", "non-empty", ""]
        data = ModelCliExecutionInputData.from_string_list("test_key", items)
        assert data.value == items
        assert data.get_string_value() == ",non-empty,"
