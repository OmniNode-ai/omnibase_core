# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for enum_message_role.py"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_message_role import EnumMessageRole


@pytest.mark.unit
class TestEnumMessageRole:
    """Test cases for EnumMessageRole"""

    def test_enum_values(self):
        """Test that all enum values are correct"""
        assert EnumMessageRole.USER == "user"
        assert EnumMessageRole.SYSTEM == "system"
        assert EnumMessageRole.ASSISTANT == "assistant"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum"""
        assert issubclass(EnumMessageRole, str)
        assert issubclass(EnumMessageRole, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values"""
        assert EnumMessageRole.USER == "user"
        assert EnumMessageRole.SYSTEM == "system"
        assert EnumMessageRole.ASSISTANT == "assistant"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values"""
        values = list(EnumMessageRole)
        assert len(values) == 3
        assert EnumMessageRole.USER in values
        assert EnumMessageRole.ASSISTANT in values

    def test_enum_membership(self):
        """Test membership testing"""
        assert EnumMessageRole.USER in EnumMessageRole
        assert "user" in EnumMessageRole
        assert "invalid_value" not in EnumMessageRole

    def test_enum_comparison(self):
        """Test enum comparison"""
        assert EnumMessageRole.USER == EnumMessageRole.USER
        assert EnumMessageRole.SYSTEM != EnumMessageRole.USER
        assert EnumMessageRole.USER == "user"

    def test_enum_serialization(self):
        """Test enum serialization"""
        assert EnumMessageRole.USER.value == "user"
        assert EnumMessageRole.SYSTEM.value == "system"

    def test_enum_deserialization(self):
        """Test enum deserialization"""
        assert EnumMessageRole("user") == EnumMessageRole.USER
        assert EnumMessageRole("system") == EnumMessageRole.SYSTEM

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError"""
        with pytest.raises(ValueError):
            EnumMessageRole("invalid_value")

        with pytest.raises(ValueError):
            EnumMessageRole("")

    def test_enum_all_values(self):
        """Test that all expected values are present"""
        expected_values = {"user", "system", "assistant"}
        actual_values = {member.value for member in EnumMessageRole}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring"""
        assert "Message roles for LLM chat conversations" in EnumMessageRole.__doc__

    def test_enum_message_roles(self):
        """Test specific message roles"""
        # User role
        assert EnumMessageRole.USER.value == "user"

        # System role
        assert EnumMessageRole.SYSTEM.value == "system"

        # Assistant role
        assert EnumMessageRole.ASSISTANT.value == "assistant"

    def test_enum_role_categories(self):
        """Test message role categories"""
        # Human roles
        human_roles = {EnumMessageRole.USER}

        # AI roles
        ai_roles = {EnumMessageRole.ASSISTANT}

        # System roles
        system_roles = {EnumMessageRole.SYSTEM}

        all_roles = set(EnumMessageRole)
        assert human_roles.union(ai_roles).union(system_roles) == all_roles
