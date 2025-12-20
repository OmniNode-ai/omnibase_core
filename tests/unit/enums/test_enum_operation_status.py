"""Tests for enum_operation_status.py"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_operation_status import EnumOperationStatus


@pytest.mark.unit
class TestEnumOperationStatus:
    """Test cases for EnumOperationStatus"""

    def test_enum_values(self):
        """Test that all enum values are correct"""
        assert EnumOperationStatus.SUCCESS == "success"
        assert EnumOperationStatus.FAILED == "failed"
        assert EnumOperationStatus.IN_PROGRESS == "in_progress"
        assert EnumOperationStatus.CANCELLED == "cancelled"
        assert EnumOperationStatus.PENDING == "pending"
        assert EnumOperationStatus.TIMEOUT == "timeout"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum"""
        assert issubclass(EnumOperationStatus, str)
        assert issubclass(EnumOperationStatus, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values"""
        assert EnumOperationStatus.SUCCESS == "success"
        assert EnumOperationStatus.FAILED == "failed"
        assert EnumOperationStatus.IN_PROGRESS == "in_progress"

    def test_enum_iteration(self):
        """Test that we can iterate over enum values"""
        values = list(EnumOperationStatus)
        assert len(values) == 6
        assert EnumOperationStatus.SUCCESS in values
        assert EnumOperationStatus.TIMEOUT in values

    def test_enum_membership(self):
        """Test membership testing"""
        assert EnumOperationStatus.SUCCESS in EnumOperationStatus
        assert "success" in EnumOperationStatus
        assert "invalid_value" not in EnumOperationStatus

    def test_enum_comparison(self):
        """Test enum comparison"""
        assert EnumOperationStatus.SUCCESS == EnumOperationStatus.SUCCESS
        assert EnumOperationStatus.FAILED != EnumOperationStatus.SUCCESS
        assert EnumOperationStatus.SUCCESS == "success"

    def test_enum_serialization(self):
        """Test enum serialization"""
        assert EnumOperationStatus.SUCCESS.value == "success"
        assert EnumOperationStatus.FAILED.value == "failed"

    def test_enum_deserialization(self):
        """Test enum deserialization"""
        assert EnumOperationStatus("success") == EnumOperationStatus.SUCCESS
        assert EnumOperationStatus("failed") == EnumOperationStatus.FAILED

    def test_enum_invalid_values(self):
        """Test that invalid values raise ValueError"""
        with pytest.raises(ValueError):
            EnumOperationStatus("invalid_value")

        with pytest.raises(ValueError):
            EnumOperationStatus("")

    def test_enum_all_values(self):
        """Test that all expected values are present"""
        expected_values = {
            "success",
            "failed",
            "in_progress",
            "cancelled",
            "pending",
            "timeout",
        }
        actual_values = {member.value for member in EnumOperationStatus}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring"""
        assert "Enumeration for operation status values" in EnumOperationStatus.__doc__

    def test_enum_status_types(self):
        """Test specific status types"""
        # Success status
        assert EnumOperationStatus.SUCCESS.value == "success"

        # Failure status
        assert EnumOperationStatus.FAILED.value == "failed"

        # Active statuses
        assert EnumOperationStatus.IN_PROGRESS.value == "in_progress"
        assert EnumOperationStatus.PENDING.value == "pending"

        # Terminal statuses
        assert EnumOperationStatus.CANCELLED.value == "cancelled"
        assert EnumOperationStatus.TIMEOUT.value == "timeout"

    def test_is_terminal_method(self):
        """Test the is_terminal method"""
        # Terminal statuses
        assert EnumOperationStatus.SUCCESS.is_terminal() is True
        assert EnumOperationStatus.FAILED.is_terminal() is True
        assert EnumOperationStatus.CANCELLED.is_terminal() is True
        assert EnumOperationStatus.TIMEOUT.is_terminal() is True

        # Non-terminal statuses
        assert EnumOperationStatus.IN_PROGRESS.is_terminal() is False
        assert EnumOperationStatus.PENDING.is_terminal() is False

    def test_is_active_method(self):
        """Test the is_active method"""
        # Active statuses
        assert EnumOperationStatus.IN_PROGRESS.is_active() is True
        assert EnumOperationStatus.PENDING.is_active() is True

        # Non-active statuses
        assert EnumOperationStatus.SUCCESS.is_active() is False
        assert EnumOperationStatus.FAILED.is_active() is False
        assert EnumOperationStatus.CANCELLED.is_active() is False
        assert EnumOperationStatus.TIMEOUT.is_active() is False

    def test_is_successful_method(self):
        """Test the is_successful method"""
        # Successful status
        assert EnumOperationStatus.SUCCESS.is_successful() is True

        # Non-successful statuses
        assert EnumOperationStatus.FAILED.is_successful() is False
        assert EnumOperationStatus.IN_PROGRESS.is_successful() is False
        assert EnumOperationStatus.CANCELLED.is_successful() is False
        assert EnumOperationStatus.PENDING.is_successful() is False
        assert EnumOperationStatus.TIMEOUT.is_successful() is False

    def test_enum_status_categories(self):
        """Test status categories"""
        # Success statuses
        success_statuses = {EnumOperationStatus.SUCCESS}

        # Failure statuses
        failure_statuses = {
            EnumOperationStatus.FAILED,
            EnumOperationStatus.CANCELLED,
            EnumOperationStatus.TIMEOUT,
        }

        # Active statuses
        active_statuses = {EnumOperationStatus.IN_PROGRESS, EnumOperationStatus.PENDING}

        all_statuses = set(EnumOperationStatus)
        assert (
            success_statuses.union(failure_statuses).union(active_statuses)
            == all_statuses
        )

    def test_enum_status_lifecycle(self):
        """Test status lifecycle categories"""
        # Initial statuses
        initial_statuses = {EnumOperationStatus.PENDING}

        # Running statuses
        running_statuses = {EnumOperationStatus.IN_PROGRESS}

        # Final statuses
        final_statuses = {
            EnumOperationStatus.SUCCESS,
            EnumOperationStatus.FAILED,
            EnumOperationStatus.CANCELLED,
            EnumOperationStatus.TIMEOUT,
        }

        all_statuses = set(EnumOperationStatus)
        assert (
            initial_statuses.union(running_statuses).union(final_statuses)
            == all_statuses
        )
