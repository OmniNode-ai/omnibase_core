# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The folded state of one lane work workflow (OMN-26699, plan sections 3.2 and 3.6)."""

from __future__ import annotations

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_lane_work_state import EnumLaneWorkState
from omnibase_core.models.lane_work.model_lane_help_tier import ModelLaneHelpTier
from omnibase_core.models.lane_work.model_lane_work_action import (
    LaneWorkActionId,
    LaneWorkWorkflowId,
)
from omnibase_core.models.lane_work.model_lane_work_change import ModelLaneWorkChange


class ModelLaneWorkState(BaseModel):
    """The fold of a workflow's receipts: state, expected head, counters, open actions."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    workflow_id: LaneWorkWorkflowId
    change: ModelLaneWorkChange
    state: EnumLaneWorkState = EnumLaneWorkState.QUEUED
    seq: int = Field(default=0, ge=0, description="Previous seq plus one on each fold.")
    attempt: int = Field(default=1, ge=1)
    worker_lane: str | None = None
    expected_head: str | None = None
    last_head_change_at: AwareDatetime | None = None
    help_origin: EnumLaneWorkState | None = None
    help_tiers: tuple[ModelLaneHelpTier, ...] = ()
    help_tier_index: int = Field(default=0, ge=0)
    help_episodes: int = Field(default=0, ge=0)
    repeat_counters: dict[str, int] = Field(
        default_factory=dict, description="One counter per 'event kind:class'."
    )
    outstanding_action_ids: tuple[LaneWorkActionId, ...] = ()
    seen_input_ids: tuple[str, ...] = ()
    terminals_published: tuple[str, ...] = ()


__all__ = ["ModelLaneWorkState"]
