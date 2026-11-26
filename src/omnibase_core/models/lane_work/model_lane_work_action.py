# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One action a lane work fold emits, by the worker or by a node (OMN-26699)."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError

# Plain characters only, so an action id is a valid lab work_unit_id.
ACTION_ID_PATTERN = r"^[a-z0-9-]{8,64}$"
WORKFLOW_ID_PATTERN = r"^[a-z0-9][a-z0-9-]{0,53}$"
MAX_WORKFLOW_ID_LENGTH = 54
MAX_ACTION_SEQ = 999_999
MAX_ACTION_INDEX = 99

LaneWorkActionId = Annotated[str, StringConstraints(pattern=ACTION_ID_PATTERN)]
LaneWorkWorkflowId = Annotated[str, StringConstraints(pattern=WORKFLOW_ID_PATTERN)]
# A caller-chosen record key (input, receipt, request, deadline): plain text, bounded.
LaneWorkRecordId = Annotated[str, StringConstraints(min_length=1, max_length=128)]


def build_action_id(workflow_id: str, seq: int, index: int) -> str:
    """Return ``<workflow id>-<seq>-<k>``, at most 64 plain characters."""
    if not 0 <= seq <= MAX_ACTION_SEQ:
        raise ModelOnexError(
            message=f"seq must be 0..{MAX_ACTION_SEQ}, got {seq}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    if not 0 <= index <= MAX_ACTION_INDEX:
        raise ModelOnexError(
            message=f"index must be 0..{MAX_ACTION_INDEX}, got {index}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    return f"{workflow_id}-{seq}-{index}"


class ModelLaneWorkAction(BaseModel):
    """An agent action (done by the worker) or a node action (done by an effect node)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    actor: Literal["agent", "node"]
    action_id: LaneWorkActionId
    name: str = Field(
        min_length=1, description="What is to be done, e.g. read_failing_log."
    )
    inputs: dict[str, str] = Field(default_factory=dict)
    deadline_at: AwareDatetime | None = None


__all__ = [
    "ACTION_ID_PATTERN",
    "MAX_ACTION_INDEX",
    "MAX_ACTION_SEQ",
    "MAX_WORKFLOW_ID_LENGTH",
    "WORKFLOW_ID_PATTERN",
    "LaneWorkActionId",
    "LaneWorkRecordId",
    "LaneWorkWorkflowId",
    "ModelLaneWorkAction",
    "build_action_id",
]
