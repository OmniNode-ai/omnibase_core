# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit coverage for the shared pure definition-of-done outcome reducer."""

from __future__ import annotations

import pytest

from omnibase_core.enums.governance.enum_dod_eval_outcome import EnumDodEvalOutcome
from omnibase_core.enums.governance.enum_dod_eval_refusal import EnumDodEvalRefusal
from omnibase_core.enums.governance.enum_dod_eval_verification_status import (
    EnumDodEvalVerificationStatus,
)
from omnibase_core.models.governance.model_dod_eval_input import ModelDodEvalInput
from omnibase_core.models.governance.model_dod_eval_outcome_reducer import (
    MINIMUM_BEHAVIOR_PROVING_CHECKS,
    resolve_dod_eval_outcome,
)
from omnibase_core.models.governance.model_dod_eval_verdict import ModelDodEvalVerdict


@pytest.mark.parametrize(
    ("status", "failed_count", "total_checks", "behavior_proving_count", "expected"),
    [
        (
            EnumDodEvalVerificationStatus.VERIFIED,
            2,
            5,
            1,
            EnumDodEvalRefusal.CHECKS_FAILED,
        ),
        (
            EnumDodEvalVerificationStatus.FAILED,
            0,
            5,
            1,
            EnumDodEvalRefusal.STATUS_NOT_VERIFIED,
        ),
        (
            EnumDodEvalVerificationStatus.VERIFIED,
            0,
            0,
            1,
            EnumDodEvalRefusal.NO_CHECKS_RUN,
        ),
        (
            EnumDodEvalVerificationStatus.VERIFIED,
            0,
            5,
            0,
            EnumDodEvalRefusal.NO_BEHAVIOR_PROVING_CHECK,
        ),
    ],
)
def test_resolve_dod_eval_outcome_refusal_precedence(
    status: EnumDodEvalVerificationStatus,
    failed_count: int,
    total_checks: int,
    behavior_proving_count: int,
    expected: EnumDodEvalRefusal,
) -> None:
    """The reducer has one deterministic refusal for each failed conjunct."""
    verdict = resolve_dod_eval_outcome(
        ModelDodEvalInput(
            status=status,
            failed_count=failed_count,
            total_checks=total_checks,
            behavior_proving_count=behavior_proving_count,
        )
    )

    assert verdict.outcome is EnumDodEvalOutcome.REFUSED
    assert verdict.refusal is expected


def test_resolve_dod_eval_outcome_accepts_typed_stored_facts() -> None:
    """A durable typed input can be replayed without market types."""
    verdict = resolve_dod_eval_outcome(
        ModelDodEvalInput(
            status=EnumDodEvalVerificationStatus.VERIFIED,
            failed_count=0,
            total_checks=1,
            behavior_proving_count=MINIMUM_BEHAVIOR_PROVING_CHECKS,
        )
    )

    assert verdict.outcome is EnumDodEvalOutcome.DONE
    assert verdict.refusal is None
    assert verdict.is_done is True


def test_dod_eval_verdict_requires_reason_exactly_for_refusal() -> None:
    """The shared typed verdict cannot represent ambiguous terminal state."""
    with pytest.raises(ValueError, match="refusal is set exactly when"):
        ModelDodEvalVerdict(outcome=EnumDodEvalOutcome.REFUSED)
