# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Test suite for TypedDictExecutionStats.
"""

from datetime import datetime

import pytest

from omnibase_core.types.typed_dict_execution_stats import TypedDictExecutionStats


@pytest.mark.unit
class TestTypedDictExecutionStats:
    """Test TypedDictExecutionStats functionality."""

    def test_typed_dict_execution_stats_creation(self):
        """Test creating TypedDictExecutionStats with all required fields."""
        now = datetime.now()

        stats: TypedDictExecutionStats = {
            "execution_count": 100,
            "success_count": 95,
            "failure_count": 5,
            "average_duration_ms": 150.5,
            "last_execution": now,
            "total_duration_ms": 15050,
        }

        assert stats["execution_count"] == 100
        assert stats["success_count"] == 95
        assert stats["failure_count"] == 5
        assert stats["average_duration_ms"] == 150.5
        assert stats["last_execution"] == now
        assert stats["total_duration_ms"] == 15050

    def test_typed_dict_execution_stats_field_types(self):
        """Test that all fields have correct types."""
        now = datetime.now()

        stats: TypedDictExecutionStats = {
            "execution_count": 50,
            "success_count": 48,
            "failure_count": 2,
            "average_duration_ms": 200.0,
            "last_execution": now,
            "total_duration_ms": 10000,
        }

        assert isinstance(stats["execution_count"], int)
        assert isinstance(stats["success_count"], int)
        assert isinstance(stats["failure_count"], int)
        assert isinstance(stats["average_duration_ms"], float)
        assert isinstance(stats["last_execution"], datetime)
        assert isinstance(stats["total_duration_ms"], int)

    def test_typed_dict_execution_stats_perfect_success(self):
        """Test TypedDictExecutionStats with perfect success rate."""
        now = datetime.now()

        stats: TypedDictExecutionStats = {
            "execution_count": 100,
            "success_count": 100,
            "failure_count": 0,
            "average_duration_ms": 100.0,
            "last_execution": now,
            "total_duration_ms": 10000,
        }

        assert stats["success_count"] == stats["execution_count"]
        assert stats["failure_count"] == 0
        assert (
            stats["success_count"] + stats["failure_count"] == stats["execution_count"]
        )

    def test_typed_dict_execution_stats_all_failures(self):
        """Test TypedDictExecutionStats with all failures."""
        now = datetime.now()

        stats: TypedDictExecutionStats = {
            "execution_count": 10,
            "success_count": 0,
            "failure_count": 10,
            "average_duration_ms": 50.0,
            "last_execution": now,
            "total_duration_ms": 500,
        }

        assert stats["success_count"] == 0
        assert stats["failure_count"] == stats["execution_count"]
        assert (
            stats["success_count"] + stats["failure_count"] == stats["execution_count"]
        )

    def test_typed_dict_execution_stats_zero_executions(self):
        """Test TypedDictExecutionStats with zero executions."""
        now = datetime.now()

        stats: TypedDictExecutionStats = {
            "execution_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "average_duration_ms": 0.0,
            "last_execution": now,
            "total_duration_ms": 0,
        }

        assert stats["execution_count"] == 0
        assert stats["success_count"] == 0
        assert stats["failure_count"] == 0
        assert stats["total_duration_ms"] == 0

    def test_typed_dict_execution_stats_high_duration(self):
        """Test TypedDictExecutionStats with high duration values."""
        now = datetime.now()

        stats: TypedDictExecutionStats = {
            "execution_count": 5,
            "success_count": 5,
            "failure_count": 0,
            "average_duration_ms": 5000.0,  # 5 seconds
            "last_execution": now,
            "total_duration_ms": 25000,  # 25 seconds total
        }

        assert stats["average_duration_ms"] == 5000.0
        assert stats["total_duration_ms"] == 25000
        # Verify calculation: total_duration / execution_count = average_duration
        assert (
            stats["total_duration_ms"] / stats["execution_count"]
            == stats["average_duration_ms"]
        )

    def test_typed_dict_execution_stats_very_fast_execution(self):
        """Test TypedDictExecutionStats with very fast execution."""
        now = datetime.now()

        stats: TypedDictExecutionStats = {
            "execution_count": 1000,
            "success_count": 1000,
            "failure_count": 0,
            "average_duration_ms": 0.1,  # 0.1 milliseconds
            "last_execution": now,
            "total_duration_ms": 100,  # 100 milliseconds total
        }

        assert stats["average_duration_ms"] == 0.1
        assert stats["total_duration_ms"] == 100

    def test_typed_dict_execution_stats_mixed_results(self):
        """Test TypedDictExecutionStats with mixed success/failure results."""
        now = datetime.now()

        stats: TypedDictExecutionStats = {
            "execution_count": 20,
            "success_count": 15,
            "failure_count": 5,
            "average_duration_ms": 300.0,
            "last_execution": now,
            "total_duration_ms": 6000,
        }

        # Verify counts add up
        assert (
            stats["success_count"] + stats["failure_count"] == stats["execution_count"]
        )
        assert stats["success_count"] > stats["failure_count"]
        assert stats["failure_count"] > 0

    def test_typed_dict_execution_stats_different_timestamps(self):
        """Test TypedDictExecutionStats with different timestamp formats."""
        now = datetime.now()
        iso_timestamp = datetime.fromisoformat("2024-01-01T12:00:00")

        stats1: TypedDictExecutionStats = {
            "execution_count": 10,
            "success_count": 10,
            "failure_count": 0,
            "average_duration_ms": 100.0,
            "last_execution": now,
            "total_duration_ms": 1000,
        }

        stats2: TypedDictExecutionStats = {
            "execution_count": 5,
            "success_count": 5,
            "failure_count": 0,
            "average_duration_ms": 200.0,
            "last_execution": iso_timestamp,
            "total_duration_ms": 1000,
        }

        assert stats1["last_execution"] == now
        assert stats2["last_execution"] == iso_timestamp

    def test_typed_dict_execution_stats_consistency_checks(self):
        """Test TypedDictExecutionStats for logical consistency."""
        now = datetime.now()

        stats: TypedDictExecutionStats = {
            "execution_count": 100,
            "success_count": 80,
            "failure_count": 20,
            "average_duration_ms": 150.0,
            "last_execution": now,
            "total_duration_ms": 15000,
        }

        # Verify logical consistency
        assert (
            stats["success_count"] + stats["failure_count"] == stats["execution_count"]
        )
        assert stats["success_count"] >= 0
        assert stats["failure_count"] >= 0
        assert stats["execution_count"] >= 0
        assert stats["average_duration_ms"] >= 0.0
        assert stats["total_duration_ms"] >= 0
