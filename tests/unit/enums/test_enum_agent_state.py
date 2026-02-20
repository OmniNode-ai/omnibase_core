# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for EnumAgentState closed enum (OMN-1847)."""

from enum import Enum

import pytest

from omnibase_core.enums.enum_agent_state import EnumAgentState


@pytest.mark.unit
class TestEnumAgentState:
    """Test cases for EnumAgentState enum."""

    def test_enum_values(self) -> None:
        """Test that enum has expected string values."""
        assert EnumAgentState.IDLE.value == "idle"
        assert EnumAgentState.WORKING.value == "working"
        assert EnumAgentState.BLOCKED.value == "blocked"
        assert EnumAgentState.AWAITING_INPUT.value == "awaiting_input"
        assert EnumAgentState.FINISHED.value == "finished"
        assert EnumAgentState.ERROR.value == "error"

    def test_enum_inheritance(self) -> None:
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumAgentState, str)
        assert issubclass(EnumAgentState, Enum)

    def test_enum_string_behavior(self) -> None:
        """Test that enum values behave as strings."""
        state = EnumAgentState.WORKING
        assert isinstance(state, str)
        assert state.value == "working"

    def test_enum_iteration(self) -> None:
        """Test that enum can be iterated and has exactly 6 members."""
        values = list(EnumAgentState)
        assert len(values) == 6
        assert EnumAgentState.IDLE in values
        assert EnumAgentState.FINISHED in values

    def test_enum_all_values(self) -> None:
        """Test that all expected values are present and no extras."""
        expected_values = {
            "idle",
            "working",
            "blocked",
            "awaiting_input",
            "finished",
            "error",
        }
        actual_values = {member.value for member in EnumAgentState}
        assert actual_values == expected_values

    def test_enum_membership(self) -> None:
        """Test enum membership via string values."""
        assert "idle" in EnumAgentState
        assert "working" in EnumAgentState
        assert "invalid_state" not in EnumAgentState

    def test_enum_comparison(self) -> None:
        """Test enum equality comparisons."""
        assert EnumAgentState.IDLE.value != EnumAgentState.WORKING.value
        assert EnumAgentState.IDLE.value == "idle"
        assert EnumAgentState.ERROR.value == "error"

    def test_enum_serialization(self) -> None:
        """Test that enum values serialize to their string representations."""
        import json

        state = EnumAgentState.BLOCKED
        assert state.value == "blocked"
        json_str = json.dumps(state)
        assert json_str == '"blocked"'

    def test_enum_deserialization(self) -> None:
        """Test that enum members can be constructed from their string values."""
        assert EnumAgentState("idle") == EnumAgentState.IDLE
        assert EnumAgentState("awaiting_input") == EnumAgentState.AWAITING_INPUT

    def test_enum_invalid_value_raises(self) -> None:
        """Test that constructing from an invalid value raises ValueError."""
        with pytest.raises(ValueError):
            EnumAgentState("invalid_state")

    def test_enum_unique(self) -> None:
        """Test that all enum values are unique (enforced by @unique)."""
        values = [m.value for m in EnumAgentState]
        assert len(values) == len(set(values))
