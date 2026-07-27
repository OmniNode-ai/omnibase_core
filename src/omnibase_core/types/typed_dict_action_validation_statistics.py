# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
TypedDict for action validation statistics.

Provides typed statistics for action validation history and metrics.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import NotRequired, TypedDict


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
    # OMN-14337: element type was the action-validation-result domain model
    # (immovable); widened to covariant Sequence[object] to sever types->models.
    recent_validations: NotRequired[Sequence[object]]


__all__ = ["TypedDictActionValidationStatistics"]
