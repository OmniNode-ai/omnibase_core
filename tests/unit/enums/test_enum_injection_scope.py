# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for EnumInjectionScope."""

from enum import Enum

import pytest

from omnibase_core.enums.enum_injection_scope import EnumInjectionScope


@pytest.mark.unit
class TestEnumInjectionScope:
    """Test suite for EnumInjectionScope enumeration."""

    def test_string_returns_value(self) -> None:
        """Test that str() returns the .value (StrValueHelper behavior)."""
        assert str(EnumInjectionScope.GLOBAL) == "global"
        assert str(EnumInjectionScope.REQUEST) == "request"
        assert str(EnumInjectionScope.SESSION) == "session"
        assert str(EnumInjectionScope.THREAD) == "thread"
        assert str(EnumInjectionScope.PROCESS) == "process"
        assert str(EnumInjectionScope.CUSTOM) == "custom"

    def test_value_property(self) -> None:
        """Test that .value returns the correct string."""
        assert EnumInjectionScope.REQUEST.value == "request"
        assert EnumInjectionScope.SESSION.value == "session"
        assert EnumInjectionScope.THREAD.value == "thread"
        assert EnumInjectionScope.PROCESS.value == "process"
        assert EnumInjectionScope.GLOBAL.value == "global"
        assert EnumInjectionScope.CUSTOM.value == "custom"

    def test_all_members_exist(self) -> None:
        """Test that all expected enum members exist."""
        values = [m.value for m in EnumInjectionScope]
        assert "request" in values
        assert "session" in values
        assert "thread" in values
        assert "process" in values
        assert "global" in values
        assert "custom" in values

    def test_unique_values(self) -> None:
        """Test that all enum values are unique."""
        values = [m.value for m in EnumInjectionScope]
        assert len(values) == len(set(values))

    def test_enum_count(self) -> None:
        """Test that enum has exactly 6 members."""
        members = list(EnumInjectionScope)
        assert len(members) == 6

    def test_enum_inheritance(self) -> None:
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumInjectionScope, str)
        assert issubclass(EnumInjectionScope, Enum)

    def test_enum_string_equality(self) -> None:
        """Test that enum members equal their string values."""
        assert EnumInjectionScope.REQUEST == "request"
        assert EnumInjectionScope.SESSION == "session"
        assert EnumInjectionScope.THREAD == "thread"
        assert EnumInjectionScope.PROCESS == "process"
        assert EnumInjectionScope.GLOBAL == "global"
        assert EnumInjectionScope.CUSTOM == "custom"

    def test_enum_comparison(self) -> None:
        """Test enum member equality."""
        scope1 = EnumInjectionScope.GLOBAL
        scope2 = EnumInjectionScope.GLOBAL
        scope3 = EnumInjectionScope.REQUEST

        assert scope1 == scope2
        assert scope1 != scope3
        assert scope1 is scope2

    def test_enum_membership(self) -> None:
        """Test membership testing."""
        assert EnumInjectionScope.GLOBAL in EnumInjectionScope
        assert "global" in EnumInjectionScope
        assert "invalid_scope" not in EnumInjectionScope

    def test_enum_deserialization(self) -> None:
        """Test enum deserialization from string."""
        assert EnumInjectionScope("request") == EnumInjectionScope.REQUEST
        assert EnumInjectionScope("global") == EnumInjectionScope.GLOBAL

    def test_enum_invalid_values(self) -> None:
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumInjectionScope("invalid_scope")

        with pytest.raises(ValueError):
            EnumInjectionScope("")
