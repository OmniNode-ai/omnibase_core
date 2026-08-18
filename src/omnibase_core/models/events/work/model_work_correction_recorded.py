# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Correction-recorded work event (OMN-16177)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.models.events.work.model_work_event_base import ModelWorkEventBase

__all__ = ["ModelWorkCorrectionRecorded"]


class ModelWorkCorrectionRecorded(ModelWorkEventBase):
    """A correction to an earlier record. Append-only, never an in-place edit."""

    kind: Literal[EnumWorkEventKind.CORRECTION_RECORDED] = Field(
        default=EnumWorkEventKind.CORRECTION_RECORDED, frozen=True
    )
