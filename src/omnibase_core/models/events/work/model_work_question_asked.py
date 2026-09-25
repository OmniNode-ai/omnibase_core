# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Question-asked work event (OMN-19620, typed work ledger T17).

A question a lane puts to the operator: a decision it cannot make itself. It is
answered only when a ruling or a consent names it in ``answers``, and it can be
withdrawn by a ``work.question.withdrawn`` event. Both are typed references by
event_id, so the fold never reads the question's text.

There is no addressee field. A question in this kind is put to the operator,
the only person whose ruling answers it.

``legacy_row`` is set when the event re-issues a question first asked as a row
of the markdown ledger, so a reader of that row can find its typed status.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.models.events.work.model_ledger_row_ref import ModelLedgerRowRef
from omnibase_core.models.events.work.model_work_event_base import (
    SUMMARY_MAX_LENGTH,
    ModelWorkEventBase,
)

__all__ = ["ModelWorkQuestionAsked"]


class ModelWorkQuestionAsked(ModelWorkEventBase):
    """A question put to the operator. Answered only by a ruling or consent naming it."""

    kind: Literal[EnumWorkEventKind.QUESTION_ASKED] = Field(
        default=EnumWorkEventKind.QUESTION_ASKED, frozen=True
    )
    question: str = Field(
        ...,
        min_length=1,
        max_length=SUMMARY_MAX_LENGTH,
        description="The question, verbatim. Never read by a checker.",
    )
    recommendation: str | None = Field(
        default=None,
        max_length=SUMMARY_MAX_LENGTH,
        description="The asker's recommended answer, when it gives one. Never read by a checker.",
    )
    legacy_row: ModelLedgerRowRef | None = Field(
        default=None,
        description=(
            "The md ledger row this event re-issues, when the question was first "
            "asked there. None for a question first asked as a typed event."
        ),
    )

    @field_validator("question", "recommendation")
    @classmethod
    def _reject_blank(cls, raw: str | None) -> str | None:
        if raw is not None and not raw.strip():
            raise ValueError("must not be blank or whitespace-only")
        return raw
