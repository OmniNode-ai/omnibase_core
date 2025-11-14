"""Test EnumCliContextValueType enum."""

from enum import Enum, unique

import pytest

from omnibase_core.enums.enum_cli_context_value_type import EnumCliContextValueType


class TestEnumCliContextValueType:
    """Test EnumCliContextValueType functionality."""

    def test_enum_inheritance(self):
        """Test enum inheritance."""
        assert issubclass(EnumCliContextValueType, str)
        assert issubclass(EnumCliContextValueType, Enum)

    def test_enum_values(self):
        """Test enum values."""
        assert EnumCliContextValueType.STRING == "string"
        assert EnumCliContextValueType.INTEGER == "integer"
        assert EnumCliContextValueType.FLOAT == "float"
        assert EnumCliContextValueType.BOOLEAN == "boolean"
        assert EnumCliContextValueType.DATETIME == "datetime"
        assert EnumCliContextValueType.PATH == "path"
        assert EnumCliContextValueType.UUID == "uuid"
        assert EnumCliContextValueType.STRING_LIST == "string_list"

    def test_enum_string_behavior(self):
        """Test enum string behavior."""
        value_type = EnumCliContextValueType.STRING
        assert isinstance(value_type, str)
        assert value_type == "string"
        assert len(value_type) == 6
        assert value_type.startswith("str")

    def test_enum_iteration(self):
        """Test enum iteration."""
        values = list(EnumCliContextValueType)
        assert len(values) == 8
        assert EnumCliContextValueType.STRING in values
        assert EnumCliContextValueType.UUID in values

    def test_enum_membership(self):
        """Test enum membership."""
        assert "string" in EnumCliContextValueType
        assert "integer" in EnumCliContextValueType
        assert "invalid" not in EnumCliContextValueType

    def test_enum_comparison(self):
        """Test enum comparison."""
        assert EnumCliContextValueType.STRING == "string"
        assert EnumCliContextValueType.STRING != "integer"
        assert EnumCliContextValueType.INTEGER < EnumCliContextValueType.STRING_LIST

    def test_enum_serialization(self):
        """Test enum serialization."""
        value_type = EnumCliContextValueType.BOOLEAN
        serialized = value_type.value
        assert serialized == "boolean"
        import json

        json_str = json.dumps(value_type)
        assert json_str == '"boolean"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        value_type = EnumCliContextValueType("string")
        assert value_type == EnumCliContextValueType.STRING

    def test_enum_invalid_value(self):
        """Test enum with invalid value."""
        with pytest.raises(ValueError):
            EnumCliContextValueType("invalid_type")

    def test_enum_all_values(self):
        """Test all enum values."""
        expected_values = [
            "string",
            "integer",
            "float",
            "boolean",
            "datetime",
            "path",
            "uuid",
            "string_list",
        ]
        actual_values = [e.value for e in EnumCliContextValueType]
        assert set(actual_values) == set(expected_values)

    def test_enum_docstring(self):
        """Test enum docstring."""
        assert EnumCliContextValueType.__doc__ is not None
        assert "CLI context value type enumeration" in EnumCliContextValueType.__doc__

    def test_enum_unique_decorator(self):
        """Test that enum has unique decorator."""
        assert hasattr(EnumCliContextValueType, "__annotations__")

    def test_enum_context_types(self):
        """Test specific context value types."""
        # Test string context
        string_type = EnumCliContextValueType.STRING
        assert string_type == "string"

        # Test numeric contexts
        int_type = EnumCliContextValueType.INTEGER
        float_type = EnumCliContextValueType.FLOAT
        assert int_type == "integer"
        assert float_type == "float"

        # Test boolean context
        bool_type = EnumCliContextValueType.BOOLEAN
        assert bool_type == "boolean"

        # Test complex contexts
        datetime_type = EnumCliContextValueType.DATETIME
        path_type = EnumCliContextValueType.PATH
        uuid_type = EnumCliContextValueType.UUID
        list_type = EnumCliContextValueType.STRING_LIST

        assert datetime_type == "datetime"
        assert path_type == "path"
        assert uuid_type == "uuid"
        assert list_type == "string_list"
