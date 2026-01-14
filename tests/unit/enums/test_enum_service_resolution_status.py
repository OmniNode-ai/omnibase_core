"""Unit tests for EnumServiceResolutionStatus."""

from enum import Enum

import pytest

from omnibase_core.enums.enum_service_resolution_status import (
    EnumServiceResolutionStatus,
)


@pytest.mark.unit
class TestEnumServiceResolutionStatus:
    """Test suite for EnumServiceResolutionStatus enumeration."""

    def test_string_returns_value(self) -> None:
        """Test that str() returns the .value (StrValueHelper behavior)."""
        assert str(EnumServiceResolutionStatus.RESOLVED) == "resolved"
        assert str(EnumServiceResolutionStatus.FAILED) == "failed"
        assert (
            str(EnumServiceResolutionStatus.CIRCULAR_DEPENDENCY)
            == "circular_dependency"
        )
        assert (
            str(EnumServiceResolutionStatus.MISSING_DEPENDENCY) == "missing_dependency"
        )
        assert str(EnumServiceResolutionStatus.TYPE_MISMATCH) == "type_mismatch"

    def test_value_property(self) -> None:
        """Test that .value returns the correct string."""
        assert EnumServiceResolutionStatus.RESOLVED.value == "resolved"
        assert EnumServiceResolutionStatus.FAILED.value == "failed"
        assert (
            EnumServiceResolutionStatus.CIRCULAR_DEPENDENCY.value
            == "circular_dependency"
        )
        assert (
            EnumServiceResolutionStatus.MISSING_DEPENDENCY.value == "missing_dependency"
        )
        assert EnumServiceResolutionStatus.TYPE_MISMATCH.value == "type_mismatch"

    def test_all_members_exist(self) -> None:
        """Test that all expected enum members exist."""
        values = [m.value for m in EnumServiceResolutionStatus]
        assert "resolved" in values
        assert "failed" in values
        assert "circular_dependency" in values
        assert "missing_dependency" in values
        assert "type_mismatch" in values

    def test_unique_values(self) -> None:
        """Test that all enum values are unique."""
        values = [m.value for m in EnumServiceResolutionStatus]
        assert len(values) == len(set(values))

    def test_enum_count(self) -> None:
        """Test that enum has exactly 5 members."""
        members = list(EnumServiceResolutionStatus)
        assert len(members) == 5

    def test_enum_inheritance(self) -> None:
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumServiceResolutionStatus, str)
        assert issubclass(EnumServiceResolutionStatus, Enum)

    def test_enum_string_equality(self) -> None:
        """Test that enum members equal their string values."""
        assert EnumServiceResolutionStatus.RESOLVED == "resolved"
        assert EnumServiceResolutionStatus.FAILED == "failed"
        assert EnumServiceResolutionStatus.CIRCULAR_DEPENDENCY == "circular_dependency"
        assert EnumServiceResolutionStatus.MISSING_DEPENDENCY == "missing_dependency"
        assert EnumServiceResolutionStatus.TYPE_MISMATCH == "type_mismatch"

    def test_enum_comparison(self) -> None:
        """Test enum member equality."""
        status1 = EnumServiceResolutionStatus.RESOLVED
        status2 = EnumServiceResolutionStatus.RESOLVED
        status3 = EnumServiceResolutionStatus.FAILED

        assert status1 == status2
        assert status1 != status3
        assert status1 is status2

    def test_enum_membership(self) -> None:
        """Test membership testing."""
        assert EnumServiceResolutionStatus.RESOLVED in EnumServiceResolutionStatus
        assert "resolved" in EnumServiceResolutionStatus
        assert "invalid_status" not in EnumServiceResolutionStatus

    def test_enum_deserialization(self) -> None:
        """Test enum deserialization from string."""
        assert (
            EnumServiceResolutionStatus("resolved")
            == EnumServiceResolutionStatus.RESOLVED
        )
        assert (
            EnumServiceResolutionStatus("circular_dependency")
            == EnumServiceResolutionStatus.CIRCULAR_DEPENDENCY
        )

    def test_enum_invalid_values(self) -> None:
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumServiceResolutionStatus("invalid_status")

        with pytest.raises(ValueError):
            EnumServiceResolutionStatus("")
