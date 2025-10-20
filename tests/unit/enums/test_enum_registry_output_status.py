"""Tests for EnumRegistryOutputStatus."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.enum_registry_output_status import EnumRegistryOutputStatus


class TestEnumRegistryOutputStatus:
    """Test suite for EnumRegistryOutputStatus."""

    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert EnumRegistryOutputStatus.SUCCESS == "success"
        assert EnumRegistryOutputStatus.FAILURE == "failure"
        assert EnumRegistryOutputStatus.WARNING == "warning"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumRegistryOutputStatus, str)
        assert issubclass(EnumRegistryOutputStatus, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        status = EnumRegistryOutputStatus.SUCCESS
        assert isinstance(status, str)
        assert status == "success"
        assert len(status) == 7

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumRegistryOutputStatus)
        assert len(values) == 3
        assert EnumRegistryOutputStatus.SUCCESS in values
        assert EnumRegistryOutputStatus.WARNING in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumRegistryOutputStatus.FAILURE in EnumRegistryOutputStatus
        assert "failure" in [e.value for e in EnumRegistryOutputStatus]

    def test_enum_comparison(self):
        """Test enum comparison."""
        status1 = EnumRegistryOutputStatus.SUCCESS
        status2 = EnumRegistryOutputStatus.SUCCESS
        status3 = EnumRegistryOutputStatus.FAILURE

        assert status1 == status2
        assert status1 != status3
        assert status1 == "success"

    def test_enum_serialization(self):
        """Test enum serialization."""
        status = EnumRegistryOutputStatus.WARNING
        serialized = status.value
        assert serialized == "warning"
        json_str = json.dumps(status)
        assert json_str == '"warning"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        status = EnumRegistryOutputStatus("failure")
        assert status == EnumRegistryOutputStatus.FAILURE

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumRegistryOutputStatus("invalid_status")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {"success", "failure", "warning"}
        actual_values = {e.value for e in EnumRegistryOutputStatus}
        assert actual_values == expected_values

    def test_output_status_categorization(self):
        """Test categorization of output statuses."""
        # Positive status
        positive = {EnumRegistryOutputStatus.SUCCESS}
        # Negative status
        negative = {EnumRegistryOutputStatus.FAILURE}
        # Cautionary status
        cautionary = {EnumRegistryOutputStatus.WARNING}

        assert all(s in EnumRegistryOutputStatus for s in positive)
        assert all(s in EnumRegistryOutputStatus for s in negative)
        assert all(s in EnumRegistryOutputStatus for s in cautionary)
        assert positive | negative | cautionary == set(EnumRegistryOutputStatus)

    def test_status_severity_levels(self):
        """Test implicit severity levels."""
        # Success is lowest severity
        # Warning is medium severity
        # Failure is highest severity
        statuses = [
            EnumRegistryOutputStatus.SUCCESS,
            EnumRegistryOutputStatus.WARNING,
            EnumRegistryOutputStatus.FAILURE,
        ]
        assert all(status in EnumRegistryOutputStatus for status in statuses)
