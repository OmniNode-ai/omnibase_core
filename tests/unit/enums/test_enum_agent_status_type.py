# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for EnumAgentStatusType enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_agent_status_type import EnumAgentStatusType


@pytest.mark.unit
class TestEnumAgentStatusType:
    """Test cases for EnumAgentStatusType enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        assert EnumAgentStatusType.IDLE == "idle"
        assert EnumAgentStatusType.WORKING == "working"
        assert EnumAgentStatusType.ERROR == "error"
        assert EnumAgentStatusType.TERMINATING == "terminating"
        assert EnumAgentStatusType.STARTING == "starting"
        assert EnumAgentStatusType.SUSPENDED == "suspended"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumAgentStatusType, str)
        assert issubclass(EnumAgentStatusType, Enum)

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings."""
        status = EnumAgentStatusType.WORKING
        assert isinstance(status, str)
        assert status == "working"
        assert len(status) == 7
        assert status.startswith("work")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumAgentStatusType)
        assert len(values) == 6
        assert EnumAgentStatusType.IDLE in values
        assert EnumAgentStatusType.SUSPENDED in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "idle" in EnumAgentStatusType
        assert "invalid_status" not in EnumAgentStatusType

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        status1 = EnumAgentStatusType.IDLE
        status2 = EnumAgentStatusType.WORKING

        assert status1 != status2
        assert status1 == "idle"
        assert status2 == "working"

    def test_enum_serialization(self):
        """Test that enum values can be serialized."""
        status = EnumAgentStatusType.ERROR
        serialized = status.value
        assert serialized == "error"

        # Test JSON serialization
        import json

        json_str = json.dumps(status)
        assert json_str == '"error"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        status = EnumAgentStatusType("terminating")
        assert status == EnumAgentStatusType.TERMINATING

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumAgentStatusType("invalid_status")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "idle",
            "working",
            "error",
            "terminating",
            "starting",
            "suspended",
        }

        actual_values = {member.value for member in EnumAgentStatusType}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert "Agent status enumeration" in EnumAgentStatusType.__doc__

    def test_enum_workflow_states(self):
        """Test that enum covers typical agent workflow states."""
        # Test typical workflow progression
        assert EnumAgentStatusType.STARTING in EnumAgentStatusType
        assert EnumAgentStatusType.WORKING in EnumAgentStatusType
        assert EnumAgentStatusType.IDLE in EnumAgentStatusType
        assert EnumAgentStatusType.TERMINATING in EnumAgentStatusType

        # Test error state
        assert EnumAgentStatusType.ERROR in EnumAgentStatusType

        # Test suspended state
        assert EnumAgentStatusType.SUSPENDED in EnumAgentStatusType
