# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One corrected event and its corrections (OMN-21107, TA.5)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.models.events.work.model_work_correction_recorded import (
    ModelWorkCorrectionRecorded,
)

__all__ = ["ModelCorrectedEvent"]


class ModelCorrectedEvent(BaseModel):
    """An event of any kind that at least one correction names.

    A correction never closes what it corrects: this entry is the record of
    the correction closure for display, not a change to the target's state.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    target: uuid.UUID = Field(..., description="The corrected event's event_id.")
    target_kind: EnumWorkEventKind = Field(
        ..., description="The corrected event's kind."
    )
    corrected_by: tuple[ModelWorkCorrectionRecorded, ...] = Field(
        default=(),
        description="Corrections naming it, sorted by event_id.",
    )
