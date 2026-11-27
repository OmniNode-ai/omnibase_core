# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One responder tier of the help chain (OMN-26699, plan section 3.5)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.lane_work.model_lane_work_action import LaneWorkRecordId


class ModelLaneHelpTier(BaseModel):
    """A tier names one delegation backend and what that backend must run with."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    name: str = Field(min_length=1)
    backend_id: LaneWorkRecordId
    harness: str = Field(min_length=1)
    model: str = Field(min_length=1)
    effort: str = Field(min_length=1)


__all__ = ["ModelLaneHelpTier"]
