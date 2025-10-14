"""
Tests for EnumHandlerType enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_handler_type import EnumHandlerType


class TestEnumHandlerType:
    """Test cases for EnumHandlerType enum."""

    def test_enum_values(self):
        """Test that all enum values are correct."""
        assert EnumHandlerType.EXTENSION == "extension"
        assert EnumHandlerType.SPECIAL == "special"
        assert EnumHandlerType.NAMED == "named"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumHandlerType, str)
        assert issubclass(EnumHandlerType, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        assert str(EnumHandlerType.EXTENSION) == "EnumHandlerType.EXTENSION"
        assert str(EnumHandlerType.SPECIAL) == "EnumHandlerType.SPECIAL"
        assert str(EnumHandlerType.NAMED) == "EnumHandlerType.NAMED"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values."""
        values = list(EnumHandlerType)
        assert len(values) == 3
        assert EnumHandlerType.EXTENSION in values
        assert EnumHandlerType.SPECIAL in values
        assert EnumHandlerType.NAMED in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert "extension" in EnumHandlerType
        assert "special" in EnumHandlerType
        assert "named" in EnumHandlerType
        assert "invalid" not in EnumHandlerType

    def test_enum_comparison(self):
        """Test enum comparison."""
        assert EnumHandlerType.EXTENSION == "extension"
        assert EnumHandlerType.SPECIAL == "special"
        assert EnumHandlerType.NAMED == "named"

    def test_enum_serialization(self):
        """Test enum serialization."""
        assert EnumHandlerType.EXTENSION.value == "extension"
        assert EnumHandlerType.SPECIAL.value == "special"
        assert EnumHandlerType.NAMED.value == "named"

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        assert EnumHandlerType("extension") == EnumHandlerType.EXTENSION
        assert EnumHandlerType("special") == EnumHandlerType.SPECIAL
        assert EnumHandlerType("named") == EnumHandlerType.NAMED

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumHandlerType("invalid")

    def test_enum_all_values(self):
        """Test that all enum values are accessible."""
        all_values = [handler_type.value for handler_type in EnumHandlerType]
        expected_values = ["extension", "special", "named"]
        assert set(all_values) == set(expected_values)

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert (
            "Canonical handler types for ONEX/OmniBase file type handlers"
            in EnumHandlerType.__doc__
        )

    def test_handler_type_categories(self):
        """Test that handler types represent different categories."""
        # Extension handlers work with file extensions
        assert EnumHandlerType.EXTENSION in EnumHandlerType
        # Special handlers work with special cases
        assert EnumHandlerType.SPECIAL in EnumHandlerType
        # Named handlers work with specific names
        assert EnumHandlerType.NAMED in EnumHandlerType
