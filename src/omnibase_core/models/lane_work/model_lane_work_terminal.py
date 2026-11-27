# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The terminal of a lane work workflow (OMN-26699, plan section 3.7)."""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_lane_work_blocked_reason import (
    EnumLaneWorkBlockedReason,
)
from omnibase_core.enums.enum_lane_work_state import EnumLaneWorkState
from omnibase_core.models.lane_work.model_lane_work_action import (
    LaneWorkRecordId,
    LaneWorkWorkflowId,
)
from omnibase_core.models.lane_work.model_lane_work_change import ModelLaneWorkChange


class ModelLaneWorkTerminal(BaseModel):
    """One schema for both kinds, with the fields each kind owes checked by kind."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    workflow_id: LaneWorkWorkflowId
    seq: int = Field(ge=1, description="The final seq.")
    kind: Literal["handed_off", "blocked"]
    change: ModelLaneWorkChange
    last_state: EnumLaneWorkState
    proven_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{7,40}$")
    handoff_request_id: LaneWorkRecordId | None = None
    proof_receipt_id: LaneWorkRecordId | None = None
    reason: EnumLaneWorkBlockedReason | None = None
    evidence: tuple[str, ...] = ()
    decision_needed: str | None = Field(
        default=None, min_length=1, description="blocked only: a question, or 'none'."
    )
    decision_owner: str | None = Field(
        default=None,
        min_length=1,
        description="Who owns the outcome when decision is 'none'.",
    )
    transitions_taken: int = Field(ge=0)
    help_requests_by_tier: dict[str, int] = Field(default_factory=dict)
    started_at: AwareDatetime
    ended_at: AwareDatetime

    @model_validator(mode="after")
    def _terminal_kind_fields(self) -> ModelLaneWorkTerminal:
        if self.ended_at < self.started_at:
            raise ValueError("ended_at is before started_at")
        if self.kind == "handed_off":
            missing = [
                name
                for name in ("proven_head", "handoff_request_id", "proof_receipt_id")
                if getattr(self, name) is None
            ]
            if missing:
                raise ValueError(f"a handed_off terminal requires {', '.join(missing)}")
            if (
                self.reason is not None
                or self.decision_needed is not None
                or self.decision_owner is not None
            ):
                raise ValueError("a handed_off terminal carries no reason or decision")
        else:
            if self.reason is None:
                raise ValueError("a blocked terminal requires reason")
            if self.decision_needed is None:
                raise ValueError("a blocked terminal requires decision_needed")
            if self.decision_needed == "none" and self.decision_owner is None:
                raise ValueError("decision_needed 'none' requires decision_owner")
            if self.handoff_request_id is not None or self.proof_receipt_id is not None:
                raise ValueError("a blocked terminal carries no handoff or proof ids")
        return self


__all__ = ["ModelLaneWorkTerminal"]
