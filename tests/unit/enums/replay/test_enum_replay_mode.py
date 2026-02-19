# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for EnumReplayMode.

Tests all aspects of the replay mode enum including:
- All enum values are present
- String enum behavior
- Serialization/deserialization
"""

from enum import Enum

import pytest

from omnibase_core.enums.replay.enum_replay_mode import EnumReplayMode


@pytest.mark.unit
class TestEnumReplayModeValues:
    """Test cases for EnumReplayMode enum values."""

    def test_enum_values_exist(self) -> None:
        """Test that all expected enum values are present."""
        assert hasattr(EnumReplayMode, "PRODUCTION")
        assert hasattr(EnumReplayMode, "RECORDING")
        assert hasattr(EnumReplayMode, "REPLAYING")

    def test_enum_values_are_correct(self) -> None:
        """Test that enum values have correct string values."""
        assert EnumReplayMode.PRODUCTION.value == "production"
        assert EnumReplayMode.RECORDING.value == "recording"
        assert EnumReplayMode.REPLAYING.value == "replaying"

    def test_enum_count(self) -> None:
        """Test that enum has exactly 3 values."""
        values = list(EnumReplayMode)
        assert len(values) == 3

    def test_all_expected_values(self) -> None:
        """Test that all expected values are present."""
        expected_values = {"production", "recording", "replaying"}
        actual_values = {member.value for member in EnumReplayMode}
        assert actual_values == expected_values


@pytest.mark.unit
class TestEnumReplayModeStringBehavior:
    """Test string enum behavior."""

    def test_enum_is_string(self) -> None:
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumReplayMode, str)
        assert issubclass(EnumReplayMode, Enum)

    def test_enum_string_comparison(self) -> None:
        """Test string comparison behavior."""
        assert EnumReplayMode.PRODUCTION == "production"
        assert EnumReplayMode.RECORDING == "recording"
        assert EnumReplayMode.REPLAYING == "replaying"

    def test_enum_equality(self) -> None:
        """Test enum equality."""
        assert EnumReplayMode.PRODUCTION == EnumReplayMode.PRODUCTION
        assert EnumReplayMode.PRODUCTION != EnumReplayMode.RECORDING

    def test_enum_membership(self) -> None:
        """Test membership testing."""
        assert EnumReplayMode.PRODUCTION in EnumReplayMode
        assert "production" in EnumReplayMode
        assert "invalid_mode" not in EnumReplayMode


@pytest.mark.unit
class TestEnumReplayModeSerialization:
    """Test enum serialization and deserialization."""

    def test_enum_serialization(self) -> None:
        """Test enum serialization via .value property."""
        assert EnumReplayMode.PRODUCTION.value == "production"
        assert EnumReplayMode.RECORDING.value == "recording"
        assert EnumReplayMode.REPLAYING.value == "replaying"

    def test_enum_deserialization(self) -> None:
        """Test enum deserialization from string."""
        assert EnumReplayMode("production") == EnumReplayMode.PRODUCTION
        assert EnumReplayMode("recording") == EnumReplayMode.RECORDING
        assert EnumReplayMode("replaying") == EnumReplayMode.REPLAYING

    def test_invalid_value_raises_error(self) -> None:
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumReplayMode("invalid_mode")

        with pytest.raises(ValueError):
            EnumReplayMode("")


@pytest.mark.unit
class TestEnumReplayModeIteration:
    """Test enum iteration."""

    def test_enum_iteration(self) -> None:
        """Test that we can iterate over enum values."""
        values = list(EnumReplayMode)
        assert EnumReplayMode.PRODUCTION in values
        assert EnumReplayMode.RECORDING in values
        assert EnumReplayMode.REPLAYING in values


@pytest.mark.unit
class TestEnumReplayModeDocstring:
    """Test enum documentation."""

    def test_enum_has_docstring(self) -> None:
        """Test that enum has proper docstring."""
        assert EnumReplayMode.__doc__ is not None
        assert "replay" in EnumReplayMode.__doc__.lower()
