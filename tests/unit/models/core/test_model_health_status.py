"""
Tests for ModelHealthStatus.

Comprehensive tests for health status model including timestamp validation,
metrics, and health details.
"""

from datetime import UTC, datetime

import pytest

from omnibase_core.enums.enum_node_health_status import EnumNodeHealthStatus
from omnibase_core.models.core.model_health_details import ModelHealthDetails
from omnibase_core.models.health.model_health_status import ModelHealthStatus


class TestModelHealthStatus:
    """Test suite for ModelHealthStatus."""

    def test_initialization_with_required_fields(self):
        """Test initialization with required fields only."""
        status = ModelHealthStatus(status=EnumNodeHealthStatus.HEALTHY)

        assert status.status == EnumNodeHealthStatus.HEALTHY
        assert status.message is None
        assert status.timestamp is None
        assert isinstance(status.details, ModelHealthDetails)
        assert status.uptime_seconds is None
        assert status.memory_usage_mb is None
        assert status.cpu_usage_percent is None

    def test_initialization_with_all_fields(self):
        """Test initialization with all fields."""
        timestamp = datetime.now(UTC).isoformat()
        details = ModelHealthDetails()

        status = ModelHealthStatus(
            status=EnumNodeHealthStatus.HEALTHY,
            message="All systems operational",
            timestamp=timestamp,
            details=details,
            uptime_seconds=3600.0,
            memory_usage_mb=512.5,
            cpu_usage_percent=25.8,
        )

        assert status.status == EnumNodeHealthStatus.HEALTHY
        assert status.message == "All systems operational"
        assert status.timestamp == timestamp
        assert status.details == details
        assert status.uptime_seconds == 3600.0
        assert status.memory_usage_mb == 512.5
        assert status.cpu_usage_percent == 25.8

    def test_timestamp_datetime_conversion(self):
        """Test timestamp validator converts datetime to ISO string."""
        dt = datetime(2024, 1, 15, 12, 30, 45)

        status = ModelHealthStatus(status=EnumNodeHealthStatus.HEALTHY, timestamp=dt)

        assert status.timestamp is not None
        assert isinstance(status.timestamp, str)
        assert status.timestamp == dt.isoformat()

    def test_timestamp_string_passthrough(self):
        """Test timestamp validator passes through strings."""
        timestamp_str = "2024-01-15T12:30:45"

        status = ModelHealthStatus(
            status=EnumNodeHealthStatus.HEALTHY, timestamp=timestamp_str
        )

        assert status.timestamp == timestamp_str

    def test_timestamp_none_handling(self):
        """Test timestamp validator handles None."""
        status = ModelHealthStatus(status=EnumNodeHealthStatus.HEALTHY, timestamp=None)

        assert status.timestamp is None

    def test_timestamp_other_type_conversion(self):
        """Test timestamp validator converts other types to string."""
        status = ModelHealthStatus(status=EnumNodeHealthStatus.HEALTHY, timestamp=12345)

        assert status.timestamp == "12345"

    def test_different_health_statuses(self):
        """Test different health status values."""
        # Healthy
        healthy = ModelHealthStatus(status=EnumNodeHealthStatus.HEALTHY)
        assert healthy.status == EnumNodeHealthStatus.HEALTHY

        # Degraded
        degraded = ModelHealthStatus(status=EnumNodeHealthStatus.DEGRADED)
        assert degraded.status == EnumNodeHealthStatus.DEGRADED

        # Unhealthy
        unhealthy = ModelHealthStatus(status=EnumNodeHealthStatus.UNHEALTHY)
        assert unhealthy.status == EnumNodeHealthStatus.UNHEALTHY

    def test_details_default_factory(self):
        """Test that details field uses default factory."""
        status1 = ModelHealthStatus(status=EnumNodeHealthStatus.HEALTHY)
        status2 = ModelHealthStatus(status=EnumNodeHealthStatus.HEALTHY)

        # Each instance should have its own details object
        assert status1.details is not status2.details
        assert isinstance(status1.details, ModelHealthDetails)
        assert isinstance(status2.details, ModelHealthDetails)

    def test_uptime_seconds_precision(self):
        """Test uptime_seconds accepts float values."""
        status = ModelHealthStatus(
            status=EnumNodeHealthStatus.HEALTHY, uptime_seconds=3661.234
        )

        assert status.uptime_seconds == 3661.234
        assert isinstance(status.uptime_seconds, float)

    def test_memory_usage_precision(self):
        """Test memory_usage_mb accepts float values."""
        status = ModelHealthStatus(
            status=EnumNodeHealthStatus.HEALTHY, memory_usage_mb=1024.75
        )

        assert status.memory_usage_mb == 1024.75
        assert isinstance(status.memory_usage_mb, float)

    def test_cpu_usage_precision(self):
        """Test cpu_usage_percent accepts float values."""
        status = ModelHealthStatus(
            status=EnumNodeHealthStatus.HEALTHY, cpu_usage_percent=45.67
        )

        assert status.cpu_usage_percent == 45.67
        assert isinstance(status.cpu_usage_percent, float)

    def test_message_optional(self):
        """Test message field is optional."""
        status_no_message = ModelHealthStatus(status=EnumNodeHealthStatus.HEALTHY)
        assert status_no_message.message is None

        status_with_message = ModelHealthStatus(
            status=EnumNodeHealthStatus.DEGRADED,
            message="Performance degradation detected",
        )
        assert status_with_message.message == "Performance degradation detected"

    def test_serialization(self):
        """Test model serialization."""
        status = ModelHealthStatus(
            status=EnumNodeHealthStatus.HEALTHY,
            message="OK",
            timestamp="2024-01-15T12:30:45",
            uptime_seconds=3600.0,
            memory_usage_mb=512.0,
            cpu_usage_percent=25.0,
        )

        data = status.model_dump()

        assert data["status"] == EnumNodeHealthStatus.HEALTHY
        assert data["message"] == "OK"
        assert data["timestamp"] == "2024-01-15T12:30:45"
        assert data["uptime_seconds"] == 3600.0
        assert data["memory_usage_mb"] == 512.0
        assert data["cpu_usage_percent"] == 25.0
        assert "details" in data

    def test_deserialization(self):
        """Test model deserialization from dict."""
        data = {
            "status": EnumNodeHealthStatus.HEALTHY,
            "message": "All good",
            "timestamp": "2024-01-15T12:30:45",
            "uptime_seconds": 3600.0,
            "memory_usage_mb": 512.0,
            "cpu_usage_percent": 25.0,
        }

        status = ModelHealthStatus(**data)

        assert status.status == EnumNodeHealthStatus.HEALTHY
        assert status.message == "All good"
        assert status.timestamp == "2024-01-15T12:30:45"
        assert status.uptime_seconds == 3600.0

    def test_zero_values(self):
        """Test handling of zero values."""
        status = ModelHealthStatus(
            status=EnumNodeHealthStatus.HEALTHY,
            uptime_seconds=0.0,
            memory_usage_mb=0.0,
            cpu_usage_percent=0.0,
        )

        assert status.uptime_seconds == 0.0
        assert status.memory_usage_mb == 0.0
        assert status.cpu_usage_percent == 0.0

    def test_large_values(self):
        """Test handling of large values."""
        status = ModelHealthStatus(
            status=EnumNodeHealthStatus.HEALTHY,
            uptime_seconds=999999999.99,
            memory_usage_mb=999999.99,
            cpu_usage_percent=100.0,
        )

        assert status.uptime_seconds == 999999999.99
        assert status.memory_usage_mb == 999999.99
        assert status.cpu_usage_percent == 100.0

    def test_negative_values(self):
        """Test handling of negative values (should be allowed by model)."""
        # Note: The model doesn't enforce positive values, so this should work
        status = ModelHealthStatus(
            status=EnumNodeHealthStatus.HEALTHY,
            uptime_seconds=-1.0,
            memory_usage_mb=-1.0,
            cpu_usage_percent=-1.0,
        )

        assert status.uptime_seconds == -1.0
        assert status.memory_usage_mb == -1.0
        assert status.cpu_usage_percent == -1.0


class TestModelHealthStatusEdgeCases:
    """Edge case tests for ModelHealthStatus."""

    def test_empty_message(self):
        """Test with empty string message."""
        status = ModelHealthStatus(status=EnumNodeHealthStatus.HEALTHY, message="")

        assert status.message == ""

    def test_long_message(self):
        """Test with very long message."""
        long_message = "x" * 10000

        status = ModelHealthStatus(
            status=EnumNodeHealthStatus.DEGRADED, message=long_message
        )

        assert status.message == long_message
        assert len(status.message) == 10000

    def test_special_characters_in_message(self):
        """Test message with special characters."""
        special_message = "Error: \n\t\r\"'<>&"

        status = ModelHealthStatus(
            status=EnumNodeHealthStatus.UNHEALTHY, message=special_message
        )

        assert status.message == special_message

    def test_timestamp_iso_format_variations(self):
        """Test various ISO timestamp formats."""
        timestamps = [
            "2024-01-15T12:30:45",
            "2024-01-15T12:30:45.123456",
            "2024-01-15T12:30:45+00:00",
            "2024-01-15T12:30:45Z",
        ]

        for ts in timestamps:
            status = ModelHealthStatus(
                status=EnumNodeHealthStatus.HEALTHY, timestamp=ts
            )
            assert status.timestamp == ts

    def test_model_copy(self):
        """Test model copying."""
        original = ModelHealthStatus(
            status=EnumNodeHealthStatus.HEALTHY,
            message="Original",
            uptime_seconds=3600.0,
        )

        copy = original.model_copy()

        assert copy.status == original.status
        assert copy.message == original.message
        assert copy.uptime_seconds == original.uptime_seconds
        assert copy is not original

    def test_model_copy_deep(self):
        """Test deep model copying."""
        original = ModelHealthStatus(
            status=EnumNodeHealthStatus.HEALTHY, message="Original"
        )

        copy = original.model_copy(deep=True)

        assert copy.details is not original.details
        assert isinstance(copy.details, ModelHealthDetails)
