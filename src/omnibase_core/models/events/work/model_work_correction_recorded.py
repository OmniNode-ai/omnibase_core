# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Correction-recorded work event (OMN-16177)."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import Field, model_validator

from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.models.events.work.model_work_event_base import ModelWorkEventBase

__all__ = ["ModelWorkCorrectionRecorded"]


class ModelWorkCorrectionRecorded(ModelWorkEventBase):
    """A correction to an earlier record. Append-only, never an in-place edit."""

    kind: Literal[EnumWorkEventKind.CORRECTION_RECORDED] = Field(
        default=EnumWorkEventKind.CORRECTION_RECORDED, frozen=True
    )
    corrects: uuid.UUID | None = Field(
        default=None,
        description="event_id of the typed event this corrects, when it corrects one.",
    )
    corrects_legacy_ts: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
        description="Timestamp of the legacy markdown row this corrects. Display only.",
    )

    @model_validator(mode="after")
    def _does_not_correct_itself(self) -> ModelWorkCorrectionRecorded:
        if self.corrects == self.event_id:
            raise ValueError("a correction cannot correct itself")
        return self
