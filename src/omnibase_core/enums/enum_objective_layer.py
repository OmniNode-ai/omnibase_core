# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Objective layer enum for the three-layer objective architecture.

Defines the three distinct objective layers in OmniNode's reward
architecture (OMN-2537). Conflating these layers leads to failure.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ["EnumObjectiveLayer"]


@unique
class EnumObjectiveLayer(StrValueHelper, str, Enum):
    """The three distinct objective layers in OmniNode.

    Conflating these layers leads to metric collapse. Each layer has
    a distinct scope, form, and set of evaluation primitives.

    Attributes:
        TASK: Single execution of a contract (Evidence -> ScoreVector + GateStatus).
        POLICY: Behavior across many runs (AggregatedEvidence -> RewardDelta -> PolicyStateUpdate).
        SYSTEM: Platform economics and governance (MultiObjectiveVector + LexicographicOrdering).
    """

    TASK = "task"
    """Single execution of a contract.

    Defines what success means for one run.
    Form: Evidence -> ScoreVector + GateStatus.
    Properties: deterministic, versioned, replayable.
    """

    POLICY = "policy"
    """Behavior across many runs.

    Defines how agents and tools should evolve over time.
    Form: AggregatedEvidence -> RewardDelta -> PolicyStateUpdate.
    """

    SYSTEM = "system"
    """Platform economics and governance.

    Covers cost minimization, risk budgets, compliance, and PII containment.
    Form: MultiObjectiveVector + LexicographicOrdering.
    """
