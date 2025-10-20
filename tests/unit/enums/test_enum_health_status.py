"""
Tests for EnumHealthStatus enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_health_status import EnumHealthStatus


class TestEnumHealthStatus:
    """Test cases for EnumHealthStatus enum."""

    def test_enum_values(self):
        """Test that all enum values are correct."""
        assert EnumHealthStatus.HEALTHY == "healthy"
        assert EnumHealthStatus.DEGRADED == "degraded"
        assert EnumHealthStatus.UNHEALTHY == "unhealthy"
        assert EnumHealthStatus.CRITICAL == "critical"
        assert EnumHealthStatus.UNKNOWN == "unknown"
        assert EnumHealthStatus.WARNING == "warning"
        assert EnumHealthStatus.UNREACHABLE == "unreachable"
        assert EnumHealthStatus.AVAILABLE == "available"
        assert EnumHealthStatus.UNAVAILABLE == "unavailable"
        assert EnumHealthStatus.ERROR == "error"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumHealthStatus, str)
        assert issubclass(EnumHealthStatus, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        assert str(EnumHealthStatus.HEALTHY) == "healthy"
        assert str(EnumHealthStatus.DEGRADED) == "degraded"
        assert str(EnumHealthStatus.UNHEALTHY) == "unhealthy"
        assert str(EnumHealthStatus.CRITICAL) == "critical"
        assert str(EnumHealthStatus.UNKNOWN) == "unknown"
        assert str(EnumHealthStatus.WARNING) == "warning"
        assert str(EnumHealthStatus.UNREACHABLE) == "unreachable"
        assert str(EnumHealthStatus.AVAILABLE) == "available"
        assert str(EnumHealthStatus.UNAVAILABLE) == "unavailable"
        assert str(EnumHealthStatus.ERROR) == "error"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values."""
        values = list(EnumHealthStatus)
        assert len(values) == 10
        assert EnumHealthStatus.HEALTHY in values
        assert EnumHealthStatus.DEGRADED in values
        assert EnumHealthStatus.UNHEALTHY in values
        assert EnumHealthStatus.CRITICAL in values
        assert EnumHealthStatus.UNKNOWN in values
        assert EnumHealthStatus.WARNING in values
        assert EnumHealthStatus.UNREACHABLE in values
        assert EnumHealthStatus.AVAILABLE in values
        assert EnumHealthStatus.UNAVAILABLE in values
        assert EnumHealthStatus.ERROR in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert "healthy" in EnumHealthStatus
        assert "degraded" in EnumHealthStatus
        assert "unhealthy" in EnumHealthStatus
        assert "critical" in EnumHealthStatus
        assert "unknown" in EnumHealthStatus
        assert "warning" in EnumHealthStatus
        assert "unreachable" in EnumHealthStatus
        assert "available" in EnumHealthStatus
        assert "unavailable" in EnumHealthStatus
        assert "error" in EnumHealthStatus
        assert "invalid" not in EnumHealthStatus

    def test_enum_comparison(self):
        """Test enum comparison."""
        assert EnumHealthStatus.HEALTHY == "healthy"
        assert EnumHealthStatus.DEGRADED == "degraded"
        assert EnumHealthStatus.UNHEALTHY == "unhealthy"
        assert EnumHealthStatus.CRITICAL == "critical"
        assert EnumHealthStatus.UNKNOWN == "unknown"
        assert EnumHealthStatus.WARNING == "warning"
        assert EnumHealthStatus.UNREACHABLE == "unreachable"
        assert EnumHealthStatus.AVAILABLE == "available"
        assert EnumHealthStatus.UNAVAILABLE == "unavailable"
        assert EnumHealthStatus.ERROR == "error"

    def test_enum_serialization(self):
        """Test enum serialization."""
        assert EnumHealthStatus.HEALTHY.value == "healthy"
        assert EnumHealthStatus.DEGRADED.value == "degraded"
        assert EnumHealthStatus.UNHEALTHY.value == "unhealthy"
        assert EnumHealthStatus.CRITICAL.value == "critical"
        assert EnumHealthStatus.UNKNOWN.value == "unknown"
        assert EnumHealthStatus.WARNING.value == "warning"
        assert EnumHealthStatus.UNREACHABLE.value == "unreachable"
        assert EnumHealthStatus.AVAILABLE.value == "available"
        assert EnumHealthStatus.UNAVAILABLE.value == "unavailable"
        assert EnumHealthStatus.ERROR.value == "error"

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        assert EnumHealthStatus("healthy") == EnumHealthStatus.HEALTHY
        assert EnumHealthStatus("degraded") == EnumHealthStatus.DEGRADED
        assert EnumHealthStatus("unhealthy") == EnumHealthStatus.UNHEALTHY
        assert EnumHealthStatus("critical") == EnumHealthStatus.CRITICAL
        assert EnumHealthStatus("unknown") == EnumHealthStatus.UNKNOWN
        assert EnumHealthStatus("warning") == EnumHealthStatus.WARNING
        assert EnumHealthStatus("unreachable") == EnumHealthStatus.UNREACHABLE
        assert EnumHealthStatus("available") == EnumHealthStatus.AVAILABLE
        assert EnumHealthStatus("unavailable") == EnumHealthStatus.UNAVAILABLE
        assert EnumHealthStatus("error") == EnumHealthStatus.ERROR

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumHealthStatus("invalid")

    def test_enum_all_values(self):
        """Test that all enum values are accessible."""
        all_values = [status.value for status in EnumHealthStatus]
        expected_values = [
            "healthy",
            "degraded",
            "unhealthy",
            "critical",
            "unknown",
            "warning",
            "unreachable",
            "available",
            "unavailable",
            "error",
        ]
        assert set(all_values) == set(expected_values)

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert (
            "Health status for LLM provider health checks" in EnumHealthStatus.__doc__
        )

    def test_is_operational_method(self):
        """Test the is_operational method."""
        assert EnumHealthStatus.HEALTHY.is_operational() is True
        assert EnumHealthStatus.DEGRADED.is_operational() is True
        assert EnumHealthStatus.UNHEALTHY.is_operational() is False
        assert EnumHealthStatus.CRITICAL.is_operational() is False
        assert EnumHealthStatus.UNKNOWN.is_operational() is False
        assert EnumHealthStatus.WARNING.is_operational() is False
        assert EnumHealthStatus.UNREACHABLE.is_operational() is False
        assert EnumHealthStatus.AVAILABLE.is_operational() is False
        assert EnumHealthStatus.UNAVAILABLE.is_operational() is False
        assert EnumHealthStatus.ERROR.is_operational() is False

    def test_requires_attention_method(self):
        """Test the requires_attention method."""
        assert EnumHealthStatus.HEALTHY.requires_attention() is False
        assert EnumHealthStatus.DEGRADED.requires_attention() is False
        assert EnumHealthStatus.UNHEALTHY.requires_attention() is True
        assert EnumHealthStatus.CRITICAL.requires_attention() is True
        assert EnumHealthStatus.UNKNOWN.requires_attention() is False
        assert EnumHealthStatus.WARNING.requires_attention() is False
        assert EnumHealthStatus.UNREACHABLE.requires_attention() is False
        assert EnumHealthStatus.AVAILABLE.requires_attention() is False
        assert EnumHealthStatus.UNAVAILABLE.requires_attention() is False
        assert EnumHealthStatus.ERROR.requires_attention() is False
