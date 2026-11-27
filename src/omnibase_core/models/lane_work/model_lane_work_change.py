# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The change a lane work workflow is about: one pull request (OMN-26699)."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.lane_work.model_lane_work_action import (
    MAX_WORKFLOW_ID_LENGTH,
)


def workflow_id_for(owner: str, repo: str, pr_number: int, attempt: int) -> str:
    """Return ``<owner>-<repo>-<pr>-<n>`` in plain characters; refuse one over the limit."""
    plain = re.sub(r"[^a-z0-9]+", "-", f"{owner}-{repo}".lower()).strip("-")
    workflow_id = f"{plain}-{pr_number}-{attempt}"
    if len(workflow_id) > MAX_WORKFLOW_ID_LENGTH:
        raise ModelOnexError(
            message=f"workflow id {workflow_id!r} is over {MAX_WORKFLOW_ID_LENGTH} characters",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    return workflow_id


class ModelLaneWorkChange(BaseModel):
    """One pull request and the ticket it carries."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    owner: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
    repo: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
    pr_number: int = Field(ge=1)
    ticket: str | None = Field(default=None, pattern=r"^OMN-[0-9]+$")


__all__ = ["ModelLaneWorkChange", "workflow_id_for"]
