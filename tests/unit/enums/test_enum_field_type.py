# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for EnumFieldType enum.

Tests the field type enumeration for metadata field information.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_field_type import EnumFieldType


@pytest.mark.unit
class TestEnumFieldType:
    """Test class for EnumFieldType."""

    def test_enum_values(self):
        """Test enum values exist."""
        assert EnumFieldType.STRING == "str"
        assert EnumFieldType.INTEGER == "int"
        assert EnumFieldType.FLOAT == "float"
        assert EnumFieldType.BOOLEAN == "bool"
        assert EnumFieldType.DATETIME == "datetime"
        assert EnumFieldType.DATE == "date"
        assert EnumFieldType.TIME == "time"
        assert EnumFieldType.TIMESTAMP == "timestamp"
        assert EnumFieldType.UUID == "uuid"
        assert EnumFieldType.UUID4 == "uuid4"
        assert EnumFieldType.LIST == "list[Any]"
        assert EnumFieldType.DICT == "dict[str, Any]"
        assert EnumFieldType.SET == "set"
        assert EnumFieldType.OPTIONAL_STRING == "str | none"
        assert EnumFieldType.OPTIONAL_INTEGER == "int | none"
        assert EnumFieldType.OPTIONAL_FLOAT == "float | none"
        assert EnumFieldType.OPTIONAL_BOOLEAN == "bool | none"
        assert EnumFieldType.OPTIONAL_DATETIME == "datetime | none"
        assert EnumFieldType.OPTIONAL_UUID == "uuid | none"
        assert EnumFieldType.JSON == "json"
        assert EnumFieldType.BYTES == "bytes"
        assert EnumFieldType.ANY == "any"

    def test_enum_inheritance(self):
        """Test enum inheritance."""
        assert issubclass(EnumFieldType, str)
        assert issubclass(EnumFieldType, Enum)

    def test_enum_string_behavior(self):
        """Test enum string behavior."""
        field_type = EnumFieldType.STRING
        assert isinstance(field_type, str)
        assert field_type == "str"
        assert len(field_type) == 3

    def test_enum_iteration(self):
        """Test enum iteration."""
        values = list(EnumFieldType)
        assert len(values) == 22
        assert EnumFieldType.STRING in values

    def test_enum_membership(self):
        """Test enum membership."""
        assert "str" in EnumFieldType
        assert "int" in EnumFieldType
        assert "invalid_value" not in EnumFieldType

    def test_enum_comparison(self):
        """Test enum comparison."""
        field_type1 = EnumFieldType.STRING
        field_type2 = EnumFieldType.STRING
        assert field_type1 == field_type2
        assert field_type1 is field_type2

    def test_enum_serialization(self):
        """Test enum serialization."""
        field_type = EnumFieldType.INTEGER
        serialized = field_type.value
        assert serialized == "int"

        import json

        json_str = json.dumps(field_type)
        assert json_str == '"int"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        data = "float"
        field_type = EnumFieldType(data)
        assert field_type == EnumFieldType.FLOAT

    def test_enum_invalid_value(self):
        """Test enum invalid value handling."""
        with pytest.raises(ValueError):
            EnumFieldType("invalid_value")

    def test_enum_all_values(self):
        """Test all enum values are accessible."""
        expected_values = [
            "str",
            "int",
            "float",
            "bool",
            "datetime",
            "date",
            "time",
            "timestamp",
            "uuid",
            "uuid4",
            "list[Any]",
            "dict[str, Any]",
            "set",
            "str | none",
            "int | none",
            "float | none",
            "bool | none",
            "datetime | none",
            "uuid | none",
            "json",
            "bytes",
            "any",
        ]
        actual_values = [e.value for e in EnumFieldType]
        assert set(actual_values) == set(expected_values)

    def test_enum_docstring(self):
        """Test enum has proper docstring."""
        assert EnumFieldType.__doc__ is not None
        assert "field type" in EnumFieldType.__doc__

    def test_enum_unique_decorator(self):
        """Test enum has unique decorator."""
        # The @unique decorator ensures no duplicate values
        values = [e.value for e in EnumFieldType]
        assert len(values) == len(set(values))

    def test_enum_str_method(self):
        """Test enum __str__ method."""
        field_type = EnumFieldType.STRING
        assert str(field_type) == "str"
        assert field_type.__str__() == "str"

    def test_from_string_direct_mapping(self):
        """Test from_string with direct mapping."""
        assert EnumFieldType.from_string("str") == EnumFieldType.STRING
        assert EnumFieldType.from_string("int") == EnumFieldType.INTEGER
        assert EnumFieldType.from_string("float") == EnumFieldType.FLOAT
        assert EnumFieldType.from_string("bool") == EnumFieldType.BOOLEAN
        assert EnumFieldType.from_string("datetime") == EnumFieldType.DATETIME
        assert EnumFieldType.from_string("uuid") == EnumFieldType.UUID

    def test_from_string_aliases(self):
        """Test from_string with aliases."""
        assert EnumFieldType.from_string("string") == EnumFieldType.STRING
        assert EnumFieldType.from_string("text") == EnumFieldType.STRING
        assert EnumFieldType.from_string("number") == EnumFieldType.FLOAT
        assert EnumFieldType.from_string("numeric") == EnumFieldType.FLOAT
        assert EnumFieldType.from_string("bool") == EnumFieldType.BOOLEAN
        assert EnumFieldType.from_string("datetime") == EnumFieldType.DATETIME
        assert EnumFieldType.from_string("timestamp") == EnumFieldType.TIMESTAMP
        assert EnumFieldType.from_string("id") == EnumFieldType.UUID
        assert EnumFieldType.from_string("identifier") == EnumFieldType.UUID
        assert (
            EnumFieldType.from_string("optional_str") == EnumFieldType.OPTIONAL_STRING
        )
        assert (
            EnumFieldType.from_string("optional_int") == EnumFieldType.OPTIONAL_INTEGER
        )

    def test_from_string_case_insensitive(self):
        """Test from_string is case insensitive."""
        assert EnumFieldType.from_string("STRING") == EnumFieldType.STRING
        assert EnumFieldType.from_string("String") == EnumFieldType.STRING
        assert EnumFieldType.from_string("  string  ") == EnumFieldType.STRING

    def test_from_string_fallback(self):
        """Test from_string fallback to STRING."""
        assert EnumFieldType.from_string("unknown_type") == EnumFieldType.STRING
        assert EnumFieldType.from_string("") == EnumFieldType.STRING

    def test_is_optional_property(self):
        """Test is_optional property."""
        # Non-optional types return False
        assert EnumFieldType.STRING.is_optional is False
        assert EnumFieldType.INTEGER.is_optional is False
        assert EnumFieldType.FLOAT.is_optional is False
        assert EnumFieldType.BOOLEAN.is_optional is False
        assert EnumFieldType.DATETIME.is_optional is False
        assert EnumFieldType.UUID.is_optional is False

        # Optional types return True (values contain "| none")
        assert EnumFieldType.OPTIONAL_STRING.is_optional is True
        assert EnumFieldType.OPTIONAL_INTEGER.is_optional is True
        assert EnumFieldType.OPTIONAL_FLOAT.is_optional is True
        assert EnumFieldType.OPTIONAL_BOOLEAN.is_optional is True
        assert EnumFieldType.OPTIONAL_DATETIME.is_optional is True
        assert EnumFieldType.OPTIONAL_UUID.is_optional is True

    def test_base_type_property(self):
        """Test base_type property."""
        # Non-optional types return themselves
        assert EnumFieldType.STRING.base_type == EnumFieldType.STRING
        assert EnumFieldType.INTEGER.base_type == EnumFieldType.INTEGER
        assert EnumFieldType.FLOAT.base_type == EnumFieldType.FLOAT
        assert EnumFieldType.BOOLEAN.base_type == EnumFieldType.BOOLEAN
        assert EnumFieldType.DATETIME.base_type == EnumFieldType.DATETIME
        assert EnumFieldType.UUID.base_type == EnumFieldType.UUID

        # Optional types return their non-optional base type
        assert EnumFieldType.OPTIONAL_STRING.base_type == EnumFieldType.STRING
        assert EnumFieldType.OPTIONAL_INTEGER.base_type == EnumFieldType.INTEGER
        assert EnumFieldType.OPTIONAL_FLOAT.base_type == EnumFieldType.FLOAT
        assert EnumFieldType.OPTIONAL_BOOLEAN.base_type == EnumFieldType.BOOLEAN
        assert EnumFieldType.OPTIONAL_DATETIME.base_type == EnumFieldType.DATETIME
        assert EnumFieldType.OPTIONAL_UUID.base_type == EnumFieldType.UUID

    def test_field_type_categories(self):
        """Test field type categories."""
        # Basic types
        basic_types = [
            EnumFieldType.STRING,
            EnumFieldType.INTEGER,
            EnumFieldType.FLOAT,
            EnumFieldType.BOOLEAN,
        ]
        for field_type in basic_types:
            assert field_type.value in ["str", "int", "float", "bool"]

        # Date/time types
        datetime_types = [
            EnumFieldType.DATETIME,
            EnumFieldType.DATE,
            EnumFieldType.TIME,
            EnumFieldType.TIMESTAMP,
        ]
        for field_type in datetime_types:
            assert field_type.value in ["datetime", "date", "time", "timestamp"]

        # UUID types
        uuid_types = [EnumFieldType.UUID, EnumFieldType.UUID4]
        for field_type in uuid_types:
            assert field_type.value in ["uuid", "uuid4"]

        # Collection types
        collection_types = [EnumFieldType.LIST, EnumFieldType.DICT, EnumFieldType.SET]
        for field_type in collection_types:
            assert field_type.value in ["list[Any]", "dict[str, Any]", "set"]

        # Optional types
        optional_types = [
            EnumFieldType.OPTIONAL_STRING,
            EnumFieldType.OPTIONAL_INTEGER,
            EnumFieldType.OPTIONAL_FLOAT,
            EnumFieldType.OPTIONAL_BOOLEAN,
            EnumFieldType.OPTIONAL_DATETIME,
            EnumFieldType.OPTIONAL_UUID,
        ]
        for field_type in optional_types:
            assert "| none" in field_type.value

        # Complex types
        complex_types = [EnumFieldType.JSON, EnumFieldType.BYTES, EnumFieldType.ANY]
        for field_type in complex_types:
            assert field_type.value in ["json", "bytes", "any"]
