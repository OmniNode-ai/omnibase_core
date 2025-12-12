"""
TypedDict for action validation statistics.

Provides typed statistics for action validation history and metrics.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, NotRequired, TypedDict

if TYPE_CHECKING:
    from omnibase_core.models.core.model_action_validation_result import (
        ModelActionValidationResult,
    )


class TypedDictActionValidationStatistics(TypedDict, total=False):
    """TypedDict for action validation statistics.

    Captures validation history metrics including success rates,
    trust scores, and recent validation results.

    All fields are optional (total=False) except total_validations.
    """

    total_validations: int
    valid_actions: NotRequired[int]
    invalid_actions: NotRequired[int]
    success_rate: NotRequired[float]
    average_trust_score: NotRequired[float]
    recent_validations: NotRequired[list[ModelActionValidationResult]]


__all__ = ["TypedDictActionValidationStatistics"]
