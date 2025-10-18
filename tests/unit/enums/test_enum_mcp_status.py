"""Tests for enum_mcp_status.py"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_mcp_status import EnumMcpStatus


class TestEnumMcpStatus:
    """Test cases for EnumMcpStatus"""

    def test_enum_values(self):
        """Test that all enum values are correct"""
        assert EnumMcpStatus.SUCCESS == "success"
        assert EnumMcpStatus.ERROR == "error"
        assert EnumMcpStatus.HEALTHY == "healthy"
        assert EnumMcpStatus.DEGRADED == "degraded"
        assert EnumMcpStatus.UNHEALTHY == "unhealthy"
        assert EnumMcpStatus.RUNNING == "running"
        assert EnumMcpStatus.UNKNOWN == "unknown"
        assert EnumMcpStatus.UNREACHABLE == "unreachable"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum"""
        assert issubclass(EnumMcpStatus, str)
        assert issubclass(EnumMcpStatus, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values"""
        assert EnumMcpStatus.SUCCESS == "success"
        assert EnumMcpStatus.ERROR == "error"
        assert EnumMcpStatus.HEALTHY == "healthy"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values"""
        values = list(EnumMcpStatus)
        assert len(values) == 8
        assert EnumMcpStatus.SUCCESS in values
        assert EnumMcpStatus.UNREACHABLE in values

    def test_enum_membership(self):
        """Test membership testing"""
        assert EnumMcpStatus.SUCCESS in EnumMcpStatus
        assert "success" in EnumMcpStatus
        assert "invalid_value" not in EnumMcpStatus

    def test_enum_comparison(self):
        """Test enum comparison"""
        assert EnumMcpStatus.SUCCESS == EnumMcpStatus.SUCCESS
        assert EnumMcpStatus.ERROR != EnumMcpStatus.SUCCESS
        assert EnumMcpStatus.SUCCESS == "success"

    def test_enum_serialization(self):
        """Test enum serialization"""
        assert EnumMcpStatus.SUCCESS.value == "success"
        assert EnumMcpStatus.ERROR.value == "error"

    def test_enum_deserialization(self):
        """Test enum deserialization"""
        assert EnumMcpStatus("success") == EnumMcpStatus.SUCCESS
        assert EnumMcpStatus("error") == EnumMcpStatus.ERROR

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError"""
        with pytest.raises(ValueError):
            EnumMcpStatus("invalid_value")

        with pytest.raises(ValueError):
            EnumMcpStatus("")

    def test_enum_all_values(self):
        """Test that all expected values are present"""
        expected_values = {
            "success",
            "error",
            "healthy",
            "degraded",
            "unhealthy",
            "running",
            "unknown",
            "unreachable",
        }
        actual_values = {member.value for member in EnumMcpStatus}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring"""
        assert "Status values for MCP operations" in EnumMcpStatus.__doc__

    def test_enum_status_categories(self):
        """Test specific status categories"""
        # Success states
        assert EnumMcpStatus.SUCCESS.value == "success"
        assert EnumMcpStatus.HEALTHY.value == "healthy"
        assert EnumMcpStatus.RUNNING.value == "running"

        # Error states
        assert EnumMcpStatus.ERROR.value == "error"
        assert EnumMcpStatus.UNHEALTHY.value == "unhealthy"
        assert EnumMcpStatus.UNREACHABLE.value == "unreachable"

        # Degraded states
        assert EnumMcpStatus.DEGRADED.value == "degraded"

        # Unknown states
        assert EnumMcpStatus.UNKNOWN.value == "unknown"

    def test_enum_health_statuses(self):
        """Test health-related status values"""
        healthy_statuses = {
            EnumMcpStatus.SUCCESS,
            EnumMcpStatus.HEALTHY,
            EnumMcpStatus.RUNNING,
        }

        unhealthy_statuses = {
            EnumMcpStatus.ERROR,
            EnumMcpStatus.UNHEALTHY,
            EnumMcpStatus.UNREACHABLE,
        }

        degraded_statuses = {EnumMcpStatus.DEGRADED}
        unknown_statuses = {EnumMcpStatus.UNKNOWN}

        all_statuses = set(EnumMcpStatus)
        assert (
            healthy_statuses.union(unhealthy_statuses)
            .union(degraded_statuses)
            .union(unknown_statuses)
            == all_statuses
        )

    def test_enum_operation_statuses(self):
        """Test operation-related status values"""
        # Positive operation statuses
        positive_statuses = {
            EnumMcpStatus.SUCCESS,
            EnumMcpStatus.HEALTHY,
            EnumMcpStatus.RUNNING,
        }

        # Negative operation statuses
        negative_statuses = {
            EnumMcpStatus.ERROR,
            EnumMcpStatus.UNHEALTHY,
            EnumMcpStatus.UNREACHABLE,
        }

        # Neutral operation statuses
        neutral_statuses = {EnumMcpStatus.DEGRADED, EnumMcpStatus.UNKNOWN}

        all_statuses = set(EnumMcpStatus)
        assert (
            positive_statuses.union(negative_statuses).union(neutral_statuses)
            == all_statuses
        )
