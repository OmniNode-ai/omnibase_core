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


@pytest.mark.unit
class TestEnumCheckpointTypeIsRecoveryRelated:
    """Test cases for is_recovery_related class method."""

    @pytest.mark.parametrize(
        "checkpoint_type",
        [
            EnumCheckpointType.FAILURE_RECOVERY,
            EnumCheckpointType.RECOVERY,
            EnumCheckpointType.SNAPSHOT,
        ],
    )
    def test_recovery_related_returns_true(
        self, checkpoint_type: EnumCheckpointType
    ) -> None:
        """Test that recovery-related checkpoint types return True."""
        assert EnumCheckpointType.is_recovery_related(checkpoint_type) is True

    @pytest.mark.parametrize(
        "checkpoint_type",
        [
            EnumCheckpointType.MANUAL,
            EnumCheckpointType.AUTOMATIC,
            EnumCheckpointType.STEP_COMPLETION,
            EnumCheckpointType.STAGE_COMPLETION,
            EnumCheckpointType.INCREMENTAL,
            EnumCheckpointType.COMPOSITION_BOUNDARY,
        ],
    )
    def test_non_recovery_related_returns_false(
        self, checkpoint_type: EnumCheckpointType
    ) -> None:
        """Test that non-recovery checkpoint types return False."""
        assert EnumCheckpointType.is_recovery_related(checkpoint_type) is False


@pytest.mark.unit
class TestEnumCheckpointTypeIsAutomatic:
    """Test cases for is_automatic class method."""

    def test_manual_is_not_automatic(self) -> None:
        """Test that MANUAL checkpoint type is not automatic."""
        assert EnumCheckpointType.is_automatic(EnumCheckpointType.MANUAL) is False

    @pytest.mark.parametrize(
        "checkpoint_type",
        [
            EnumCheckpointType.AUTOMATIC,
            EnumCheckpointType.FAILURE_RECOVERY,
            EnumCheckpointType.RECOVERY,
            EnumCheckpointType.STEP_COMPLETION,
            EnumCheckpointType.STAGE_COMPLETION,
            EnumCheckpointType.SNAPSHOT,
            EnumCheckpointType.INCREMENTAL,
            EnumCheckpointType.COMPOSITION_BOUNDARY,
        ],
    )
    def test_automatic_checkpoint_types(
        self, checkpoint_type: EnumCheckpointType
    ) -> None:
        """Test that automatic checkpoint types return True."""
        assert EnumCheckpointType.is_automatic(checkpoint_type) is True

    def test_all_checkpoint_types_are_classified(self) -> None:
        """Test that all checkpoint types are classified as either automatic or manual."""
        for checkpoint_type in EnumCheckpointType:
            result = EnumCheckpointType.is_automatic(checkpoint_type)
            assert isinstance(result, bool)


@pytest.mark.unit
class TestEnumCheckpointTypeStrMethod:
    """Test cases for __str__ method."""

    def test_str_returns_value(self) -> None:
        """Test that __str__ returns the enum value."""
        assert str(EnumCheckpointType.MANUAL) == "manual"
        assert str(EnumCheckpointType.AUTOMATIC) == "automatic"
        assert str(EnumCheckpointType.FAILURE_RECOVERY) == "failure_recovery"
        assert str(EnumCheckpointType.STEP_COMPLETION) == "step_completion"
        assert str(EnumCheckpointType.COMPOSITION_BOUNDARY) == "composition_boundary"

    def test_str_in_format_string(self) -> None:
        """Test that enum works correctly in format strings."""
        checkpoint = EnumCheckpointType.SNAPSHOT
        formatted = f"Checkpoint type: {checkpoint}"
        assert formatted == "Checkpoint type: snapshot"
