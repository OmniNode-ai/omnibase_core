"""
Compensation Strategy Enum.

Strongly typed enumeration for workflow compensation strategies.
Replaces Literal["rollback", "forward_recovery", "mixed"] patterns.
"""

from __future__ import annotations

from enum import Enum, unique
from typing import Literal, assert_never

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumCompensationStrategy(StrValueHelper, str, Enum):
    """
    Strongly typed compensation strategy discriminators.

    Used for workflow error handling and recovery to specify how
    compensation actions should be performed. Inherits from str
    for JSON serialization compatibility while providing type safety
    and IDE support.
    """

    ROLLBACK = "rollback"
    FORWARD_RECOVERY = "forward_recovery"
    MIXED = "mixed"

    @classmethod
    def is_backward_looking(cls, strategy: EnumCompensationStrategy) -> bool:
        """Check if the strategy focuses on undoing previous actions."""
        return strategy in {cls.ROLLBACK, cls.MIXED}

    @classmethod
    def is_forward_looking(cls, strategy: EnumCompensationStrategy) -> bool:
        """Check if the strategy focuses on moving forward to recovery."""
        return strategy in {cls.FORWARD_RECOVERY, cls.MIXED}

    @classmethod
    def is_complex_strategy(cls, strategy: EnumCompensationStrategy) -> bool:
        """Check if the strategy involves multiple approaches."""
        return strategy == cls.MIXED

    @classmethod
    def is_single_approach_strategy(cls, strategy: EnumCompensationStrategy) -> bool:
        """Check if the strategy uses a single approach."""
        return strategy in {cls.ROLLBACK, cls.FORWARD_RECOVERY}

    @classmethod
    def requires_state_tracking(cls, strategy: EnumCompensationStrategy) -> bool:
        """Check if the strategy requires detailed state tracking."""
        return strategy in {cls.ROLLBACK, cls.MIXED}

    @classmethod
    def get_strategy_description(cls, strategy: EnumCompensationStrategy) -> str:
        """Get a human-readable description of the compensation strategy."""
        descriptions = {
            cls.ROLLBACK: "Undo previous actions to restore prior state",
            cls.FORWARD_RECOVERY: "Continue forward with corrective actions",
            cls.MIXED: "Combine rollback and forward recovery as appropriate",
        }
        return descriptions.get(strategy, "Unknown compensation strategy")

    @classmethod
    def get_typical_use_case(cls, strategy: EnumCompensationStrategy) -> str:
        """Get typical use case for each compensation strategy."""
        use_cases = {
            cls.ROLLBACK: "Database transactions, file operations with backup",
            cls.FORWARD_RECOVERY: "API calls, external service interactions",
            cls.MIXED: "Complex workflows with multiple operation types",
        }
        return use_cases.get(strategy, "Unknown use case")

    @classmethod
    def get_complexity_level(
        cls,
        strategy: EnumCompensationStrategy,
    ) -> Literal["low", "medium", "high", "unknown"]:
        """Get the complexity level of implementing the strategy."""
        if strategy == cls.ROLLBACK:
            return "medium"
        if strategy == cls.FORWARD_RECOVERY:
            return "low"
        if strategy == cls.MIXED:
            return "high"
        # This should never be reached for valid enum values
        assert_never(strategy)


# Export for use
__all__ = ["EnumCompensationStrategy"]
