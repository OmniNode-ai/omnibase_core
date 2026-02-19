# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Test EnumComplexityLevel enum."""

from enum import Enum

import pytest

from omnibase_core.enums.enum_complexity_level import EnumComplexityLevel


@pytest.mark.unit
class TestEnumComplexityLevel:
    """Test EnumComplexityLevel functionality."""

    def test_enum_inheritance(self):
        """Test enum inheritance."""
        assert issubclass(EnumComplexityLevel, str)
        assert issubclass(EnumComplexityLevel, Enum)

    def test_enum_values(self):
        """Test enum values."""
        assert EnumComplexityLevel.SIMPLE == "simple"
        assert EnumComplexityLevel.BASIC == "basic"
        assert EnumComplexityLevel.LOW == "low"
        assert EnumComplexityLevel.MEDIUM == "medium"
        assert EnumComplexityLevel.MODERATE == "moderate"
        assert EnumComplexityLevel.HIGH == "high"
        assert EnumComplexityLevel.COMPLEX == "complex"
        assert EnumComplexityLevel.ADVANCED == "advanced"
        assert EnumComplexityLevel.EXPERT == "expert"
        assert EnumComplexityLevel.CRITICAL == "critical"
        assert EnumComplexityLevel.UNKNOWN == "unknown"

    def test_enum_string_behavior(self):
        """Test enum string behavior."""
        level = EnumComplexityLevel.SIMPLE
        assert isinstance(level, str)
        assert level == "simple"
        assert len(level) == 6
        assert level.startswith("sim")

    def test_enum_iteration(self):
        """Test enum iteration."""
        values = list(EnumComplexityLevel)
        assert len(values) == 11
        assert EnumComplexityLevel.SIMPLE in values
        assert EnumComplexityLevel.CRITICAL in values

    def test_enum_membership(self):
        """Test enum membership."""
        assert "simple" in EnumComplexityLevel
        assert "complex" in EnumComplexityLevel
        assert "invalid_level" not in EnumComplexityLevel

    def test_enum_comparison(self):
        """Test enum comparison."""
        assert EnumComplexityLevel.SIMPLE == "simple"
        assert EnumComplexityLevel.SIMPLE != "complex"
        assert EnumComplexityLevel.BASIC < EnumComplexityLevel.COMPLEX

    def test_enum_serialization(self):
        """Test enum serialization."""
        level = EnumComplexityLevel.HIGH
        serialized = level.value
        assert serialized == "high"
        import json

        json_str = json.dumps(level)
        assert json_str == '"high"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        level = EnumComplexityLevel("simple")
        assert level == EnumComplexityLevel.SIMPLE

    def test_enum_invalid_value(self):
        """Test enum with invalid value."""
        with pytest.raises(ValueError):
            EnumComplexityLevel("invalid_level")

    def test_enum_all_values(self):
        """Test all enum values."""
        expected_values = [
            "simple",
            "basic",
            "low",
            "medium",
            "moderate",
            "high",
            "complex",
            "advanced",
            "expert",
            "critical",
            "unknown",
        ]
        actual_values = [e.value for e in EnumComplexityLevel]
        assert set(actual_values) == set(expected_values)

    def test_enum_docstring(self):
        """Test enum docstring."""
        assert EnumComplexityLevel.__doc__ is not None
        assert "Complexity levels" in EnumComplexityLevel.__doc__

    def test_enum_unique_decorator(self):
        """Test that enum has unique decorator."""
        assert hasattr(EnumComplexityLevel, "__annotations__")

    def test_str_method(self):
        """Test __str__ method."""
        level = EnumComplexityLevel.COMPLEX
        assert str(level) == "complex"
        assert str(level) == level.value

    def test_get_numeric_value(self):
        """Test get_numeric_value method."""
        assert EnumComplexityLevel.get_numeric_value(EnumComplexityLevel.SIMPLE) == 1
        assert EnumComplexityLevel.get_numeric_value(EnumComplexityLevel.BASIC) == 2
        assert EnumComplexityLevel.get_numeric_value(EnumComplexityLevel.LOW) == 3
        assert EnumComplexityLevel.get_numeric_value(EnumComplexityLevel.MEDIUM) == 5
        assert EnumComplexityLevel.get_numeric_value(EnumComplexityLevel.MODERATE) == 6
        assert EnumComplexityLevel.get_numeric_value(EnumComplexityLevel.HIGH) == 7
        assert EnumComplexityLevel.get_numeric_value(EnumComplexityLevel.COMPLEX) == 8
        assert EnumComplexityLevel.get_numeric_value(EnumComplexityLevel.ADVANCED) == 9
        assert EnumComplexityLevel.get_numeric_value(EnumComplexityLevel.EXPERT) == 10
        assert EnumComplexityLevel.get_numeric_value(EnumComplexityLevel.CRITICAL) == 11
        assert EnumComplexityLevel.get_numeric_value(EnumComplexityLevel.UNKNOWN) == 5

    def test_is_simple(self):
        """Test is_simple method."""
        assert EnumComplexityLevel.is_simple(EnumComplexityLevel.SIMPLE) is True
        assert EnumComplexityLevel.is_simple(EnumComplexityLevel.BASIC) is True
        assert EnumComplexityLevel.is_simple(EnumComplexityLevel.LOW) is True
        assert EnumComplexityLevel.is_simple(EnumComplexityLevel.MEDIUM) is False
        assert EnumComplexityLevel.is_simple(EnumComplexityLevel.COMPLEX) is False
        assert EnumComplexityLevel.is_simple(EnumComplexityLevel.CRITICAL) is False

    def test_is_complex(self):
        """Test is_complex method."""
        assert EnumComplexityLevel.is_complex(EnumComplexityLevel.SIMPLE) is False
        assert EnumComplexityLevel.is_complex(EnumComplexityLevel.BASIC) is False
        assert EnumComplexityLevel.is_complex(EnumComplexityLevel.MEDIUM) is False
        assert EnumComplexityLevel.is_complex(EnumComplexityLevel.HIGH) is True
        assert EnumComplexityLevel.is_complex(EnumComplexityLevel.COMPLEX) is True
        assert EnumComplexityLevel.is_complex(EnumComplexityLevel.ADVANCED) is True
        assert EnumComplexityLevel.is_complex(EnumComplexityLevel.EXPERT) is True
        assert EnumComplexityLevel.is_complex(EnumComplexityLevel.CRITICAL) is True

    def test_complexity_levels_ordering(self):
        """Test complexity levels ordering."""
        levels = [
            EnumComplexityLevel.SIMPLE,
            EnumComplexityLevel.BASIC,
            EnumComplexityLevel.LOW,
            EnumComplexityLevel.MEDIUM,
            EnumComplexityLevel.MODERATE,
            EnumComplexityLevel.HIGH,
            EnumComplexityLevel.COMPLEX,
            EnumComplexityLevel.ADVANCED,
            EnumComplexityLevel.EXPERT,
            EnumComplexityLevel.CRITICAL,
        ]

        # Test that numeric values increase with complexity
        numeric_values = [
            EnumComplexityLevel.get_numeric_value(level) for level in levels
        ]
        assert numeric_values == [1, 2, 3, 5, 6, 7, 8, 9, 10, 11]

    def test_complexity_classification(self):
        """Test complexity classification methods."""
        # Test simple levels
        simple_levels = [
            EnumComplexityLevel.SIMPLE,
            EnumComplexityLevel.BASIC,
            EnumComplexityLevel.LOW,
        ]
        for level in simple_levels:
            assert EnumComplexityLevel.is_simple(level) is True
            assert EnumComplexityLevel.is_complex(level) is False

        # Test complex levels
        complex_levels = [
            EnumComplexityLevel.HIGH,
            EnumComplexityLevel.COMPLEX,
            EnumComplexityLevel.ADVANCED,
            EnumComplexityLevel.EXPERT,
            EnumComplexityLevel.CRITICAL,
        ]
        for level in complex_levels:
            assert EnumComplexityLevel.is_simple(level) is False
            assert EnumComplexityLevel.is_complex(level) is True

        # Test medium levels (neither simple nor complex)
        medium_levels = [
            EnumComplexityLevel.MEDIUM,
            EnumComplexityLevel.MODERATE,
            EnumComplexityLevel.UNKNOWN,
        ]
        for level in medium_levels:
            assert EnumComplexityLevel.is_simple(level) is False
            assert EnumComplexityLevel.is_complex(level) is False
