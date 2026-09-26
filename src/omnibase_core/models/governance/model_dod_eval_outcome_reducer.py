# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Clock-free shared reducer for a definition-of-done verification outcome."""

from __future__ import annotations

from omnibase_core.enums.governance.enum_dod_eval_outcome import EnumDodEvalOutcome
from omnibase_core.enums.governance.enum_dod_eval_refusal import EnumDodEvalRefusal
from omnibase_core.enums.governance.enum_dod_eval_verification_status import (
    EnumDodEvalVerificationStatus,
)
from omnibase_core.models.governance.model_dod_eval_input import ModelDodEvalInput
from omnibase_core.models.governance.model_dod_eval_verdict import ModelDodEvalVerdict

MINIMUM_BEHAVIOR_PROVING_CHECKS = 1


def resolve_dod_eval_outcome(
    evaluation: ModelDodEvalInput,
) -> ModelDodEvalVerdict:
    """Reduce stored verification facts to the one authoritative eval verdict.

    The input is Core-owned and carries no envelope, clock, database, or
    market type, so a durable row can be replayed without an application
    dependency. The declared precedence is: failed checks, non-verified
    status, no checks, then no behavior-proving check.
    """
    if evaluation.failed_count > 0:
        return ModelDodEvalVerdict(
            outcome=EnumDodEvalOutcome.REFUSED,
            refusal=EnumDodEvalRefusal.CHECKS_FAILED,
        )
    if evaluation.status is not EnumDodEvalVerificationStatus.VERIFIED:
        return ModelDodEvalVerdict(
            outcome=EnumDodEvalOutcome.REFUSED,
            refusal=EnumDodEvalRefusal.STATUS_NOT_VERIFIED,
        )
    if evaluation.total_checks <= 0:
        return ModelDodEvalVerdict(
            outcome=EnumDodEvalOutcome.REFUSED,
            refusal=EnumDodEvalRefusal.NO_CHECKS_RUN,
        )
    if evaluation.behavior_proving_count < MINIMUM_BEHAVIOR_PROVING_CHECKS:
        return ModelDodEvalVerdict(
            outcome=EnumDodEvalOutcome.REFUSED,
            refusal=EnumDodEvalRefusal.NO_BEHAVIOR_PROVING_CHECK,
        )
    return ModelDodEvalVerdict(outcome=EnumDodEvalOutcome.DONE)


__all__ = ["MINIMUM_BEHAVIOR_PROVING_CHECKS", "resolve_dod_eval_outcome"]
