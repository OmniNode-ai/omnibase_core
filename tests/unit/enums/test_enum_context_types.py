"""
Tests for EnumContextTypes enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_context_types import EnumContextTypes


class TestEnumContextTypes:
    """Test cases for EnumContextTypes enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        assert EnumContextTypes.CONTEXT == "context"
        assert EnumContextTypes.VARIABLE == "variable"
        assert EnumContextTypes.ENVIRONMENT == "environment"
        assert EnumContextTypes.CONFIGURATION == "configuration"
        assert EnumContextTypes.RUNTIME == "runtime"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumContextTypes, str)
        assert issubclass(EnumContextTypes, Enum)

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings."""
        context_type = EnumContextTypes.CONTEXT
        assert isinstance(context_type, str)
        assert context_type == "context"
        assert len(context_type) == 7
        assert context_type.startswith("cont")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumContextTypes)
        assert len(values) == 5
        assert EnumContextTypes.CONTEXT in values
        assert EnumContextTypes.RUNTIME in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "context" in EnumContextTypes
        assert "invalid_type" not in EnumContextTypes

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        type1 = EnumContextTypes.CONTEXT
        type2 = EnumContextTypes.VARIABLE

        assert type1 != type2
        assert type1 == "context"
        assert type2 == "variable"

    def test_enum_serialization(self):
        """Test that enum values can be serialized."""
        context_type = EnumContextTypes.ENVIRONMENT
        serialized = context_type.value
        assert serialized == "environment"

        # Test JSON serialization
        import json

        json_str = json.dumps(context_type)
        assert json_str == '"environment"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        context_type = EnumContextTypes("configuration")
        assert context_type == EnumContextTypes.CONFIGURATION

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumContextTypes("invalid_type")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "context",
            "variable",
            "environment",
            "configuration",
            "runtime",
        }

        actual_values = {member.value for member in EnumContextTypes}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert "Enum for context types used in execution" in EnumContextTypes.__doc__

    def test_enum_context_types(self):
        """Test that enum covers typical context types."""
        # Test basic context types
        assert EnumContextTypes.CONTEXT in EnumContextTypes
        assert EnumContextTypes.VARIABLE in EnumContextTypes

        # Test environment types
        assert EnumContextTypes.ENVIRONMENT in EnumContextTypes
        assert EnumContextTypes.CONFIGURATION in EnumContextTypes

        # Test runtime type
        assert EnumContextTypes.RUNTIME in EnumContextTypes
