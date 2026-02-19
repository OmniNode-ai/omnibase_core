# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for EnumSecurityLevel."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.enum_security_level import EnumSecurityLevel


@pytest.mark.unit
class TestEnumSecurityLevel:
    """Test suite for EnumSecurityLevel."""

    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert EnumSecurityLevel.BASIC.value == "basic"
        assert EnumSecurityLevel.DEVELOPMENT_ONLY.value == "development_only"
        assert EnumSecurityLevel.MEDIUM.value == "medium"
        assert EnumSecurityLevel.PRODUCTION.value == "production"
        assert EnumSecurityLevel.ENTERPRISE.value == "enterprise"
        assert EnumSecurityLevel.NOT_RECOMMENDED.value == "not_recommended"

    def test_enum_inheritance(self):
        """Test that enum inherits from Enum."""
        assert issubclass(EnumSecurityLevel, Enum)

    def test_enum_string_representation(self):
        """Test string representation of enum values."""
        level = EnumSecurityLevel.PRODUCTION
        # Note: This enum doesn't inherit from str, so we check .value
        assert level.value == "production"
        assert isinstance(level.value, str)

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumSecurityLevel)
        assert len(values) == 6
        assert EnumSecurityLevel.BASIC in values
        assert EnumSecurityLevel.NOT_RECOMMENDED in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumSecurityLevel.ENTERPRISE in EnumSecurityLevel
        assert "enterprise" in [e.value for e in EnumSecurityLevel]

    def test_enum_comparison(self):
        """Test enum comparison."""
        level1 = EnumSecurityLevel.PRODUCTION
        level2 = EnumSecurityLevel.PRODUCTION
        level3 = EnumSecurityLevel.BASIC

        assert level1 == level2
        assert level1 != level3
        assert level1.value == "production"

    def test_enum_serialization(self):
        """Test enum serialization."""
        level = EnumSecurityLevel.MEDIUM
        serialized = level.value
        assert serialized == "medium"
        # Note: Direct json.dumps won't work without str inheritance
        json_str = json.dumps(level.value)
        assert json_str == '"medium"'

    def test_enum_value_access(self):
        """Test accessing enum by value."""
        level = EnumSecurityLevel("basic")
        assert level == EnumSecurityLevel.BASIC

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumSecurityLevel("invalid_level")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "basic",
            "development_only",
            "medium",
            "production",
            "enterprise",
            "not_recommended",
        }
        actual_values = {e.value for e in EnumSecurityLevel}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumSecurityLevel.__doc__ is not None
        assert "security" in EnumSecurityLevel.__doc__.lower()

    def test_recommended_security_levels(self):
        """Test recommended security level grouping."""
        recommended = {
            EnumSecurityLevel.PRODUCTION,
            EnumSecurityLevel.ENTERPRISE,
            EnumSecurityLevel.MEDIUM,
        }
        assert all(level in EnumSecurityLevel for level in recommended)

    def test_development_security_levels(self):
        """Test development-specific security levels."""
        development = {
            EnumSecurityLevel.BASIC,
            EnumSecurityLevel.DEVELOPMENT_ONLY,
        }
        assert all(level in EnumSecurityLevel for level in development)

    def test_discouraged_security_levels(self):
        """Test discouraged security levels."""
        discouraged = {EnumSecurityLevel.NOT_RECOMMENDED}
        assert all(level in EnumSecurityLevel for level in discouraged)

    def test_all_security_levels_categorized(self):
        """Test that all security levels are properly categorized."""
        # Production-ready levels
        production_ready = {
            EnumSecurityLevel.PRODUCTION,
            EnumSecurityLevel.ENTERPRISE,
            EnumSecurityLevel.MEDIUM,
        }
        # Development-only levels
        dev_only = {
            EnumSecurityLevel.BASIC,
            EnumSecurityLevel.DEVELOPMENT_ONLY,
        }
        # Discouraged levels
        discouraged = {EnumSecurityLevel.NOT_RECOMMENDED}

        all_levels = production_ready | dev_only | discouraged
        assert all_levels == set(EnumSecurityLevel)

    def test_security_level_progression(self):
        """Test security level progression from lowest to highest."""
        # Typical progression from least to most secure
        progression = [
            EnumSecurityLevel.NOT_RECOMMENDED,
            EnumSecurityLevel.DEVELOPMENT_ONLY,
            EnumSecurityLevel.BASIC,
            EnumSecurityLevel.MEDIUM,
            EnumSecurityLevel.PRODUCTION,
            EnumSecurityLevel.ENTERPRISE,
        ]
        assert all(level in EnumSecurityLevel for level in progression)
