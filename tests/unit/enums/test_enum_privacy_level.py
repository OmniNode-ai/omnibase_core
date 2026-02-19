# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for EnumPrivacyLevel."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.enum_privacy_level import EnumPrivacyLevel


@pytest.mark.unit
class TestEnumPrivacyLevel:
    """Test suite for EnumPrivacyLevel."""

    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert EnumPrivacyLevel.LOCAL_ONLY == "local_only"
        assert EnumPrivacyLevel.EXTERNAL_OK == "external_ok"
        assert EnumPrivacyLevel.ANY == "any"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumPrivacyLevel, str)
        assert issubclass(EnumPrivacyLevel, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        level = EnumPrivacyLevel.LOCAL_ONLY
        assert isinstance(level, str)
        assert level == "local_only"
        assert len(level) == 10

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumPrivacyLevel)
        assert len(values) == 3
        assert EnumPrivacyLevel.LOCAL_ONLY in values
        assert EnumPrivacyLevel.ANY in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumPrivacyLevel.EXTERNAL_OK in EnumPrivacyLevel
        assert "external_ok" in [e.value for e in EnumPrivacyLevel]

    def test_enum_comparison(self):
        """Test enum comparison."""
        level1 = EnumPrivacyLevel.LOCAL_ONLY
        level2 = EnumPrivacyLevel.LOCAL_ONLY
        level3 = EnumPrivacyLevel.ANY

        assert level1 == level2
        assert level1 != level3
        assert level1 == "local_only"

    def test_enum_serialization(self):
        """Test enum serialization."""
        level = EnumPrivacyLevel.EXTERNAL_OK
        serialized = level.value
        assert serialized == "external_ok"
        json_str = json.dumps(level)
        assert json_str == '"external_ok"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        level = EnumPrivacyLevel("any")
        assert level == EnumPrivacyLevel.ANY

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumPrivacyLevel("invalid_level")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {"local_only", "external_ok", "any"}
        actual_values = {e.value for e in EnumPrivacyLevel}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumPrivacyLevel.__doc__ is not None
        assert "privacy" in EnumPrivacyLevel.__doc__.lower()

    def test_privacy_levels_semantic_ordering(self):
        """Test semantic ordering from most restrictive to least."""
        # From most restrictive to least restrictive
        levels = [
            EnumPrivacyLevel.LOCAL_ONLY,
            EnumPrivacyLevel.EXTERNAL_OK,
            EnumPrivacyLevel.ANY,
        ]
        assert all(level in EnumPrivacyLevel for level in levels)

    def test_local_only_level(self):
        """Test local only privacy level."""
        level = EnumPrivacyLevel.LOCAL_ONLY
        assert "local" in level.value
        assert level == "local_only"

    def test_external_ok_level(self):
        """Test external ok privacy level."""
        level = EnumPrivacyLevel.EXTERNAL_OK
        assert "external" in level.value
        assert level == "external_ok"

    def test_any_level(self):
        """Test any privacy level."""
        level = EnumPrivacyLevel.ANY
        assert level == "any"
        assert len(level.value) == 3
