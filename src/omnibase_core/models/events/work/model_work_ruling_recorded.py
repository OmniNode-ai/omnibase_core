# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Ruling-recorded work event (OMN-16177)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from omnibase_core.enums.enum_work_event_kind import EnumWorkEventKind
from omnibase_core.models.events.work.model_work_event_base import ModelWorkEventBase

__all__ = ["ModelWorkRulingRecorded"]


class ModelWorkRulingRecorded(ModelWorkEventBase):
    """An operator ruling, recorded against the actor that received it."""

    kind: Literal[EnumWorkEventKind.RULING_RECORDED] = Field(
        default=EnumWorkEventKind.RULING_RECORDED, frozen=True
    )
