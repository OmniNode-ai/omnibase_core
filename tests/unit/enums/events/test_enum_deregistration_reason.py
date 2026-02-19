# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for EnumDeregistrationReason.

Test coverage for deregistration reason enumeration and the is_planned() method.
"""

import pytest

from omnibase_core.enums import EnumDeregistrationReason


@pytest.mark.unit
class TestEnumDeregistrationReason:
    """Test cases for EnumDeregistrationReason enum."""

    def test_enum_values(self) -> None:
        """Test all enum values are present."""
        expected_values = {"shutdown", "upgrade", "manual"}
        actual_values = {reason.value for reason in EnumDeregistrationReason}
        assert actual_values == expected_values

    def test_string_inheritance(self) -> None:
        """Test that enum inherits from str."""
        assert isinstance(EnumDeregistrationReason.SHUTDOWN, str)
        assert EnumDeregistrationReason.SHUTDOWN == "shutdown"
        assert EnumDeregistrationReason.UPGRADE == "upgrade"
        assert EnumDeregistrationReason.MANUAL == "manual"

    def test_str_representation(self) -> None:
        """Test string representation returns the value."""
        for reason in EnumDeregistrationReason:
            assert str(reason) == reason.value


@pytest.mark.unit
class TestEnumDeregistrationReasonIsPlanned:
    """Test cases for EnumDeregistrationReason.is_planned() method."""

    def test_is_planned_shutdown(self) -> None:
        """Test SHUTDOWN is considered planned."""
        assert EnumDeregistrationReason.SHUTDOWN.is_planned() is True

    def test_is_planned_upgrade(self) -> None:
        """Test UPGRADE is considered planned."""
        assert EnumDeregistrationReason.UPGRADE.is_planned() is True

    def test_is_planned_manual(self) -> None:
        """Test MANUAL is considered planned."""
        assert EnumDeregistrationReason.MANUAL.is_planned() is True

    def test_all_enum_values_are_planned(self) -> None:
        """Test all standard enum values are considered planned."""
        for reason in EnumDeregistrationReason:
            assert reason.is_planned() is True
