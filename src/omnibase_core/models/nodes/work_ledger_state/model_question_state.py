# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One question's derived state (OMN-19620, typed work ledger T17)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_question_status import EnumQuestionStatus
from omnibase_core.models.events.work.model_work_operator_consent_recorded import (
    ModelWorkOperatorConsentRecorded,
)
from omnibase_core.models.events.work.model_work_question_asked import (
    ModelWorkQuestionAsked,
)
from omnibase_core.models.events.work.model_work_question_withdrawn import (
    ModelWorkQuestionWithdrawn,
)
from omnibase_core.models.events.work.model_work_ruling_recorded import (
    ModelWorkRulingRecorded,
)

__all__ = ["ModelQuestionState"]


class ModelQuestionState(BaseModel):
    """A question, its status, and every answer and withdrawal that names it.

    ANSWERED outranks WITHDRAWN. A withdrawal recorded beside an answer is kept
    here for display and never changes the status.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    question: ModelWorkQuestionAsked = Field(..., description="The question.")
    status: EnumQuestionStatus = Field(..., description="OPEN, ANSWERED or WITHDRAWN.")
    answered_by: tuple[
        ModelWorkRulingRecorded | ModelWorkOperatorConsentRecorded, ...
    ] = Field(
        default=(),
        description="Rulings and consents naming the question, sorted by event_id.",
    )
    withdrawn_by: tuple[ModelWorkQuestionWithdrawn, ...] = Field(
        default=(),
        description="Withdrawals naming the question, sorted by event_id.",
    )
