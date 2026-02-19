# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for EnumRegistryEntryStatus."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.enum_registry_entry_status import EnumRegistryEntryStatus


@pytest.mark.unit
class TestEnumRegistryEntryStatus:
    """Test suite for EnumRegistryEntryStatus."""

    def test_enum_values(self):
        """Test that all enum values are defined correctly."""
        assert EnumRegistryEntryStatus.EPHEMERAL == "ephemeral"
        assert EnumRegistryEntryStatus.ONLINE == "online"
        assert EnumRegistryEntryStatus.VALIDATED == "validated"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumRegistryEntryStatus, str)
        assert issubclass(EnumRegistryEntryStatus, Enum)

    def test_enum_string_behavior(self):
        """Test string behavior of enum values."""
        status = EnumRegistryEntryStatus.ONLINE
        assert isinstance(status, str)
        assert status == "online"
        assert len(status) == 6

    def test_enum_iteration(self):
        """Test that all enum values can be iterated."""
        values = list(EnumRegistryEntryStatus)
        assert len(values) == 3
        assert EnumRegistryEntryStatus.EPHEMERAL in values
        assert EnumRegistryEntryStatus.VALIDATED in values

    def test_enum_membership(self):
        """Test membership testing."""
        assert EnumRegistryEntryStatus.ONLINE in EnumRegistryEntryStatus
        assert "online" in [e.value for e in EnumRegistryEntryStatus]

    def test_enum_comparison(self):
        """Test enum comparison."""
        status1 = EnumRegistryEntryStatus.VALIDATED
        status2 = EnumRegistryEntryStatus.VALIDATED
        status3 = EnumRegistryEntryStatus.EPHEMERAL

        assert status1 == status2
        assert status1 != status3
        assert status1 == "validated"

    def test_enum_serialization(self):
        """Test enum serialization."""
        status = EnumRegistryEntryStatus.EPHEMERAL
        serialized = status.value
        assert serialized == "ephemeral"
        json_str = json.dumps(status)
        assert json_str == '"ephemeral"'

    def test_enum_deserialization(self):
        """Test enum deserialization."""
        status = EnumRegistryEntryStatus("online")
        assert status == EnumRegistryEntryStatus.ONLINE

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumRegistryEntryStatus("invalid_status")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {"ephemeral", "online", "validated"}
        actual_values = {e.value for e in EnumRegistryEntryStatus}
        assert actual_values == expected_values

    def test_status_progression(self):
        """Test logical status progression."""
        # Ephemeral -> Online -> Validated represents a typical progression
        progression = [
            EnumRegistryEntryStatus.EPHEMERAL,
            EnumRegistryEntryStatus.ONLINE,
            EnumRegistryEntryStatus.VALIDATED,
        ]
        assert all(status in EnumRegistryEntryStatus for status in progression)

    def test_temporary_vs_permanent_status(self):
        """Test categorization of temporary vs permanent status."""
        # Ephemeral is temporary
        temporary = {EnumRegistryEntryStatus.EPHEMERAL}
        # Online and Validated are more permanent
        permanent = {
            EnumRegistryEntryStatus.ONLINE,
            EnumRegistryEntryStatus.VALIDATED,
        }

        assert all(s in EnumRegistryEntryStatus for s in temporary)
        assert all(s in EnumRegistryEntryStatus for s in permanent)
        assert temporary | permanent == set(EnumRegistryEntryStatus)
