"""
Tests for ModelCliDiscoveryStats - CLI tool discovery statistics.

This module tests discovery statistics tracking, health metrics calculation,
and performance monitoring for CLI tool discovery operations.
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.core.model_cli_discovery_stats import (
    ModelCliDiscoveryStats,
)


class TestModelCliDiscoveryStatsCreation:
    """Test discovery stats creation and defaults."""

    def test_stats_creation_defaults(self):
        """Test stats initializes with default values."""
        stats = ModelCliDiscoveryStats()

        assert stats.total_tools_discovered == 0
        assert stats.healthy_tools_count == 0
        assert stats.unhealthy_tools_count == 0
        assert stats.discovery_cache_size == 0
        assert stats.cache_hit_rate is None
        assert stats.last_discovery_duration_ms is None
        assert stats.average_discovery_duration_ms is None
        assert stats.last_refresh_timestamp is None
        assert stats.last_health_check_timestamp is None
        assert stats.discovery_errors_count == 0
        assert stats.last_error_message is None
        assert stats.registries_online == 0
        assert stats.registries_total == 0

    def test_stats_creation_with_values(self):
        """Test stats creation with provided values."""
        stats = ModelCliDiscoveryStats(
            total_tools_discovered=50,
            healthy_tools_count=45,
            unhealthy_tools_count=5,
            discovery_cache_size=100,
            cache_hit_rate=85.5,
            last_discovery_duration_ms=123.45,
            average_discovery_duration_ms=150.0,
            last_refresh_timestamp="2024-01-15T10:30:00Z",
            last_health_check_timestamp="2024-01-15T10:35:00Z",
            discovery_errors_count=2,
            last_error_message="Connection timeout",
            registries_online=3,
            registries_total=5,
        )

        assert stats.total_tools_discovered == 50
        assert stats.healthy_tools_count == 45
        assert stats.unhealthy_tools_count == 5
        assert stats.discovery_cache_size == 100
        assert stats.cache_hit_rate == 85.5
        assert stats.last_discovery_duration_ms == 123.45
        assert stats.average_discovery_duration_ms == 150.0
        assert stats.last_refresh_timestamp == "2024-01-15T10:30:00Z"
        assert stats.last_health_check_timestamp == "2024-01-15T10:35:00Z"
        assert stats.discovery_errors_count == 2
        assert stats.last_error_message == "Connection timeout"
        assert stats.registries_online == 3
        assert stats.registries_total == 5


class TestHealthPercentageProperty:
    """Test health_percentage property calculation."""

    def test_health_percentage_all_healthy(self):
        """Test health percentage when all tools are healthy."""
        stats = ModelCliDiscoveryStats(
            total_tools_discovered=100,
            healthy_tools_count=100,
            unhealthy_tools_count=0,
        )

        assert stats.health_percentage == 100.0

    def test_health_percentage_partial_healthy(self):
        """Test health percentage with partially healthy tools."""
        stats = ModelCliDiscoveryStats(
            total_tools_discovered=100,
            healthy_tools_count=75,
            unhealthy_tools_count=25,
        )

        assert stats.health_percentage == 75.0

    def test_health_percentage_none_healthy(self):
        """Test health percentage when no tools are healthy."""
        stats = ModelCliDiscoveryStats(
            total_tools_discovered=50,
            healthy_tools_count=0,
            unhealthy_tools_count=50,
        )

        assert stats.health_percentage == 0.0

    def test_health_percentage_zero_total(self):
        """Test health percentage returns 100% when no tools discovered."""
        stats = ModelCliDiscoveryStats(
            total_tools_discovered=0,
            healthy_tools_count=0,
            unhealthy_tools_count=0,
        )

        assert stats.health_percentage == 100.0

    def test_health_percentage_decimal_precision(self):
        """Test health percentage with decimal precision."""
        stats = ModelCliDiscoveryStats(
            total_tools_discovered=3,
            healthy_tools_count=2,
            unhealthy_tools_count=1,
        )

        # 2/3 = 66.666...
        assert abs(stats.health_percentage - 66.66666666666667) < 0.0001

    def test_health_percentage_single_tool_healthy(self):
        """Test health percentage with single healthy tool."""
        stats = ModelCliDiscoveryStats(
            total_tools_discovered=1,
            healthy_tools_count=1,
        )

        assert stats.health_percentage == 100.0

    def test_health_percentage_single_tool_unhealthy(self):
        """Test health percentage with single unhealthy tool."""
        stats = ModelCliDiscoveryStats(
            total_tools_discovered=1,
            healthy_tools_count=0,
            unhealthy_tools_count=1,
        )

        assert stats.health_percentage == 0.0


class TestRegistryHealthPercentageProperty:
    """Test registry_health_percentage property calculation."""

    def test_registry_health_percentage_all_online(self):
        """Test registry health when all registries are online."""
        stats = ModelCliDiscoveryStats(
            registries_online=5,
            registries_total=5,
        )

        assert stats.registry_health_percentage == 100.0

    def test_registry_health_percentage_partial_online(self):
        """Test registry health with partially online registries."""
        stats = ModelCliDiscoveryStats(
            registries_online=3,
            registries_total=5,
        )

        assert stats.registry_health_percentage == 60.0

    def test_registry_health_percentage_none_online(self):
        """Test registry health when no registries are online."""
        stats = ModelCliDiscoveryStats(
            registries_online=0,
            registries_total=10,
        )

        assert stats.registry_health_percentage == 0.0

    def test_registry_health_percentage_zero_total(self):
        """Test registry health returns 100% when no registries configured."""
        stats = ModelCliDiscoveryStats(
            registries_online=0,
            registries_total=0,
        )

        assert stats.registry_health_percentage == 100.0

    def test_registry_health_percentage_decimal_precision(self):
        """Test registry health percentage with decimal precision."""
        stats = ModelCliDiscoveryStats(
            registries_online=2,
            registries_total=3,
        )

        # 2/3 = 66.666...
        assert abs(stats.registry_health_percentage - 66.66666666666667) < 0.0001


class TestToSummaryDict:
    """Test to_summary_dict method."""

    def test_to_summary_dict_default_values(self):
        """Test summary dict with default values."""
        stats = ModelCliDiscoveryStats()

        summary = stats.to_summary_dict()

        assert summary["total_tools"] == 0
        assert summary["healthy_tools"] == 0
        assert summary["health_percentage"] == 100.0
        assert summary["cache_size"] == 0
        assert summary["registries_online"] == "0/0"
        assert summary["last_refresh"] is None

    def test_to_summary_dict_with_values(self):
        """Test summary dict with populated values."""
        stats = ModelCliDiscoveryStats(
            total_tools_discovered=100,
            healthy_tools_count=95,
            discovery_cache_size=200,
            registries_online=4,
            registries_total=5,
            last_refresh_timestamp="2024-01-15T10:00:00Z",
        )

        summary = stats.to_summary_dict()

        assert summary["total_tools"] == 100
        assert summary["healthy_tools"] == 95
        assert summary["health_percentage"] == 95.0
        assert summary["cache_size"] == 200
        assert summary["registries_online"] == "4/5"
        assert summary["last_refresh"] == "2024-01-15T10:00:00Z"

    def test_to_summary_dict_rounds_health_percentage(self):
        """Test summary dict rounds health percentage to 1 decimal."""
        stats = ModelCliDiscoveryStats(
            total_tools_discovered=3,
            healthy_tools_count=2,
        )

        summary = stats.to_summary_dict()

        # Should be rounded to 1 decimal place
        assert summary["health_percentage"] == 66.7

    def test_to_summary_dict_format_registries(self):
        """Test summary dict formats registry status correctly."""
        stats = ModelCliDiscoveryStats(
            registries_online=7,
            registries_total=10,
        )

        summary = stats.to_summary_dict()

        assert summary["registries_online"] == "7/10"

    def test_to_summary_dict_returns_dict(self):
        """Test summary dict returns a dictionary."""
        stats = ModelCliDiscoveryStats()

        summary = stats.to_summary_dict()

        assert isinstance(summary, dict)

    def test_to_summary_dict_has_expected_keys(self):
        """Test summary dict contains expected keys."""
        stats = ModelCliDiscoveryStats()

        summary = stats.to_summary_dict()

        expected_keys = {
            "total_tools",
            "healthy_tools",
            "health_percentage",
            "cache_size",
            "registries_online",
            "last_refresh",
        }
        assert set(summary.keys()) == expected_keys


class TestDiscoveryStatsEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_stats_with_large_numbers(self):
        """Test stats handles large numbers correctly."""
        stats = ModelCliDiscoveryStats(
            total_tools_discovered=1_000_000,
            healthy_tools_count=999_999,
            discovery_cache_size=5_000_000,
            cache_hit_rate=99.99,
        )

        assert stats.total_tools_discovered == 1_000_000
        assert stats.healthy_tools_count == 999_999
        assert stats.health_percentage > 99.99

    def test_stats_with_zero_values(self):
        """Test stats with all zero values."""
        stats = ModelCliDiscoveryStats(
            total_tools_discovered=0,
            healthy_tools_count=0,
            unhealthy_tools_count=0,
            discovery_cache_size=0,
            discovery_errors_count=0,
            registries_online=0,
            registries_total=0,
        )

        assert stats.health_percentage == 100.0
        assert stats.registry_health_percentage == 100.0

    def test_stats_with_negative_duration_allowed(self):
        """Test stats allows negative duration values (for testing)."""
        # Pydantic doesn't enforce non-negative by default for floats
        stats = ModelCliDiscoveryStats(
            last_discovery_duration_ms=-10.0,
        )

        assert stats.last_discovery_duration_ms == -10.0

    def test_stats_with_cache_hit_rate_100(self):
        """Test stats with 100% cache hit rate."""
        stats = ModelCliDiscoveryStats(
            cache_hit_rate=100.0,
        )

        assert stats.cache_hit_rate == 100.0

    def test_stats_with_cache_hit_rate_0(self):
        """Test stats with 0% cache hit rate."""
        stats = ModelCliDiscoveryStats(
            cache_hit_rate=0.0,
        )

        assert stats.cache_hit_rate == 0.0

    def test_stats_with_very_long_error_message(self):
        """Test stats handles very long error messages."""
        long_message = "Error: " + "A" * 10000
        stats = ModelCliDiscoveryStats(
            last_error_message=long_message,
        )

        assert len(stats.last_error_message) == len(long_message)
        assert stats.last_error_message.startswith("Error: AAA")


class TestDiscoveryStatsTimestamps:
    """Test timestamp handling."""

    def test_stats_with_iso_timestamps(self):
        """Test stats with ISO format timestamps."""
        stats = ModelCliDiscoveryStats(
            last_refresh_timestamp="2024-01-15T10:30:00Z",
            last_health_check_timestamp="2024-01-15T10:35:00.123456Z",
        )

        assert stats.last_refresh_timestamp == "2024-01-15T10:30:00Z"
        assert stats.last_health_check_timestamp == "2024-01-15T10:35:00.123456Z"

    def test_stats_with_different_timestamp_formats(self):
        """Test stats accepts different timestamp string formats."""
        stats = ModelCliDiscoveryStats(
            last_refresh_timestamp="2024-01-15 10:30:00",
        )

        assert stats.last_refresh_timestamp == "2024-01-15 10:30:00"

    def test_stats_timestamp_none_by_default(self):
        """Test timestamps are None by default."""
        stats = ModelCliDiscoveryStats()

        assert stats.last_refresh_timestamp is None
        assert stats.last_health_check_timestamp is None


class TestDiscoveryStatsPerformanceMetrics:
    """Test performance metrics fields."""

    def test_stats_with_performance_metrics(self):
        """Test stats with performance metrics."""
        stats = ModelCliDiscoveryStats(
            last_discovery_duration_ms=125.5,
            average_discovery_duration_ms=150.0,
            cache_hit_rate=85.5,
        )

        assert stats.last_discovery_duration_ms == 125.5
        assert stats.average_discovery_duration_ms == 150.0
        assert stats.cache_hit_rate == 85.5

    def test_stats_duration_none_by_default(self):
        """Test duration metrics are None by default."""
        stats = ModelCliDiscoveryStats()

        assert stats.last_discovery_duration_ms is None
        assert stats.average_discovery_duration_ms is None

    def test_stats_cache_hit_rate_none_by_default(self):
        """Test cache hit rate is None by default."""
        stats = ModelCliDiscoveryStats()

        assert stats.cache_hit_rate is None

    def test_stats_with_zero_duration(self):
        """Test stats with zero duration."""
        stats = ModelCliDiscoveryStats(
            last_discovery_duration_ms=0.0,
            average_discovery_duration_ms=0.0,
        )

        assert stats.last_discovery_duration_ms == 0.0
        assert stats.average_discovery_duration_ms == 0.0


class TestDiscoveryStatsErrorTracking:
    """Test error tracking fields."""

    def test_stats_with_errors(self):
        """Test stats with error information."""
        stats = ModelCliDiscoveryStats(
            discovery_errors_count=5,
            last_error_message="Connection timeout to registry",
        )

        assert stats.discovery_errors_count == 5
        assert stats.last_error_message == "Connection timeout to registry"

    def test_stats_error_count_default_zero(self):
        """Test error count defaults to zero."""
        stats = ModelCliDiscoveryStats()

        assert stats.discovery_errors_count == 0

    def test_stats_error_message_default_none(self):
        """Test error message defaults to None."""
        stats = ModelCliDiscoveryStats()

        assert stats.last_error_message is None

    def test_stats_with_multiple_errors(self):
        """Test stats tracks error count correctly."""
        stats = ModelCliDiscoveryStats(
            discovery_errors_count=100,
        )

        assert stats.discovery_errors_count == 100


class TestDiscoveryStatsIntegration:
    """Test integration scenarios."""

    def test_stats_complete_scenario(self):
        """Test complete discovery stats scenario."""
        stats = ModelCliDiscoveryStats(
            total_tools_discovered=150,
            healthy_tools_count=140,
            unhealthy_tools_count=10,
            discovery_cache_size=300,
            cache_hit_rate=92.5,
            last_discovery_duration_ms=234.56,
            average_discovery_duration_ms=250.0,
            last_refresh_timestamp="2024-01-15T10:00:00Z",
            last_health_check_timestamp="2024-01-15T10:05:00Z",
            discovery_errors_count=3,
            last_error_message="Timeout on registry 'external'",
            registries_online=4,
            registries_total=5,
        )

        # Verify calculations
        assert stats.health_percentage > 93.0
        assert stats.registry_health_percentage == 80.0

        # Verify summary
        summary = stats.to_summary_dict()
        assert summary["total_tools"] == 150
        assert summary["healthy_tools"] == 140
        assert summary["registries_online"] == "4/5"

    def test_stats_serialization_deserialization(self):
        """Test stats can be serialized and deserialized."""
        original = ModelCliDiscoveryStats(
            total_tools_discovered=100,
            healthy_tools_count=95,
            cache_hit_rate=85.0,
            last_refresh_timestamp="2024-01-15T10:00:00Z",
        )

        # Serialize to dict
        data = original.model_dump()

        # Deserialize from dict
        restored = ModelCliDiscoveryStats.model_validate(data)

        assert restored.total_tools_discovered == original.total_tools_discovered
        assert restored.healthy_tools_count == original.healthy_tools_count
        assert restored.cache_hit_rate == original.cache_hit_rate
        assert restored.last_refresh_timestamp == original.last_refresh_timestamp

    def test_stats_immutability_of_calculations(self):
        """Test that calculated properties don't change with mutations."""
        stats = ModelCliDiscoveryStats(
            total_tools_discovered=100,
            healthy_tools_count=80,
        )

        health1 = stats.health_percentage

        # Mutate the stats
        stats.healthy_tools_count = 90

        health2 = stats.health_percentage

        # Health percentage should reflect new values
        assert health1 == 80.0
        assert health2 == 90.0

    def test_stats_update_scenario(self):
        """Test updating stats over time."""
        stats = ModelCliDiscoveryStats()

        # Initial discovery
        stats.total_tools_discovered = 50
        stats.healthy_tools_count = 48
        stats.last_refresh_timestamp = "2024-01-15T10:00:00Z"

        assert stats.health_percentage == 96.0

        # After some tools become unhealthy
        stats.healthy_tools_count = 45
        stats.unhealthy_tools_count = 5
        stats.discovery_errors_count = 2

        assert stats.health_percentage == 90.0
        assert stats.discovery_errors_count == 2
