"""Unit tests for EnumRegistrationStatus."""

from enum import Enum

import pytest

from omnibase_core.enums.enum_registration_status import EnumRegistrationStatus


@pytest.mark.unit
class TestEnumRegistrationStatus:
    """Test suite for EnumRegistrationStatus enumeration."""

    def test_string_returns_value(self) -> None:
        """Test that str() returns the .value (StrValueHelper behavior)."""
        assert str(EnumRegistrationStatus.REGISTERED) == "registered"
        assert str(EnumRegistrationStatus.UNREGISTERED) == "unregistered"
        assert str(EnumRegistrationStatus.FAILED) == "failed"
        assert str(EnumRegistrationStatus.PENDING) == "pending"
        assert str(EnumRegistrationStatus.CONFLICT) == "conflict"
        assert str(EnumRegistrationStatus.INVALID) == "invalid"

    def test_value_property(self) -> None:
        """Test that .value returns the correct string."""
        assert EnumRegistrationStatus.REGISTERED.value == "registered"
        assert EnumRegistrationStatus.UNREGISTERED.value == "unregistered"
        assert EnumRegistrationStatus.FAILED.value == "failed"
        assert EnumRegistrationStatus.PENDING.value == "pending"
        assert EnumRegistrationStatus.CONFLICT.value == "conflict"
        assert EnumRegistrationStatus.INVALID.value == "invalid"

    def test_all_members_exist(self) -> None:
        """Test that all expected enum members exist."""
        values = [m.value for m in EnumRegistrationStatus]
        assert "registered" in values
        assert "unregistered" in values
        assert "failed" in values
        assert "pending" in values
        assert "conflict" in values
        assert "invalid" in values

    def test_unique_values(self) -> None:
        """Test that all enum values are unique."""
        values = [m.value for m in EnumRegistrationStatus]
        assert len(values) == len(set(values))

    def test_enum_count(self) -> None:
        """Test that enum has exactly 6 members."""
        members = list(EnumRegistrationStatus)
        assert len(members) == 6

    def test_enum_inheritance(self) -> None:
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumRegistrationStatus, str)
        assert issubclass(EnumRegistrationStatus, Enum)

    def test_enum_string_equality(self) -> None:
        """Test that enum members equal their string values."""
        assert EnumRegistrationStatus.REGISTERED == "registered"
        assert EnumRegistrationStatus.UNREGISTERED == "unregistered"
        assert EnumRegistrationStatus.FAILED == "failed"
        assert EnumRegistrationStatus.PENDING == "pending"
        assert EnumRegistrationStatus.CONFLICT == "conflict"
        assert EnumRegistrationStatus.INVALID == "invalid"

    def test_enum_comparison(self) -> None:
        """Test enum member equality."""
        status1 = EnumRegistrationStatus.REGISTERED
        status2 = EnumRegistrationStatus.REGISTERED
        status3 = EnumRegistrationStatus.FAILED

        assert status1 == status2
        assert status1 != status3
        assert status1 is status2

    def test_enum_membership(self) -> None:
        """Test membership testing."""
        assert EnumRegistrationStatus.REGISTERED in EnumRegistrationStatus
        assert "registered" in EnumRegistrationStatus
        assert "invalid_status" not in EnumRegistrationStatus

    def test_enum_deserialization(self) -> None:
        """Test enum deserialization from string."""
        assert EnumRegistrationStatus("registered") == EnumRegistrationStatus.REGISTERED
        assert EnumRegistrationStatus("failed") == EnumRegistrationStatus.FAILED

    def test_enum_invalid_values(self) -> None:
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumRegistrationStatus("invalid_status")

        with pytest.raises(ValueError):
            EnumRegistrationStatus("")
