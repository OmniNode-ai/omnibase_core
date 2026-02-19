# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for EnumServiceLifecycle."""

from enum import Enum

import pytest

from omnibase_core.enums.enum_service_lifecycle import EnumServiceLifecycle


@pytest.mark.unit
class TestEnumServiceLifecycle:
    """Test suite for EnumServiceLifecycle enumeration."""

    def test_string_returns_value(self) -> None:
        """Test that str() returns the .value (StrValueHelper behavior)."""
        assert str(EnumServiceLifecycle.SINGLETON) == "singleton"
        assert str(EnumServiceLifecycle.TRANSIENT) == "transient"
        assert str(EnumServiceLifecycle.SCOPED) == "scoped"
        assert str(EnumServiceLifecycle.POOLED) == "pooled"
        assert str(EnumServiceLifecycle.LAZY) == "lazy"
        assert str(EnumServiceLifecycle.EAGER) == "eager"

    def test_value_property(self) -> None:
        """Test that .value returns the correct string."""
        assert EnumServiceLifecycle.SINGLETON.value == "singleton"
        assert EnumServiceLifecycle.TRANSIENT.value == "transient"
        assert EnumServiceLifecycle.SCOPED.value == "scoped"
        assert EnumServiceLifecycle.POOLED.value == "pooled"
        assert EnumServiceLifecycle.LAZY.value == "lazy"
        assert EnumServiceLifecycle.EAGER.value == "eager"

    def test_all_members_exist(self) -> None:
        """Test that all expected enum members exist."""
        values = [m.value for m in EnumServiceLifecycle]
        assert "singleton" in values
        assert "transient" in values
        assert "scoped" in values
        assert "pooled" in values
        assert "lazy" in values
        assert "eager" in values

    def test_unique_values(self) -> None:
        """Test that all enum values are unique."""
        values = [m.value for m in EnumServiceLifecycle]
        assert len(values) == len(set(values))

    def test_enum_count(self) -> None:
        """Test that enum has exactly 6 members."""
        members = list(EnumServiceLifecycle)
        assert len(members) == 6

    def test_enum_inheritance(self) -> None:
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumServiceLifecycle, str)
        assert issubclass(EnumServiceLifecycle, Enum)

    def test_enum_string_equality(self) -> None:
        """Test that enum members equal their string values."""
        assert EnumServiceLifecycle.SINGLETON == "singleton"
        assert EnumServiceLifecycle.TRANSIENT == "transient"
        assert EnumServiceLifecycle.SCOPED == "scoped"
        assert EnumServiceLifecycle.POOLED == "pooled"
        assert EnumServiceLifecycle.LAZY == "lazy"
        assert EnumServiceLifecycle.EAGER == "eager"

    def test_enum_comparison(self) -> None:
        """Test enum member equality."""
        lifecycle1 = EnumServiceLifecycle.SINGLETON
        lifecycle2 = EnumServiceLifecycle.SINGLETON
        lifecycle3 = EnumServiceLifecycle.TRANSIENT

        assert lifecycle1 == lifecycle2
        assert lifecycle1 != lifecycle3
        assert lifecycle1 is lifecycle2

    def test_enum_membership(self) -> None:
        """Test membership testing."""
        assert EnumServiceLifecycle.SINGLETON in EnumServiceLifecycle
        assert "singleton" in EnumServiceLifecycle
        assert "invalid_lifecycle" not in EnumServiceLifecycle

    def test_enum_deserialization(self) -> None:
        """Test enum deserialization from string."""
        assert EnumServiceLifecycle("singleton") == EnumServiceLifecycle.SINGLETON
        assert EnumServiceLifecycle("transient") == EnumServiceLifecycle.TRANSIENT

    def test_enum_invalid_values(self) -> None:
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumServiceLifecycle("invalid_lifecycle")

        with pytest.raises(ValueError):
            EnumServiceLifecycle("")
