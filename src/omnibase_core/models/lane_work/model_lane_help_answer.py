# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The help answer a responder tier returns, parsed at the lane boundary (OMN-26699)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_lane_work_blocked_reason import (
    EnumLaneWorkBlockedReason,
)
from omnibase_core.enums.enum_lane_work_state import EnumLaneWorkState


class ModelLaneHelpAnswer(BaseModel):
    """``help_cause_found``, ``help_retry`` with its origin, or ``help_stop`` with reason."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: Literal["help_cause_found", "help_retry", "help_stop"]
    cause: str | None = Field(default=None, min_length=1)
    correction: str | None = Field(default=None, min_length=1)
    help_origin: EnumLaneWorkState | None = None
    reason: EnumLaneWorkBlockedReason | None = None
    decision_needed: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _kind_fields(self) -> ModelLaneHelpAnswer:
        owed = {
            "help_cause_found": ("cause",),
            "help_retry": ("help_origin",),
            "help_stop": ("reason", "decision_needed"),
        }[self.kind]
        missing = [name for name in owed if getattr(self, name) is None]
        if missing:
            raise ValueError(f"{self.kind} requires {', '.join(missing)}")
        return self


__all__ = ["ModelLaneHelpAnswer"]
