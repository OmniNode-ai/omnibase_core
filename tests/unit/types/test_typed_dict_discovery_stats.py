"""
Test suite for TypedDictDiscoveryStats.
"""

import pytest

from omnibase_core.types.typed_dict_discovery_stats import TypedDictDiscoveryStats


class TestTypedDictDiscoveryStats:
    """Test TypedDictDiscoveryStats functionality."""

    def test_typed_dict_discovery_stats_structure(self):
        """Verify TypedDict accepts correct structure."""
        stats: TypedDictDiscoveryStats = {
            "requests_received": 5,
            "responses_sent": 3,
            "throttled_requests": 2,
            "last_request_time": 1234.56,
            "error_count": 1,
        }
        assert stats["requests_received"] == 5
        assert stats["responses_sent"] == 3
        assert stats["throttled_requests"] == 2
        assert stats["last_request_time"] == 1234.56
        assert stats["error_count"] == 1

    def test_typed_dict_last_request_none(self):
        """Verify None handling for last_request_time."""
        stats: TypedDictDiscoveryStats = {
            "requests_received": 0,
            "responses_sent": 0,
            "throttled_requests": 0,
            "last_request_time": None,
            "error_count": 0,
        }
        assert stats["last_request_time"] is None

    def test_typed_dict_all_fields_required(self):
        """Verify all fields are required."""
        # This test documents the structure
        stats: TypedDictDiscoveryStats = {
            "requests_received": 1,
            "responses_sent": 1,
            "throttled_requests": 0,
            "last_request_time": 1.0,
            "error_count": 0,
        }
        assert len(stats) == 5

    def test_typed_dict_zero_values(self):
        """Test TypedDict with all zero values."""
        stats: TypedDictDiscoveryStats = {
            "requests_received": 0,
            "responses_sent": 0,
            "throttled_requests": 0,
            "last_request_time": None,
            "error_count": 0,
        }
        assert stats["requests_received"] == 0
        assert stats["responses_sent"] == 0
        assert stats["throttled_requests"] == 0
        assert stats["last_request_time"] is None
        assert stats["error_count"] == 0

    def test_typed_dict_high_volume_stats(self):
        """Test TypedDict with high volume statistics."""
        stats: TypedDictDiscoveryStats = {
            "requests_received": 10000,
            "responses_sent": 9500,
            "throttled_requests": 500,
            "last_request_time": 1234567890.123456,
            "error_count": 50,
        }
        assert stats["requests_received"] == 10000
        assert stats["responses_sent"] == 9500
        assert stats["throttled_requests"] == 500
        assert stats["last_request_time"] == 1234567890.123456
        assert stats["error_count"] == 50

    def test_typed_dict_partial_throttling(self):
        """Test TypedDict with partial throttling scenario."""
        stats: TypedDictDiscoveryStats = {
            "requests_received": 100,
            "responses_sent": 80,
            "throttled_requests": 20,
            "last_request_time": 1640000000.0,
            "error_count": 0,
        }
        assert (
            stats["requests_received"]
            == stats["responses_sent"] + stats["throttled_requests"]
        )

    def test_typed_dict_error_tracking(self):
        """Test TypedDict with error count tracking."""
        stats: TypedDictDiscoveryStats = {
            "requests_received": 50,
            "responses_sent": 45,
            "throttled_requests": 0,
            "last_request_time": 1640000000.0,
            "error_count": 5,
        }
        assert stats["error_count"] == 5
        assert (
            stats["error_count"] == stats["requests_received"] - stats["responses_sent"]
        )

    def test_typed_dict_field_types(self):
        """Test that all fields have correct types."""
        stats: TypedDictDiscoveryStats = {
            "requests_received": 10,
            "responses_sent": 8,
            "throttled_requests": 2,
            "last_request_time": 1234.56,
            "error_count": 0,
        }
        assert isinstance(stats["requests_received"], int)
        assert isinstance(stats["responses_sent"], int)
        assert isinstance(stats["throttled_requests"], int)
        assert isinstance(stats["last_request_time"], float)
        assert isinstance(stats["error_count"], int)

    def test_typed_dict_field_types_with_none(self):
        """Test field types with None value for optional field."""
        stats: TypedDictDiscoveryStats = {
            "requests_received": 10,
            "responses_sent": 8,
            "throttled_requests": 2,
            "last_request_time": None,
            "error_count": 0,
        }
        assert isinstance(stats["requests_received"], int)
        assert isinstance(stats["responses_sent"], int)
        assert isinstance(stats["throttled_requests"], int)
        assert stats["last_request_time"] is None
        assert isinstance(stats["error_count"], int)

    def test_typed_dict_incremental_updates(self):
        """Test TypedDict with incremental counter updates."""
        stats: TypedDictDiscoveryStats = {
            "requests_received": 0,
            "responses_sent": 0,
            "throttled_requests": 0,
            "last_request_time": None,
            "error_count": 0,
        }
        # Simulate incremental updates
        stats["requests_received"] += 1
        stats["responses_sent"] += 1
        stats["last_request_time"] = 1640000000.0

        assert stats["requests_received"] == 1
        assert stats["responses_sent"] == 1
        assert stats["last_request_time"] == 1640000000.0

    def test_typed_dict_throttling_scenario(self):
        """Test TypedDict with throttling scenario."""
        stats: TypedDictDiscoveryStats = {
            "requests_received": 0,
            "responses_sent": 0,
            "throttled_requests": 0,
            "last_request_time": None,
            "error_count": 0,
        }
        # Simulate receiving request but throttling response
        stats["requests_received"] += 1
        stats["throttled_requests"] += 1
        stats["last_request_time"] = 1640000000.0

        assert stats["requests_received"] == 1
        assert stats["responses_sent"] == 0
        assert stats["throttled_requests"] == 1

    def test_typed_dict_error_scenario(self):
        """Test TypedDict with error tracking scenario."""
        stats: TypedDictDiscoveryStats = {
            "requests_received": 0,
            "responses_sent": 0,
            "throttled_requests": 0,
            "last_request_time": None,
            "error_count": 0,
        }
        # Simulate receiving request with error
        stats["requests_received"] += 1
        stats["error_count"] += 1
        stats["last_request_time"] = 1640000000.0

        assert stats["requests_received"] == 1
        assert stats["responses_sent"] == 0
        assert stats["error_count"] == 1

    def test_typed_dict_reset_stats(self):
        """Test TypedDict reset to initial state."""
        stats: TypedDictDiscoveryStats = {
            "requests_received": 100,
            "responses_sent": 95,
            "throttled_requests": 5,
            "last_request_time": 1640000000.0,
            "error_count": 3,
        }
        # Reset stats
        stats = {
            "requests_received": 0,
            "responses_sent": 0,
            "throttled_requests": 0,
            "last_request_time": None,
            "error_count": 0,
        }
        assert stats["requests_received"] == 0
        assert stats["responses_sent"] == 0
        assert stats["throttled_requests"] == 0
        assert stats["last_request_time"] is None
        assert stats["error_count"] == 0
