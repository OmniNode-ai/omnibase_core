# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Lifecycle states of the experiment FSM owned by the ab-compare reducer (OMN-22001)."""

from enum import Enum, unique

from omnibase_core.enums.enum_str_enum_base import UtilStrValueHelper


@unique
class EnumExperimentLifecycleState(UtilStrValueHelper, str, Enum):
    """The union of the MASS and LPX experiment lifecycles.

    Attributes:
        ADMITTED: The experiment is admitted.
        CALIBRATING: Calibration runs (passed through when the subject needs none).
        VALIDATING: The A/A validation runs (passed through when the subject needs none).
        ENROLLING: Units are being enrolled.
        SEALED: The manifest is sealed and its rule_sha fixed.
        BASELINE_FROZEN: The baseline snapshot is frozen.
        COLLECTING: Evidence is being collected.
        MATURE: The observation window has matured.
        EVALUATED: A verdict exists.
        DECIDED: A champion decision exists. Terminal.
        VOID: The experiment was voided. Terminal.
        CANCELLED: The experiment was cancelled. Terminal.
        BUDGET_EXHAUSTED: The budget ran out. Terminal.
        REFUSED: The loop refused to proceed. Terminal.
    """

    ADMITTED = "admitted"
    CALIBRATING = "calibrating"
    VALIDATING = "validating"
    ENROLLING = "enrolling"
    SEALED = "sealed"
    BASELINE_FROZEN = "baseline_frozen"
    COLLECTING = "collecting"
    MATURE = "mature"
    EVALUATED = "evaluated"
    DECIDED = "decided"
    VOID = "void"
    CANCELLED = "cancelled"
    BUDGET_EXHAUSTED = "budget_exhausted"
    REFUSED = "refused"

    @property
    def is_terminal(self) -> bool:
        """True for the five states the experiment never leaves."""
        return self in _TERMINAL

    @property
    def is_sealed_or_later(self) -> bool:
        """True once the manifest is sealed, so a rule_sha must exist."""
        return self in _SEALED_OR_LATER


_TERMINAL = frozenset(
    {
        EnumExperimentLifecycleState.DECIDED,
        EnumExperimentLifecycleState.VOID,
        EnumExperimentLifecycleState.CANCELLED,
        EnumExperimentLifecycleState.BUDGET_EXHAUSTED,
        EnumExperimentLifecycleState.REFUSED,
    }
)
_SEALED_OR_LATER = frozenset(
    {
        EnumExperimentLifecycleState.SEALED,
        EnumExperimentLifecycleState.BASELINE_FROZEN,
        EnumExperimentLifecycleState.COLLECTING,
        EnumExperimentLifecycleState.MATURE,
        EnumExperimentLifecycleState.EVALUATED,
        EnumExperimentLifecycleState.DECIDED,
    }
)
