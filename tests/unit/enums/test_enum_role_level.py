# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for EnumRoleLevel."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.enum_role_level import EnumRoleLevel


@pytest.mark.unit
class TestEnumRoleLevel:
    """Test suite for EnumRoleLevel."""

    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert EnumRoleLevel.INTERN == "intern"
        assert EnumRoleLevel.JUNIOR == "junior"
        assert EnumRoleLevel.MID == "mid"
        assert EnumRoleLevel.SENIOR == "senior"
        assert EnumRoleLevel.LEAD == "lead"
        assert EnumRoleLevel.PRINCIPAL == "principal"
        assert EnumRoleLevel.STAFF == "staff"
        assert EnumRoleLevel.DISTINGUISHED == "distinguished"
        assert EnumRoleLevel.FELLOW == "fellow"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumRoleLevel, str)
        assert issubclass(EnumRoleLevel, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        role = EnumRoleLevel.SENIOR
        assert isinstance(role, str)
        assert role == "senior"
        assert len(role) == 6

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumRoleLevel)
        assert len(values) == 9
        assert EnumRoleLevel.INTERN in values
        assert EnumRoleLevel.FELLOW in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumRoleLevel.PRINCIPAL in EnumRoleLevel
        assert "principal" in [e.value for e in EnumRoleLevel]

    def test_enum_comparison(self):
        """Test enum comparison."""
        role1 = EnumRoleLevel.LEAD
        role2 = EnumRoleLevel.LEAD
        role3 = EnumRoleLevel.STAFF

        assert role1 == role2
        assert role1 != role3
        assert role1 == "lead"

    def test_enum_serialization(self):
        """Test enum serialization."""
        role = EnumRoleLevel.DISTINGUISHED
        serialized = role.value
        assert serialized == "distinguished"
        json_str = json.dumps(role)
        assert json_str == '"distinguished"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        role = EnumRoleLevel("mid")
        assert role == EnumRoleLevel.MID

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumRoleLevel("invalid_role")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "intern",
            "junior",
            "mid",
            "senior",
            "lead",
            "principal",
            "staff",
            "distinguished",
            "fellow",
        }
        actual_values = {e.value for e in EnumRoleLevel}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert EnumRoleLevel.__doc__ is not None
        assert "role" in EnumRoleLevel.__doc__.lower()

    def test_entry_level_roles(self):
        """Test entry-level role grouping."""
        entry_level = {
            EnumRoleLevel.INTERN,
            EnumRoleLevel.JUNIOR,
        }
        assert all(role in EnumRoleLevel for role in entry_level)

    def test_mid_level_roles(self):
        """Test mid-level role grouping."""
        mid_level = {
            EnumRoleLevel.MID,
            EnumRoleLevel.SENIOR,
        }
        assert all(role in EnumRoleLevel for role in mid_level)

    def test_leadership_roles(self):
        """Test leadership role grouping."""
        leadership = {
            EnumRoleLevel.LEAD,
            EnumRoleLevel.PRINCIPAL,
        }
        assert all(role in EnumRoleLevel for role in leadership)

    def test_executive_roles(self):
        """Test executive/senior technical role grouping."""
        executive = {
            EnumRoleLevel.STAFF,
            EnumRoleLevel.DISTINGUISHED,
            EnumRoleLevel.FELLOW,
        }
        assert all(role in EnumRoleLevel for role in executive)

    def test_all_roles_categorized(self):
        """Test that all roles are properly categorized."""
        # Entry level
        entry = {
            EnumRoleLevel.INTERN,
            EnumRoleLevel.JUNIOR,
        }
        # Mid level
        mid = {
            EnumRoleLevel.MID,
            EnumRoleLevel.SENIOR,
        }
        # Leadership
        leadership = {
            EnumRoleLevel.LEAD,
            EnumRoleLevel.PRINCIPAL,
        }
        # Executive/Senior technical
        executive = {
            EnumRoleLevel.STAFF,
            EnumRoleLevel.DISTINGUISHED,
            EnumRoleLevel.FELLOW,
        }

        all_roles = entry | mid | leadership | executive
        assert all_roles == set(EnumRoleLevel)

    def test_role_progression(self):
        """Test typical role progression path."""
        # Typical progression path
        progression = [
            EnumRoleLevel.INTERN,
            EnumRoleLevel.JUNIOR,
            EnumRoleLevel.MID,
            EnumRoleLevel.SENIOR,
            EnumRoleLevel.LEAD,
            EnumRoleLevel.PRINCIPAL,
            EnumRoleLevel.STAFF,
            EnumRoleLevel.DISTINGUISHED,
            EnumRoleLevel.FELLOW,
        ]
        assert all(role in EnumRoleLevel for role in progression)
