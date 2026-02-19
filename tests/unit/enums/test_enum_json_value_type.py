# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for enum_json_value_type.py"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_json_value_type import EnumJsonValueType


@pytest.mark.unit
class TestEnumJsonValueType:
    """Test cases for EnumJsonValueType"""

    def test_enum_values(self):
        """Test that all enum values are correct"""
        assert EnumJsonValueType.STRING == "string"
        assert EnumJsonValueType.NUMBER == "number"
        assert EnumJsonValueType.BOOLEAN == "boolean"
        assert EnumJsonValueType.ARRAY == "array"
        assert EnumJsonValueType.NULL == "null"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum"""
        assert issubclass(EnumJsonValueType, str)
        assert issubclass(EnumJsonValueType, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values"""
        assert EnumJsonValueType.STRING == "string"
        assert EnumJsonValueType.NUMBER == "number"
        assert EnumJsonValueType.BOOLEAN == "boolean"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values"""
        values = list(EnumJsonValueType)
        assert len(values) == 5
        assert EnumJsonValueType.STRING in values
        assert EnumJsonValueType.NULL in values

    def test_enum_membership(self):
        """Test membership testing"""
        assert EnumJsonValueType.STRING in EnumJsonValueType
        assert "string" in EnumJsonValueType
        assert "invalid_value" not in EnumJsonValueType

    def test_enum_comparison(self):
        """Test enum comparison"""
        assert EnumJsonValueType.STRING == EnumJsonValueType.STRING
        assert EnumJsonValueType.NUMBER != EnumJsonValueType.STRING
        assert EnumJsonValueType.STRING == "string"

    def test_enum_serialization(self):
        """Test enum serialization"""
        assert EnumJsonValueType.STRING.value == "string"
        assert EnumJsonValueType.NUMBER.value == "number"

    def test_enum_deserialization(self):
        """Test enum deserialization"""
        assert EnumJsonValueType("string") == EnumJsonValueType.STRING
        assert EnumJsonValueType("number") == EnumJsonValueType.NUMBER

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError"""
        with pytest.raises(ValueError):
            EnumJsonValueType("invalid_value")

        with pytest.raises(ValueError):
            EnumJsonValueType("")

    def test_enum_all_values(self):
        """Test that all expected values are present"""
        expected_values = {"string", "number", "boolean", "array", "null"}
        actual_values = {member.value for member in EnumJsonValueType}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring"""
        # Accept either "compliant" or "compatible" - both are valid ONEX descriptors
        docstring = EnumJsonValueType.__doc__ or ""
        assert "ONEX-" in docstring and "JSON value type" in docstring

    def test_enum_json_types(self):
        """Test specific JSON value types"""
        # Primitive types
        assert EnumJsonValueType.STRING.value == "string"
        assert EnumJsonValueType.NUMBER.value == "number"
        assert EnumJsonValueType.BOOLEAN.value == "boolean"

        # Complex types
        assert EnumJsonValueType.ARRAY.value == "array"

        # Special types
        assert EnumJsonValueType.NULL.value == "null"

    def test_enum_json_type_categories(self):
        """Test JSON type categories"""
        # Primitive types
        primitive_types = {
            EnumJsonValueType.STRING,
            EnumJsonValueType.NUMBER,
            EnumJsonValueType.BOOLEAN,
        }

        # Complex types
        complex_types = {EnumJsonValueType.ARRAY}

        # Special types
        special_types = {EnumJsonValueType.NULL}

        all_types = set(EnumJsonValueType)
        assert primitive_types.union(complex_types).union(special_types) == all_types
