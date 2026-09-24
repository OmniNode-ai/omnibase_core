# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A hold release the work-ledger fold refused (OMN-19405, typed work ledger T4)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_invalid_release_reason import EnumInvalidReleaseReason
from omnibase_core.models.events.work.model_work_hold_released import (
    ModelWorkHoldReleased,
)

__all__ = ["ModelInvalidRelease"]


class ModelInvalidRelease(BaseModel):
    """A release that released nothing, and why."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    release: ModelWorkHoldReleased = Field(..., description="The refused release.")
    reason: EnumInvalidReleaseReason = Field(..., description="Why it was refused.")
