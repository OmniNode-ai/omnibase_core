"""
Tests for EnumErrorCategory enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_error_category import EnumErrorCategory


@pytest.mark.unit
class TestEnumErrorCategory:
    """Test cases for EnumErrorCategory enum."""

    def test_enum_values(self):
        """Test that all enum values are correct."""
        assert EnumErrorCategory.TRANSIENT == "transient"
        assert EnumErrorCategory.CONFIGURATION == "configuration"
        assert EnumErrorCategory.RESOURCE_EXHAUSTION == "resource_exhaustion"
        assert EnumErrorCategory.AUTHENTICATION == "authentication"
        assert EnumErrorCategory.NETWORK == "network"
        assert EnumErrorCategory.VALIDATION == "validation"
        assert EnumErrorCategory.SYSTEM == "system"
        assert EnumErrorCategory.UNKNOWN == "unknown"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumErrorCategory, str)
        assert issubclass(EnumErrorCategory, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        assert str(EnumErrorCategory.TRANSIENT) == "EnumErrorCategory.TRANSIENT"
        assert str(EnumErrorCategory.CONFIGURATION) == "EnumErrorCategory.CONFIGURATION"
        assert (
            str(EnumErrorCategory.RESOURCE_EXHAUSTION)
            == "EnumErrorCategory.RESOURCE_EXHAUSTION"
        )
        assert (
            str(EnumErrorCategory.AUTHENTICATION) == "EnumErrorCategory.AUTHENTICATION"
        )
        assert str(EnumErrorCategory.NETWORK) == "EnumErrorCategory.NETWORK"
        assert str(EnumErrorCategory.VALIDATION) == "EnumErrorCategory.VALIDATION"
        assert str(EnumErrorCategory.SYSTEM) == "EnumErrorCategory.SYSTEM"
        assert str(EnumErrorCategory.UNKNOWN) == "EnumErrorCategory.UNKNOWN"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values."""
        values = list(EnumErrorCategory)
        assert len(values) == 8
        assert EnumErrorCategory.TRANSIENT in values
        assert EnumErrorCategory.CONFIGURATION in values
        assert EnumErrorCategory.RESOURCE_EXHAUSTION in values
        assert EnumErrorCategory.AUTHENTICATION in values
        assert EnumErrorCategory.NETWORK in values
        assert EnumErrorCategory.VALIDATION in values
        assert EnumErrorCategory.SYSTEM in values
        assert EnumErrorCategory.UNKNOWN in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert "transient" in EnumErrorCategory
        assert "configuration" in EnumErrorCategory
        assert "resource_exhaustion" in EnumErrorCategory
        assert "authentication" in EnumErrorCategory
        assert "network" in EnumErrorCategory
        assert "validation" in EnumErrorCategory
        assert "system" in EnumErrorCategory
        assert "unknown" in EnumErrorCategory
        assert "invalid" not in EnumErrorCategory

    def test_enum_comparison(self):
        """Test enum comparison."""
        assert EnumErrorCategory.TRANSIENT == "transient"
        assert EnumErrorCategory.CONFIGURATION == "configuration"
        assert EnumErrorCategory.RESOURCE_EXHAUSTION == "resource_exhaustion"
        assert EnumErrorCategory.AUTHENTICATION == "authentication"
        assert EnumErrorCategory.NETWORK == "network"
        assert EnumErrorCategory.VALIDATION == "validation"
        assert EnumErrorCategory.SYSTEM == "system"
        assert EnumErrorCategory.UNKNOWN == "unknown"

    def test_enum_serialization(self):
        """Test enum serialization."""
        assert EnumErrorCategory.TRANSIENT.value == "transient"
        assert EnumErrorCategory.CONFIGURATION.value == "configuration"
        assert EnumErrorCategory.RESOURCE_EXHAUSTION.value == "resource_exhaustion"
        assert EnumErrorCategory.AUTHENTICATION.value == "authentication"
        assert EnumErrorCategory.NETWORK.value == "network"
        assert EnumErrorCategory.VALIDATION.value == "validation"
        assert EnumErrorCategory.SYSTEM.value == "system"
        assert EnumErrorCategory.UNKNOWN.value == "unknown"

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        assert EnumErrorCategory("transient") == EnumErrorCategory.TRANSIENT
        assert EnumErrorCategory("configuration") == EnumErrorCategory.CONFIGURATION
        assert (
            EnumErrorCategory("resource_exhaustion")
            == EnumErrorCategory.RESOURCE_EXHAUSTION
        )
        assert EnumErrorCategory("authentication") == EnumErrorCategory.AUTHENTICATION
        assert EnumErrorCategory("network") == EnumErrorCategory.NETWORK
        assert EnumErrorCategory("validation") == EnumErrorCategory.VALIDATION
        assert EnumErrorCategory("system") == EnumErrorCategory.SYSTEM
        assert EnumErrorCategory("unknown") == EnumErrorCategory.UNKNOWN

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumErrorCategory("invalid")

    def test_enum_all_values(self):
        """Test that all enum values are accessible."""
        all_values = [category.value for category in EnumErrorCategory]
        expected_values = [
            "transient",
            "configuration",
            "resource_exhaustion",
            "authentication",
            "network",
            "validation",
            "system",
            "unknown",
        ]
        assert set(all_values) == set(expected_values)

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert "Error categories for task queue operations" in EnumErrorCategory.__doc__
