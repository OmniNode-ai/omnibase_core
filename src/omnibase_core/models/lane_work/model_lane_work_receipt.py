# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The transition receipt a fold publishes before its outputs (OMN-26699, plan section 3.6)."""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_lane_work_event import EnumLaneWorkEvent
from omnibase_core.enums.enum_lane_work_state import EnumLaneWorkState
from omnibase_core.models.lane_work.model_lane_work_action import (
    LaneWorkActionId,
    LaneWorkRecordId,
    LaneWorkWorkflowId,
    ModelLaneWorkAction,
)


class ModelLaneWorkReceipt(BaseModel):
    """One fold of one input. A refused input is a receipt kind, not a state."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    workflow_id: LaneWorkWorkflowId
    seq: int = Field(ge=1, description="The previous seq plus one.")
    receipt_id: LaneWorkRecordId
    kind: Literal["transition", "refused", "duplicate"]
    input_id: LaneWorkRecordId
    event_kind: EnumLaneWorkEvent
    from_state: EnumLaneWorkState
    to_state: EnumLaneWorkState
    action_ids: tuple[LaneWorkActionId, ...] = Field(
        description="Ids of the outputs this receipt lists, in order; may be empty."
    )
    actions: tuple[ModelLaneWorkAction, ...] = ()
    refusal: str | None = Field(default=None, min_length=1)
    occurred_at: AwareDatetime

    @model_validator(mode="after")
    def _consistent(self) -> ModelLaneWorkReceipt:
        if self.kind == "refused":
            if self.refusal is None:
                raise ValueError("a refused receipt must name its refusal")
            if self.to_state != self.from_state:
                raise ValueError("a refused receipt makes no transition")
        elif self.refusal is not None:
            raise ValueError("only a refused receipt carries a refusal")
        listed = {action.action_id for action in self.actions}
        if not listed <= set(self.action_ids):
            raise ValueError("every action must be listed in action_ids")
        return self


__all__ = ["ModelLaneWorkReceipt"]
