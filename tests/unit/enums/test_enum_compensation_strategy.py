# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for EnumCompensationStrategy.

Tests all aspects of the compensation strategy enum including:
- Enum value validation
- Helper methods for strategy classification
- String representation
- JSON serialization compatibility
- Pydantic integration
- Complexity level assessment
"""

import json

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_compensation_strategy import EnumCompensationStrategy


@pytest.mark.unit
class TestEnumCompensationStrategy:
    """Test cases for EnumCompensationStrategy."""

    def test_enum_values(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "ROLLBACK": "rollback",
            "FORWARD_RECOVERY": "forward_recovery",
            "MIXED": "mixed",
        }

        for name, value in expected_values.items():
            strategy = getattr(EnumCompensationStrategy, name)
            assert strategy.value == value
            assert str(strategy) == value

    def test_string_inheritance(self):
        """Test that enum inherits from str."""
        assert isinstance(EnumCompensationStrategy.ROLLBACK, str)
        assert EnumCompensationStrategy.ROLLBACK == "rollback"

    def test_string_representation(self):
        """Test string representation of enum values."""
        assert str(EnumCompensationStrategy.ROLLBACK) == "rollback"
        assert str(EnumCompensationStrategy.FORWARD_RECOVERY) == "forward_recovery"
        assert str(EnumCompensationStrategy.MIXED) == "mixed"

    def test_is_backward_looking(self):
        """Test the is_backward_looking class method."""
        assert (
            EnumCompensationStrategy.is_backward_looking(
                EnumCompensationStrategy.ROLLBACK
            )
            is True
        )
        assert (
            EnumCompensationStrategy.is_backward_looking(EnumCompensationStrategy.MIXED)
            is True
        )
        assert (
            EnumCompensationStrategy.is_backward_looking(
                EnumCompensationStrategy.FORWARD_RECOVERY
            )
            is False
        )

    def test_is_forward_looking(self):
        """Test the is_forward_looking class method."""
        assert (
            EnumCompensationStrategy.is_forward_looking(
                EnumCompensationStrategy.FORWARD_RECOVERY
            )
            is True
        )
        assert (
            EnumCompensationStrategy.is_forward_looking(EnumCompensationStrategy.MIXED)
            is True
        )
        assert (
            EnumCompensationStrategy.is_forward_looking(
                EnumCompensationStrategy.ROLLBACK
            )
            is False
        )

    def test_is_complex_strategy(self):
        """Test the is_complex_strategy class method."""
        assert (
            EnumCompensationStrategy.is_complex_strategy(EnumCompensationStrategy.MIXED)
            is True
        )
        assert (
            EnumCompensationStrategy.is_complex_strategy(
                EnumCompensationStrategy.ROLLBACK
            )
            is False
        )
        assert (
            EnumCompensationStrategy.is_complex_strategy(
                EnumCompensationStrategy.FORWARD_RECOVERY
            )
            is False
        )

    def test_is_single_approach_strategy(self):
        """Test the is_single_approach_strategy class method."""
        assert (
            EnumCompensationStrategy.is_single_approach_strategy(
                EnumCompensationStrategy.ROLLBACK
            )
            is True
        )
        assert (
            EnumCompensationStrategy.is_single_approach_strategy(
                EnumCompensationStrategy.FORWARD_RECOVERY
            )
            is True
        )
        assert (
            EnumCompensationStrategy.is_single_approach_strategy(
                EnumCompensationStrategy.MIXED
            )
            is False
        )

    def test_requires_state_tracking(self):
        """Test the requires_state_tracking class method."""
        assert (
            EnumCompensationStrategy.requires_state_tracking(
                EnumCompensationStrategy.ROLLBACK
            )
            is True
        )
        assert (
            EnumCompensationStrategy.requires_state_tracking(
                EnumCompensationStrategy.MIXED
            )
            is True
        )
        assert (
            EnumCompensationStrategy.requires_state_tracking(
                EnumCompensationStrategy.FORWARD_RECOVERY
            )
            is False
        )

    def test_get_strategy_description(self):
        """Test the get_strategy_description class method."""
        rollback_desc = EnumCompensationStrategy.get_strategy_description(
            EnumCompensationStrategy.ROLLBACK
        )
        assert "Undo previous actions" in rollback_desc

        forward_desc = EnumCompensationStrategy.get_strategy_description(
            EnumCompensationStrategy.FORWARD_RECOVERY
        )
        assert "Continue forward" in forward_desc

        mixed_desc = EnumCompensationStrategy.get_strategy_description(
            EnumCompensationStrategy.MIXED
        )
        assert "Combine rollback and forward" in mixed_desc

    def test_get_typical_use_case(self):
        """Test the get_typical_use_case class method."""
        rollback_use = EnumCompensationStrategy.get_typical_use_case(
            EnumCompensationStrategy.ROLLBACK
        )
        assert "Database transactions" in rollback_use

        forward_use = EnumCompensationStrategy.get_typical_use_case(
            EnumCompensationStrategy.FORWARD_RECOVERY
        )
        assert "API calls" in forward_use

        mixed_use = EnumCompensationStrategy.get_typical_use_case(
            EnumCompensationStrategy.MIXED
        )
        assert "Complex workflows" in mixed_use

    def test_get_complexity_level(self):
        """Test the get_complexity_level class method."""
        rollback_complexity = EnumCompensationStrategy.get_complexity_level(
            EnumCompensationStrategy.ROLLBACK
        )
        assert rollback_complexity == "medium"

        forward_complexity = EnumCompensationStrategy.get_complexity_level(
            EnumCompensationStrategy.FORWARD_RECOVERY
        )
        assert forward_complexity == "low"

        mixed_complexity = EnumCompensationStrategy.get_complexity_level(
            EnumCompensationStrategy.MIXED
        )
        assert mixed_complexity == "high"

    def test_enum_equality(self):
        """Test enum equality comparison."""
        assert EnumCompensationStrategy.ROLLBACK == EnumCompensationStrategy.ROLLBACK
        assert EnumCompensationStrategy.MIXED != EnumCompensationStrategy.ROLLBACK

    def test_enum_membership(self):
        """Test enum membership checking."""
        all_strategies = [
            EnumCompensationStrategy.ROLLBACK,
            EnumCompensationStrategy.FORWARD_RECOVERY,
            EnumCompensationStrategy.MIXED,
        ]

        for strategy in all_strategies:
            assert strategy in EnumCompensationStrategy

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        strategies = list(EnumCompensationStrategy)
        assert len(strategies) == 3

        strategy_values = [s.value for s in strategies]
        assert set(strategy_values) == {"rollback", "forward_recovery", "mixed"}

    def test_json_serialization(self):
        """Test JSON serialization compatibility."""
        # Test direct serialization
        strategy = EnumCompensationStrategy.ROLLBACK
        json_str = json.dumps(strategy, default=str)
        assert json_str == '"rollback"'

        # Test in dictionary
        data = {"strategy": EnumCompensationStrategy.MIXED}
        json_str = json.dumps(data, default=str)
        assert '"strategy": "mixed"' in json_str

    def test_pydantic_integration(self):
        """Test integration with Pydantic models."""

        class WorkflowConfig(BaseModel):
            strategy: EnumCompensationStrategy

        # Test valid enum assignment
        config = WorkflowConfig(strategy=EnumCompensationStrategy.ROLLBACK)
        assert config.strategy == EnumCompensationStrategy.ROLLBACK

        # Test string assignment (should work due to str inheritance)
        config = WorkflowConfig(strategy="forward_recovery")
        assert config.strategy == EnumCompensationStrategy.FORWARD_RECOVERY

        # Test invalid value should raise ValidationError
        with pytest.raises(ValidationError):
            WorkflowConfig(strategy="invalid_strategy")

    def test_pydantic_serialization(self):
        """Test Pydantic model serialization."""

        class WorkflowConfig(BaseModel):
            strategy: EnumCompensationStrategy

        config = WorkflowConfig(strategy=EnumCompensationStrategy.MIXED)

        # Test dict serialization
        config_dict = config.model_dump()
        assert config_dict == {"strategy": "mixed"}

        # Test JSON serialization
        json_str = config.model_dump_json()
        assert json_str == '{"strategy":"mixed"}'

    def test_strategy_characteristics(self):
        """Test comprehensive strategy characteristics."""
        # ROLLBACK: backward, single approach, requires state tracking
        assert (
            EnumCompensationStrategy.is_backward_looking(
                EnumCompensationStrategy.ROLLBACK
            )
            is True
        )
        assert (
            EnumCompensationStrategy.is_single_approach_strategy(
                EnumCompensationStrategy.ROLLBACK
            )
            is True
        )
        assert (
            EnumCompensationStrategy.requires_state_tracking(
                EnumCompensationStrategy.ROLLBACK
            )
            is True
        )
        assert (
            EnumCompensationStrategy.get_complexity_level(
                EnumCompensationStrategy.ROLLBACK
            )
            == "medium"
        )

        # FORWARD_RECOVERY: forward, single approach, no state tracking
        assert (
            EnumCompensationStrategy.is_forward_looking(
                EnumCompensationStrategy.FORWARD_RECOVERY
            )
            is True
        )
        assert (
            EnumCompensationStrategy.is_single_approach_strategy(
                EnumCompensationStrategy.FORWARD_RECOVERY
            )
            is True
        )
        assert (
            EnumCompensationStrategy.requires_state_tracking(
                EnumCompensationStrategy.FORWARD_RECOVERY
            )
            is False
        )
        assert (
            EnumCompensationStrategy.get_complexity_level(
                EnumCompensationStrategy.FORWARD_RECOVERY
            )
            == "low"
        )

        # MIXED: both directions, complex, requires state tracking
        assert (
            EnumCompensationStrategy.is_backward_looking(EnumCompensationStrategy.MIXED)
            is True
        )
        assert (
            EnumCompensationStrategy.is_forward_looking(EnumCompensationStrategy.MIXED)
            is True
        )
        assert (
            EnumCompensationStrategy.is_complex_strategy(EnumCompensationStrategy.MIXED)
            is True
        )
        assert (
            EnumCompensationStrategy.requires_state_tracking(
                EnumCompensationStrategy.MIXED
            )
            is True
        )
        assert (
            EnumCompensationStrategy.get_complexity_level(
                EnumCompensationStrategy.MIXED
            )
            == "high"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
