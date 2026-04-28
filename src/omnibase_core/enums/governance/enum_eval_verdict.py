# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Eval Verdict Enum.

Verdict for an A/B comparison of a single eval task.
"""

from enum import Enum, unique


@unique
class EnumEvalVerdict(str, Enum):
    """Verdict for a paired A/B eval comparison.

    - ONEX_BETTER: ONEX ON produced better metrics than ONEX OFF
    - ONEX_WORSE: ONEX ON produced worse metrics than ONEX OFF
    - NEUTRAL: No significant difference between modes
    - INCOMPLETE: One or both runs missing, cannot compare
    """

    ONEX_BETTER = "onex_better"
    """ONEX features improved outcomes."""

    ONEX_WORSE = "onex_worse"
    """ONEX features degraded outcomes."""

    NEUTRAL = "neutral"
    """No significant difference detected."""

    INCOMPLETE = "incomplete"
    """One or both runs missing; cannot determine verdict."""

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value
