# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The help request sent to one responder tier (OMN-26699, plan section 3.5)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_lane_work_state import EnumLaneWorkState
from omnibase_core.models.lane_work.model_lane_help_tier import ModelLaneHelpTier
from omnibase_core.models.lane_work.model_lane_work_action import LaneWorkWorkflowId
from omnibase_core.models.lane_work.model_lane_work_receipt import ModelLaneWorkReceipt


class ModelLaneHelpRequest(BaseModel):
    """One typed help request: where the workflow is stuck and the one question."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    workflow_id: LaneWorkWorkflowId
    state: EnumLaneWorkState
    help_origin: EnumLaneWorkState
    last_receipts: tuple[ModelLaneWorkReceipt, ...] = Field(default=(), max_length=3)
    evidence_paths: tuple[str, ...] = ()
    five_whys: tuple[str, ...] = ()
    question: str = Field(min_length=1)
    tier: ModelLaneHelpTier


__all__ = ["ModelLaneHelpRequest"]
