# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Question-withdrawn work event (OMN-19620, typed work ledger T17).

The asker of a question, or the lane holding it, withdraws it because events
overtook it, it duplicates another question, or its premise proved false. The
event names the question by event_id, gives the reason class, and cites typed
evidence.

A withdrawal is not an answer. Only the operator answers, through a ruling or a
consent that names the question. So this model has no answer-shaped or
consent-shaped field (``extra="forbid"`` refuses one smuggled in), and its actor
may not be a human identity: a withdrawal recorded as the operator would be an
answer given on the operator's behalf. Any lane may withdraw any question, with
its actor recorded, so a dead lane's question is not stranded (the plan's D7
reasoning for holds).
"""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import Field, model_validator

from omnibase_core.enums.enum_question_withdrawal_reason import (
    EnumQuestionWithdrawalReason,
)
from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.models.events.work.model_evidence_refs import ModelEvidenceRefs
from omnibase_core.models.events.work.model_session_actor import ModelSessionActor
from omnibase_core.models.events.work.model_work_event_base import ModelWorkEventBase
from omnibase_core.models.events.work.model_work_operator_consent_recorded import (
    CONSENT_APPROVERS,
)

__all__ = ["ModelWorkQuestionWithdrawn"]


class ModelWorkQuestionWithdrawn(ModelWorkEventBase):
    """Withdraws one question, naming it by event_id. Never an answer."""

    kind: Literal[EnumWorkEventKind.QUESTION_WITHDRAWN] = Field(
        default=EnumWorkEventKind.QUESTION_WITHDRAWN, frozen=True
    )
    withdraws: uuid.UUID = Field(
        ..., description="event_id of the work.question.asked being withdrawn."
    )
    reason: EnumQuestionWithdrawalReason = Field(
        ..., description="Why the question stopped being one."
    )
    evidence: ModelEvidenceRefs = Field(
        ..., description="What shows the reason holds. Never empty."
    )

    @model_validator(mode="after")
    def _check_withdrawal(self) -> ModelWorkQuestionWithdrawn:
        if self.withdraws == self.event_id:
            raise ValueError(
                "a withdrawal cannot withdraw itself (withdraws equals event_id)"
            )
        if (
            isinstance(self.actor, ModelSessionActor)
            and self.actor.session_handle.strip().lower() in CONSENT_APPROVERS
        ):
            raise ValueError(
                f"a question is never withdrawn by {self.actor.session_handle!r}: a "
                "withdrawal by a human identity would answer on the operator's "
                "behalf; the operator answers with a ruling or consent naming it"
            )
        if self.reason is EnumQuestionWithdrawalReason.DUPLICATE and not (
            self.evidence.events or self.evidence.ledger_rows
        ):
            raise ValueError(
                "a DUPLICATE withdrawal names the question it duplicates: give an "
                "evidence event or ledger row"
            )
        return self
