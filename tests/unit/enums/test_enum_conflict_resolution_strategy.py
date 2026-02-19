# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for EnumConflictResolutionStrategy enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_conflict_resolution_strategy import (
    EnumConflictResolutionStrategy,
)


@pytest.mark.unit
class TestEnumConflictResolutionStrategy:
    """Test cases for EnumConflictResolutionStrategy enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        assert EnumConflictResolutionStrategy.TIMESTAMP_WINS == "timestamp_wins"
        assert EnumConflictResolutionStrategy.MANUAL == "manual"
        assert EnumConflictResolutionStrategy.LOCAL_WINS == "local_wins"
        assert EnumConflictResolutionStrategy.REMOTE_WINS == "remote_wins"
        assert EnumConflictResolutionStrategy.MERGE == "merge"
        assert EnumConflictResolutionStrategy.LAST_WRITER_WINS == "last_writer_wins"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumConflictResolutionStrategy, str)
        assert issubclass(EnumConflictResolutionStrategy, Enum)

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings."""
        strategy = EnumConflictResolutionStrategy.MANUAL
        assert isinstance(strategy, str)
        assert strategy == "manual"
        assert len(strategy) == 6
        assert strategy.startswith("man")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumConflictResolutionStrategy)
        assert len(values) == 6
        assert EnumConflictResolutionStrategy.TIMESTAMP_WINS in values
        assert EnumConflictResolutionStrategy.LAST_WRITER_WINS in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "manual" in EnumConflictResolutionStrategy
        assert "invalid_strategy" not in EnumConflictResolutionStrategy

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        strategy1 = EnumConflictResolutionStrategy.MANUAL
        strategy2 = EnumConflictResolutionStrategy.MERGE

        assert strategy1 != strategy2
        assert strategy1 == "manual"
        assert strategy2 == "merge"

    def test_enum_serialization(self):
        """Test that enum values can be serialized."""
        strategy = EnumConflictResolutionStrategy.LOCAL_WINS
        serialized = strategy.value
        assert serialized == "local_wins"

        # Test JSON serialization
        import json

        json_str = json.dumps(strategy)
        assert json_str == '"local_wins"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        strategy = EnumConflictResolutionStrategy("remote_wins")
        assert strategy == EnumConflictResolutionStrategy.REMOTE_WINS

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumConflictResolutionStrategy("invalid_strategy")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "timestamp_wins",
            "manual",
            "local_wins",
            "remote_wins",
            "merge",
            "last_writer_wins",
        }

        actual_values = {member.value for member in EnumConflictResolutionStrategy}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert (
            "Canonical conflict resolution strategies for ONEX distributed operations"
            in EnumConflictResolutionStrategy.__doc__
        )

    def test_enum_conflict_resolution_strategies(self):
        """Test that enum covers typical conflict resolution strategies."""
        # Test timestamp-based strategies
        assert (
            EnumConflictResolutionStrategy.TIMESTAMP_WINS
            in EnumConflictResolutionStrategy
        )
        assert (
            EnumConflictResolutionStrategy.LAST_WRITER_WINS
            in EnumConflictResolutionStrategy
        )

        # Test manual resolution
        assert EnumConflictResolutionStrategy.MANUAL in EnumConflictResolutionStrategy

        # Test location-based strategies
        assert (
            EnumConflictResolutionStrategy.LOCAL_WINS in EnumConflictResolutionStrategy
        )
        assert (
            EnumConflictResolutionStrategy.REMOTE_WINS in EnumConflictResolutionStrategy
        )

        # Test merge strategy
        assert EnumConflictResolutionStrategy.MERGE in EnumConflictResolutionStrategy
