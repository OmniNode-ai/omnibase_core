"""
Tests for EnumFileStampStatus enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_file_stamp_status import EnumFileStampStatus


@pytest.mark.unit
class TestEnumFileStampStatus:
    """Test cases for EnumFileStampStatus enum."""

    def test_enum_values(self):
        """Test that all enum values are correct."""
        assert EnumFileStampStatus.VALID.value == "VALID"
        assert EnumFileStampStatus.INVALID.value == "INVALID"
        assert EnumFileStampStatus.MISSING.value == "MISSING"
        assert EnumFileStampStatus.EXPIRED.value == "EXPIRED"
        assert EnumFileStampStatus.CORRUPTED.value == "CORRUPTED"

    def test_enum_inheritance(self):
        """Test that enum inherits from Enum."""
        assert issubclass(EnumFileStampStatus, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        assert str(EnumFileStampStatus.VALID) == "EnumFileStampStatus.VALID"
        assert str(EnumFileStampStatus.INVALID) == "EnumFileStampStatus.INVALID"
        assert str(EnumFileStampStatus.MISSING) == "EnumFileStampStatus.MISSING"
        assert str(EnumFileStampStatus.EXPIRED) == "EnumFileStampStatus.EXPIRED"
        assert str(EnumFileStampStatus.CORRUPTED) == "EnumFileStampStatus.CORRUPTED"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values."""
        values = list(EnumFileStampStatus)
        assert len(values) == 5
        assert EnumFileStampStatus.VALID in values
        assert EnumFileStampStatus.INVALID in values
        assert EnumFileStampStatus.MISSING in values
        assert EnumFileStampStatus.EXPIRED in values
        assert EnumFileStampStatus.CORRUPTED in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert "VALID" in EnumFileStampStatus
        assert "INVALID" in EnumFileStampStatus
        assert "MISSING" in EnumFileStampStatus
        assert "EXPIRED" in EnumFileStampStatus
        assert "CORRUPTED" in EnumFileStampStatus
        assert "invalid" not in EnumFileStampStatus

    def test_enum_comparison(self):
        """Test enum comparison."""
        assert EnumFileStampStatus.VALID.value == "VALID"
        assert EnumFileStampStatus.INVALID.value == "INVALID"
        assert EnumFileStampStatus.MISSING.value == "MISSING"
        assert EnumFileStampStatus.EXPIRED.value == "EXPIRED"
        assert EnumFileStampStatus.CORRUPTED.value == "CORRUPTED"

    def test_enum_serialization(self):
        """Test enum serialization."""
        assert EnumFileStampStatus.VALID.value == "VALID"
        assert EnumFileStampStatus.INVALID.value == "INVALID"
        assert EnumFileStampStatus.MISSING.value == "MISSING"
        assert EnumFileStampStatus.EXPIRED.value == "EXPIRED"
        assert EnumFileStampStatus.CORRUPTED.value == "CORRUPTED"

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        assert EnumFileStampStatus("VALID") == EnumFileStampStatus.VALID
        assert EnumFileStampStatus("INVALID") == EnumFileStampStatus.INVALID
        assert EnumFileStampStatus("MISSING") == EnumFileStampStatus.MISSING
        assert EnumFileStampStatus("EXPIRED") == EnumFileStampStatus.EXPIRED
        assert EnumFileStampStatus("CORRUPTED") == EnumFileStampStatus.CORRUPTED

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumFileStampStatus("invalid")

    def test_enum_all_values(self):
        """Test that all enum values are accessible."""
        all_values = [status.value for status in EnumFileStampStatus]
        expected_values = ["VALID", "INVALID", "MISSING", "EXPIRED", "CORRUPTED"]
        assert set(all_values) == set(expected_values)

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert "File stamp status indicators" in EnumFileStampStatus.__doc__
