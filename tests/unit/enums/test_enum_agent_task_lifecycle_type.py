# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for EnumAgentTaskLifecycleType (OMN-9623)."""

import json
from enum import Enum

import pytest

from omnibase_core.enums.enum_agent_task_lifecycle_type import (
    EnumAgentTaskLifecycleType,
)


@pytest.mark.unit
class TestEnumAgentTaskLifecycleType:
    """Test cases for EnumAgentTaskLifecycleType enum."""

    def test_enum_values(self) -> None:
        """Test that enum has expected SCREAMING_SNAKE string values."""
        assert EnumAgentTaskLifecycleType.SUBMITTED.value == "SUBMITTED"
        assert EnumAgentTaskLifecycleType.ACCEPTED.value == "ACCEPTED"
        assert EnumAgentTaskLifecycleType.PROGRESS.value == "PROGRESS"
        assert EnumAgentTaskLifecycleType.ARTIFACT.value == "ARTIFACT"
        assert EnumAgentTaskLifecycleType.COMPLETED.value == "COMPLETED"
        assert EnumAgentTaskLifecycleType.FAILED.value == "FAILED"
        assert EnumAgentTaskLifecycleType.TIMED_OUT.value == "TIMED_OUT"
        assert EnumAgentTaskLifecycleType.CANCELED.value == "CANCELED"

    def test_enum_inheritance(self) -> None:
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumAgentTaskLifecycleType, str)
        assert issubclass(EnumAgentTaskLifecycleType, Enum)

    def test_enum_string_behavior(self) -> None:
        """Test that enum values behave as strings."""
        lifecycle = EnumAgentTaskLifecycleType.COMPLETED
        assert isinstance(lifecycle, str)
        assert str(lifecycle) == "COMPLETED"

    def test_enum_iteration(self) -> None:
        """Test that enum can be iterated and has exactly 8 members."""
        values = list(EnumAgentTaskLifecycleType)
        assert len(values) == 8

    def test_enum_all_values(self) -> None:
        """Test that all expected values are present and no extras."""
        expected = {
            "SUBMITTED",
            "ACCEPTED",
            "PROGRESS",
            "ARTIFACT",
            "COMPLETED",
            "FAILED",
            "TIMED_OUT",
            "CANCELED",
        }
        actual = {member.value for member in EnumAgentTaskLifecycleType}
        assert actual == expected

    def test_enum_membership(self) -> None:
        """Test enum membership via string values."""
        values = {m.value for m in EnumAgentTaskLifecycleType}
        assert "SUBMITTED" in values
        assert "COMPLETED" in values
        assert "TIMED_OUT" in values
        assert "invalid_lifecycle" not in values

    def test_enum_unique(self) -> None:
        """Test that all enum values are unique (enforced by @unique)."""
        values = [m.value for m in EnumAgentTaskLifecycleType]
        assert len(values) == len(set(values))

    def test_enum_serialization(self) -> None:
        """Test that enum values serialize to their string representations."""
        lifecycle = EnumAgentTaskLifecycleType.TIMED_OUT
        assert json.dumps(lifecycle) == '"TIMED_OUT"'

    def test_enum_deserialization(self) -> None:
        """Test that enum members can be constructed from their string values."""
        assert (
            EnumAgentTaskLifecycleType("SUBMITTED")
            == EnumAgentTaskLifecycleType.SUBMITTED
        )
        assert (
            EnumAgentTaskLifecycleType("CANCELED")
            == EnumAgentTaskLifecycleType.CANCELED
        )

    def test_enum_invalid_value_raises(self) -> None:
        """Test that constructing from an invalid value raises ValueError."""
        with pytest.raises(ValueError):
            EnumAgentTaskLifecycleType("invalid")

    def test_terminal_states_present(self) -> None:
        """Test that both terminal states (COMPLETED, FAILED) are present."""
        terminal = {
            EnumAgentTaskLifecycleType.COMPLETED,
            EnumAgentTaskLifecycleType.FAILED,
            EnumAgentTaskLifecycleType.TIMED_OUT,
            EnumAgentTaskLifecycleType.CANCELED,
        }
        all_values = set(EnumAgentTaskLifecycleType)
        assert terminal.issubset(all_values)
