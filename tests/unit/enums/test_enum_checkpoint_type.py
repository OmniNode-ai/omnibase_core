"""
Tests for EnumCheckpointType enum.
"""

from enum import Enum

import pytest

from omnibase_core.enums.enum_checkpoint_type import EnumCheckpointType


@pytest.mark.unit
class TestEnumCheckpointType:
    """Test cases for EnumCheckpointType enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        assert EnumCheckpointType.MANUAL == "manual"
        assert EnumCheckpointType.AUTOMATIC == "automatic"
        assert EnumCheckpointType.FAILURE_RECOVERY == "failure_recovery"
        assert EnumCheckpointType.STEP_COMPLETION == "step_completion"
        assert EnumCheckpointType.COMPOSITION_BOUNDARY == "composition_boundary"

    def test_enum_inheritance(self):
        """Test that enum inherits from str and Enum."""
        assert issubclass(EnumCheckpointType, str)
        assert issubclass(EnumCheckpointType, Enum)

    def test_enum_string_behavior(self):
        """Test that enum values behave as strings."""
        checkpoint_type = EnumCheckpointType.MANUAL
        assert isinstance(checkpoint_type, str)
        assert checkpoint_type == "manual"
        assert len(checkpoint_type) == 6
        assert checkpoint_type.startswith("man")

    def test_enum_iteration(self):
        """Test that enum can be iterated."""
        values = list(EnumCheckpointType)
        assert len(values) == 9
        assert EnumCheckpointType.MANUAL in values
        assert EnumCheckpointType.COMPOSITION_BOUNDARY in values

    def test_enum_membership(self):
        """Test enum membership operations."""
        assert "manual" in EnumCheckpointType
        assert "invalid_type" not in EnumCheckpointType

    def test_enum_comparison(self):
        """Test enum comparison operations."""
        type1 = EnumCheckpointType.MANUAL
        type2 = EnumCheckpointType.AUTOMATIC

        assert type1 != type2
        assert type1 == "manual"
        assert type2 == "automatic"

    def test_enum_serialization(self):
        """Test that enum values can be serialized."""
        checkpoint_type = EnumCheckpointType.FAILURE_RECOVERY
        serialized = checkpoint_type.value
        assert serialized == "failure_recovery"

        # Test JSON serialization
        import json

        json_str = json.dumps(checkpoint_type)
        assert json_str == '"failure_recovery"'

    def test_enum_deserialization(self):
        """Test that enum can be created from string values."""
        checkpoint_type = EnumCheckpointType("step_completion")
        assert checkpoint_type == EnumCheckpointType.STEP_COMPLETION

    def test_enum_invalid_value(self):
        """Test that invalid values raise ValueError."""
        with pytest.raises(ValueError):
            EnumCheckpointType("invalid_type")

    def test_enum_all_values(self):
        """Test that all expected values are present."""
        expected_values = {
            "manual",
            "automatic",
            "failure_recovery",
            "recovery",
            "step_completion",
            "stage_completion",
            "snapshot",
            "incremental",
            "composition_boundary",
        }

        actual_values = {member.value for member in EnumCheckpointType}
        assert actual_values == expected_values

    def test_enum_docstring(self):
        """Test that enum has proper docstring."""
        assert "Types of workflow checkpoints" in EnumCheckpointType.__doc__

    def test_enum_checkpoint_types(self):
        """Test that enum covers typical checkpoint types."""
        # Test manual checkpoint
        assert EnumCheckpointType.MANUAL in EnumCheckpointType

        # Test automatic checkpoint
        assert EnumCheckpointType.AUTOMATIC in EnumCheckpointType

        # Test recovery checkpoint
        assert EnumCheckpointType.FAILURE_RECOVERY in EnumCheckpointType

        # Test completion checkpoint
        assert EnumCheckpointType.STEP_COMPLETION in EnumCheckpointType

        # Test boundary checkpoint
        assert EnumCheckpointType.COMPOSITION_BOUNDARY in EnumCheckpointType
