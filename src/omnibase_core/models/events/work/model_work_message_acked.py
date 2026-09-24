# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Message-acked work event (OMN-16177, typed work ledger).

Acknowledges one message, hold or ruling by its ``event_id``. Whether the named
event exists, and is of an acknowledgeable kind, is checked by the fold, which
sees both events. Like a message, an ack carries no consent field.
"""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import Field, model_validator

from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.models.events.work.model_work_event_base import ModelWorkEventBase

__all__ = ["ModelWorkMessageAcked"]


class ModelWorkMessageAcked(ModelWorkEventBase):
    """An acknowledgement of one message, hold or ruling."""

    kind: Literal[EnumWorkEventKind.MESSAGE_ACKED] = Field(
        default=EnumWorkEventKind.MESSAGE_ACKED, frozen=True
    )
    re: uuid.UUID = Field(
        ...,
        description="event_id of the message, hold or ruling acknowledged.",
    )

    @model_validator(mode="after")
    def _does_not_ack_itself(self) -> ModelWorkMessageAcked:
        if self.re == self.event_id:
            raise ValueError("an ack cannot acknowledge itself (re equals event_id)")
        return self
