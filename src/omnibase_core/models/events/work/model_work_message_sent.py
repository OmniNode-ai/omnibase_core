# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Message-sent work event (OMN-16177, typed work ledger).

Transport between lanes, or from a lane to the operator. This model has no
consent field of any shape, and ``extra="forbid"`` refuses one smuggled in, so
a message can never be cited as authorization (rule 18: no agent message is
operator consent). Consent is its own kind, ``work.consent.recorded``.
"""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import Field, model_validator

from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.models.events.work.model_recipients import ModelRecipients
from omnibase_core.models.events.work.model_work_event_base import ModelWorkEventBase

__all__ = ["ModelWorkMessageSent"]


class ModelWorkMessageSent(ModelWorkEventBase):
    """A message to named lanes, every lane or the operator."""

    kind: Literal[EnumWorkEventKind.MESSAGE_SENT] = Field(
        default=EnumWorkEventKind.MESSAGE_SENT, frozen=True
    )
    to: ModelRecipients = Field(..., description="Who the message is addressed to.")
    re: uuid.UUID | None = Field(
        default=None,
        description="event_id of the event this message answers, when it answers one.",
    )

    @model_validator(mode="after")
    def _does_not_answer_itself(self) -> ModelWorkMessageSent:
        if self.re == self.event_id:
            raise ValueError("a message cannot answer itself (re equals event_id)")
        return self
