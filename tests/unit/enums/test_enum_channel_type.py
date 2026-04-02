# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for EnumChannelType enum."""

from enum import Enum

import pytest

from omnibase_core.enums.enum_channel_type import EnumChannelType


@pytest.mark.unit
class TestEnumChannelType:
    """Test cases for EnumChannelType enum."""

    def test_enum_values(self) -> None:
        """Test that enum has expected values."""
        assert EnumChannelType.DISCORD == "discord"
        assert EnumChannelType.SLACK == "slack"
        assert EnumChannelType.TELEGRAM == "telegram"
        assert EnumChannelType.EMAIL == "email"
        assert EnumChannelType.SMS == "sms"
        assert EnumChannelType.MATRIX == "matrix"

    def test_enum_inheritance(self) -> None:
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumChannelType, str)
        assert issubclass(EnumChannelType, Enum)

    def test_enum_string_behavior(self) -> None:
        """Test that enum values behave as strings."""
        channel = EnumChannelType.DISCORD
        assert isinstance(channel, str)
        assert channel == "discord"

    def test_enum_member_count(self) -> None:
        """Test that enum has exactly 6 members."""
        values = list(EnumChannelType)
        assert len(values) == 6

    def test_enum_all_values(self) -> None:
        """Test that all expected values are present."""
        expected = {"discord", "slack", "telegram", "email", "sms", "matrix"}
        actual = {member.value for member in EnumChannelType}
        assert actual == expected

    def test_enum_membership(self) -> None:
        """Test enum membership operations."""
        assert "discord" in EnumChannelType
        assert "whatsapp" not in EnumChannelType

    def test_enum_deserialization(self) -> None:
        """Test that enum can be created from string values."""
        assert EnumChannelType("slack") == EnumChannelType.SLACK

    def test_enum_invalid_value(self) -> None:
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumChannelType("whatsapp")

    def test_str_representation(self) -> None:
        """Test that str() returns the value."""
        assert str(EnumChannelType.DISCORD) == "discord"

    def test_importable_from_enums_package(self) -> None:
        """Test that EnumChannelType is exported from enums package."""
        from omnibase_core.enums import EnumChannelType as Imported

        assert Imported is EnumChannelType
