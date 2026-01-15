"""
Test suite for util_datetime_parser.
"""

from datetime import datetime

import pytest

from omnibase_core.utils.util_datetime_parser import parse_datetime


@pytest.mark.unit
class TestUtilDatetimeParser:
    """Test parse_datetime functionality."""

    def test_parse_datetime_with_datetime_object(self):
        """Test parse_datetime with existing datetime object."""
        now = datetime.now()
        result = parse_datetime(now)

        assert result == now
        assert isinstance(result, datetime)

    def test_parse_datetime_with_iso_string(self):
        """Test parse_datetime with ISO format string."""
        iso_string = "2024-01-01T12:00:00"
        result = parse_datetime(iso_string)

        expected = datetime.fromisoformat(iso_string)
        assert result == expected
        assert isinstance(result, datetime)

    def test_parse_datetime_with_iso_string_z_suffix(self):
        """Test parse_datetime with ISO format string ending in Z."""
        iso_string = "2024-01-01T12:00:00Z"
        result = parse_datetime(iso_string)

        # Should convert Z to +00:00
        expected = datetime.fromisoformat("2024-01-01T12:00:00+00:00")
        assert result == expected
        assert isinstance(result, datetime)

    def test_parse_datetime_with_invalid_string(self):
        """Test parse_datetime with invalid string format."""
        invalid_string = "not-a-datetime"
        result = parse_datetime(invalid_string)

        # Should fallback to current datetime
        assert isinstance(result, datetime)
        # Should be recent (within last minute)
        now = datetime.now()
        time_diff = abs((now - result).total_seconds())
        assert time_diff < 60  # Within 1 minute

    def test_parse_datetime_with_empty_string(self):
        """Test parse_datetime with empty string."""
        empty_string = ""
        result = parse_datetime(empty_string)

        # Should fallback to current datetime
        assert isinstance(result, datetime)
        now = datetime.now()
        time_diff = abs((now - result).total_seconds())
        assert time_diff < 60  # Within 1 minute

    def test_parse_datetime_with_whitespace_string(self):
        """Test parse_datetime with whitespace-only string."""
        whitespace_string = "   "
        result = parse_datetime(whitespace_string)

        # Should fallback to current datetime
        assert isinstance(result, datetime)
        now = datetime.now()
        time_diff = abs((now - result).total_seconds())
        assert time_diff < 60  # Within 1 minute

    def test_parse_datetime_with_none(self):
        """Test parse_datetime with None value."""
        result = parse_datetime(None)

        # Should fallback to current datetime
        assert isinstance(result, datetime)
        now = datetime.now()
        time_diff = abs((now - result).total_seconds())
        assert time_diff < 60  # Within 1 minute

    def test_parse_datetime_with_non_string_non_datetime(self):
        """Test parse_datetime with non-string, non-datetime object."""
        result = parse_datetime(123)

        # Should fallback to current datetime
        assert isinstance(result, datetime)
        now = datetime.now()
        time_diff = abs((now - result).total_seconds())
        assert time_diff < 60  # Within 1 minute

    def test_parse_datetime_with_different_iso_formats(self):
        """Test parse_datetime with various ISO formats."""
        test_cases = [
            "2024-01-01T12:00:00",
            "2024-01-01T12:00:00Z",
            "2024-01-01T12:00:00+00:00",
            "2024-01-01T12:00:00-05:00",
        ]

        for iso_string in test_cases:
            result = parse_datetime(iso_string)
            assert isinstance(result, datetime)
            # Should be able to parse without error
            assert result.year == 2024
            assert result.month == 1
            assert result.day == 1

    def test_parse_datetime_consistency(self):
        """Test that parse_datetime is consistent for same input."""
        iso_string = "2024-01-01T12:00:00"
        result1 = parse_datetime(iso_string)
        result2 = parse_datetime(iso_string)

        assert result1 == result2

    def test_parse_datetime_with_microseconds(self):
        """Test parse_datetime with microseconds."""
        iso_string = "2024-01-01T12:00:00.123456"
        result = parse_datetime(iso_string)

        expected = datetime.fromisoformat(iso_string)
        assert result == expected
        assert result.microsecond == 123456

    def test_parse_datetime_with_timezone_info(self):
        """Test parse_datetime with timezone information."""
        iso_string = "2024-01-01T12:00:00+05:00"
        result = parse_datetime(iso_string)

        expected = datetime.fromisoformat(iso_string)
        assert result == expected
        assert result.tzinfo is not None
