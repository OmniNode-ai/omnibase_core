# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The step reply published after every fold of a caller's input (OMN-26699, plan section 3.1)."""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_lane_work_state import EnumLaneWorkState
from omnibase_core.models.lane_work.model_lane_work_action import (
    LaneWorkRecordId,
    LaneWorkWorkflowId,
    ModelLaneWorkAction,
)
from omnibase_core.models.lane_work.model_lane_work_terminal import (
    ModelLaneWorkTerminal,
)


class ModelLaneWorkStepReply(BaseModel):
    """Workflow id, new state, receipt id and ``next_action``: an agent action, wait or stop."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    workflow_id: LaneWorkWorkflowId
    state: EnumLaneWorkState
    seq: int = Field(ge=0)
    receipt_id: LaneWorkRecordId
    next_action: Literal["agent_action", "wait", "stop"]
    action: ModelLaneWorkAction | None = None
    wait_deadline: AwareDatetime | None = None
    terminal: ModelLaneWorkTerminal | None = None

    @model_validator(mode="after")
    def _next_action_fields(self) -> ModelLaneWorkStepReply:
        carried = {
            "agent_action": self.action,
            "wait": self.wait_deadline,
            "stop": self.terminal,
        }
        for name, value in carried.items():
            if name == self.next_action and value is None:
                raise ValueError(f"next_action {name} requires its payload")
            if name != self.next_action and value is not None:
                raise ValueError(
                    f"next_action {self.next_action} carries no {name} payload"
                )
        if self.action is not None and self.action.actor != "agent":
            raise ValueError("next_action agent_action requires an agent action")
        return self


__all__ = ["ModelLaneWorkStepReply"]
