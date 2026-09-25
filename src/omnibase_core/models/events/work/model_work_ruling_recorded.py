# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Ruling-recorded work event (OMN-16177)."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import Field, field_serializer, field_validator, model_validator

from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.models.events.work.model_work_event_base import (
    SUMMARY_MAX_LENGTH,
    ModelWorkEventBase,
)

__all__ = ["ModelWorkRulingRecorded"]


class ModelWorkRulingRecorded(ModelWorkEventBase):
    """An operator ruling, recorded against the actor that received it."""

    kind: Literal[EnumWorkEventKind.RULING_RECORDED] = Field(
        default=EnumWorkEventKind.RULING_RECORDED, frozen=True
    )
    operator_words: str = Field(
        ...,
        min_length=1,
        max_length=SUMMARY_MAX_LENGTH,
        description="The operator's words, verbatim. Never read by a checker.",
    )
    amends: uuid.UUID | None = Field(
        default=None,
        description="event_id of the ruling this one amends, when it amends one.",
    )
    supersedes: uuid.UUID | None = Field(
        default=None,
        description="event_id of the ruling this one supersedes, when it supersedes one.",
    )

    answers: frozenset[uuid.UUID] = Field(
        default_factory=frozenset,
        description=(
            "event_ids of the work.question.asked events this ruling answers. The "
            "operator's typed answer: a question is answered only by a ruling or a "
            "consent that names it here."
        ),
    )

    @field_validator("operator_words")
    @classmethod
    def _reject_blank_words(cls, raw: str) -> str:
        if not raw.strip():
            raise ValueError("operator_words must not be blank or whitespace-only")
        return raw

    @model_validator(mode="after")
    def _does_not_name_itself(self) -> ModelWorkRulingRecorded:
        if self.event_id in (self.amends, self.supersedes):
            raise ValueError("a ruling cannot amend or supersede itself")
        if self.event_id in self.answers:
            raise ValueError("a ruling cannot answer itself")
        return self

    @field_serializer("answers")
    def _serialize_answers_sorted(self, value: frozenset[uuid.UUID]) -> list[str]:
        return sorted(str(event_id) for event_id in value)
