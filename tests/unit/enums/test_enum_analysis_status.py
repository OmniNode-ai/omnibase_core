"""
Tests for EnumAnalysisStatus enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_analysis_status import EnumAnalysisStatus


@pytest.mark.unit
class TestEnumAnalysisStatus:
    """Test cases for EnumAnalysisStatus enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        assert EnumAnalysisStatus.PENDING == "pending"
        assert EnumAnalysisStatus.IN_PROGRESS == "in_progress"
        assert EnumAnalysisStatus.COMPLETED == "completed"
        assert EnumAnalysisStatus.FAILED == "failed"
        assert EnumAnalysisStatus.CANCELLED == "cancelled"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumAnalysisStatus, str)
        assert issubclass(EnumAnalysisStatus, Enum)

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings."""
        status = EnumAnalysisStatus.IN_PROGRESS
        assert isinstance(status, str)
        assert status == "in_progress"
        assert len(status) == 11
        assert status.startswith("in_")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumAnalysisStatus)
        assert len(values) == 5
        assert EnumAnalysisStatus.PENDING in values
        assert EnumAnalysisStatus.CANCELLED in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "pending" in EnumAnalysisStatus
        assert "invalid_status" not in EnumAnalysisStatus

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        status1 = EnumAnalysisStatus.PENDING
        status2 = EnumAnalysisStatus.COMPLETED

        assert status1 != status2
        assert status1 == "pending"
        assert status2 == "completed"

    def test_enum_serialization(self):
        """Test that enum values can be serialized."""
        status = EnumAnalysisStatus.FAILED
        serialized = status.value
        assert serialized == "failed"

        # Test JSON serialization
        import json

        json_str = json.dumps(status)
        assert json_str == '"failed"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        status = EnumAnalysisStatus("cancelled")
        assert status == EnumAnalysisStatus.CANCELLED

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumAnalysisStatus("invalid_status")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {"pending", "in_progress", "completed", "failed", "cancelled"}

        actual_values = {member.value for member in EnumAnalysisStatus}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert "Enumeration for analysis status values" in EnumAnalysisStatus.__doc__

    def test_enum_workflow_progression(self):
        """Test that enum covers typical analysis workflow states."""
        # Test typical workflow progression
        assert EnumAnalysisStatus.PENDING in EnumAnalysisStatus
        assert EnumAnalysisStatus.IN_PROGRESS in EnumAnalysisStatus
        assert EnumAnalysisStatus.COMPLETED in EnumAnalysisStatus

        # Test error states
        assert EnumAnalysisStatus.FAILED in EnumAnalysisStatus
        assert EnumAnalysisStatus.CANCELLED in EnumAnalysisStatus

    def test_enum_status_transitions(self):
        """Test that enum supports typical status transitions."""
        # Test that we can represent different states
        pending = EnumAnalysisStatus.PENDING
        in_progress = EnumAnalysisStatus.IN_PROGRESS
        completed = EnumAnalysisStatus.COMPLETED
        failed = EnumAnalysisStatus.FAILED
        cancelled = EnumAnalysisStatus.CANCELLED

        # All should be different
        assert pending != in_progress
        assert in_progress != completed
        assert completed != failed
        assert failed != cancelled
