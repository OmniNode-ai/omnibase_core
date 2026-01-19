"""Tests for enum_mcp_status.py"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_mcp_status import EnumMCPStatus


@pytest.mark.unit
class TestEnumMCPStatus:
    """Test cases for EnumMCPStatus"""

    def test_enum_values(self):
        """Test that all enum values are correct"""
        assert EnumMCPStatus.SUCCESS == "success"
        assert EnumMCPStatus.ERROR == "error"
        assert EnumMCPStatus.HEALTHY == "healthy"
        assert EnumMCPStatus.DEGRADED == "degraded"
        assert EnumMCPStatus.UNHEALTHY == "unhealthy"
        assert EnumMCPStatus.RUNNING == "running"
        assert EnumMCPStatus.UNKNOWN == "unknown"
        assert EnumMCPStatus.UNREACHABLE == "unreachable"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum"""
        assert issubclass(EnumMCPStatus, str)
        assert issubclass(EnumMCPStatus, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values"""
        assert EnumMCPStatus.SUCCESS == "success"
        assert EnumMCPStatus.ERROR == "error"
        assert EnumMCPStatus.HEALTHY == "healthy"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values"""
        values = list(EnumMCPStatus)
        assert len(values) == 8
        assert EnumMCPStatus.SUCCESS in values
        assert EnumMCPStatus.UNREACHABLE in values

    def test_enum_membership(self):
        """Test membership testing"""
        assert EnumMCPStatus.SUCCESS in EnumMCPStatus
        assert "success" in EnumMCPStatus
        assert "invalid_value" not in EnumMCPStatus

    def test_enum_comparison(self):
        """Test enum comparison"""
        assert EnumMCPStatus.SUCCESS == EnumMCPStatus.SUCCESS
        assert EnumMCPStatus.ERROR != EnumMCPStatus.SUCCESS
        assert EnumMCPStatus.SUCCESS == "success"

    def test_enum_serialization(self):
        """Test enum serialization"""
        assert EnumMCPStatus.SUCCESS.value == "success"
        assert EnumMCPStatus.ERROR.value == "error"

    def test_enum_deserialization(self):
        """Test enum deserialization"""
        assert EnumMCPStatus("success") == EnumMCPStatus.SUCCESS
        assert EnumMCPStatus("error") == EnumMCPStatus.ERROR

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError"""
        with pytest.raises(ValueError):
            EnumMCPStatus("invalid_value")

        with pytest.raises(ValueError):
            EnumMCPStatus("")

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
        actual_values = {member.value for member in EnumMCPStatus}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring"""
        assert "Status values for MCP operations" in EnumMCPStatus.__doc__

    def test_enum_status_categories(self):
        """Test specific status categories"""
        # Success states
        assert EnumMCPStatus.SUCCESS.value == "success"
        assert EnumMCPStatus.HEALTHY.value == "healthy"
        assert EnumMCPStatus.RUNNING.value == "running"

        # Error states
        assert EnumMCPStatus.ERROR.value == "error"
        assert EnumMCPStatus.UNHEALTHY.value == "unhealthy"
        assert EnumMCPStatus.UNREACHABLE.value == "unreachable"

        # Degraded states
        assert EnumMCPStatus.DEGRADED.value == "degraded"

        # Unknown states
        assert EnumMCPStatus.UNKNOWN.value == "unknown"

    def test_enum_health_statuses(self):
        """Test health-related status values"""
        healthy_statuses = {
            EnumMCPStatus.SUCCESS,
            EnumMCPStatus.HEALTHY,
            EnumMCPStatus.RUNNING,
        }

        unhealthy_statuses = {
            EnumMCPStatus.ERROR,
            EnumMCPStatus.UNHEALTHY,
            EnumMCPStatus.UNREACHABLE,
        }

        degraded_statuses = {EnumMCPStatus.DEGRADED}
        unknown_statuses = {EnumMCPStatus.UNKNOWN}

        all_statuses = set(EnumMCPStatus)
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
            EnumMCPStatus.SUCCESS,
            EnumMCPStatus.HEALTHY,
            EnumMCPStatus.RUNNING,
        }

        # Negative operation statuses
        negative_statuses = {
            EnumMCPStatus.ERROR,
            EnumMCPStatus.UNHEALTHY,
            EnumMCPStatus.UNREACHABLE,
        }

        # Neutral operation statuses
        neutral_statuses = {EnumMCPStatus.DEGRADED, EnumMCPStatus.UNKNOWN}

        all_statuses = set(EnumMCPStatus)
        assert (
            positive_statuses.union(negative_statuses).union(neutral_statuses)
            == all_statuses
        )
