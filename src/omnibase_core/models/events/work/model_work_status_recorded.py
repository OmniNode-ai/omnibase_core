# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Status-recorded work event (OMN-16177, typed work ledger).

A progress or verification note. The PRs it cites are structured, and a
countersign names the event it countersigns. ``verdict`` is a display label
only: no checker decides anything from it.
"""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import Field, model_validator

from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.models.events.work.model_pr_ref import ModelPrRef
from omnibase_core.models.events.work.model_work_event_base import ModelWorkEventBase

__all__ = ["ModelWorkStatusRecorded"]

VERDICT_MAX_LENGTH = 200


class ModelWorkStatusRecorded(ModelWorkEventBase):
    """A progress or verification note with structured citations."""

    kind: Literal[EnumWorkEventKind.STATUS_RECORDED] = Field(
        default=EnumWorkEventKind.STATUS_RECORDED, frozen=True
    )
    pr_refs: tuple[ModelPrRef, ...] = Field(
        default=(), description="Pull requests this status cites."
    )
    countersigns: uuid.UUID | None = Field(
        default=None,
        description="event_id of the event this status countersigns, when it is one.",
    )
    verdict: str | None = Field(
        default=None,
        min_length=1,
        max_length=VERDICT_MAX_LENGTH,
        description="Display label, e.g. 'GREEN'. Never read by a checker.",
    )

    @model_validator(mode="after")
    def _does_not_countersign_itself(self) -> ModelWorkStatusRecorded:
        if self.countersigns == self.event_id:
            raise ValueError("a status cannot countersign itself")
        return self
