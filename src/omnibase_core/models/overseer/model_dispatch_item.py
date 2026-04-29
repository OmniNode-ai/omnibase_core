# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDispatchItem — per-theme dispatch detail for ModelOvernightPhaseSpec (OMN-10251)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from omnibase_core.utils.util_decorators import allow_string_id


@allow_string_id(
    reason=(
        "theme_id is a domain-routing string identifier for overnight dispatch themes, "
        "not a system UUID."
    )
)
class ModelDispatchItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    theme_id: str  # string-id-ok: domain-routing string for overnight dispatch
    title: str
    target_repo: str
    dispatch_mode: Literal[
        "skill",
        "agent_team",
        "foreground_required",
        "blocked_on_human",
        "cron",
    ]
    skill_or_command: str | None = None
    dependencies: tuple[str, ...] = ()
    isolation_worktree_required: bool = False
    open_prs: tuple[int, ...] = ()
    success_criteria: tuple[str, ...] = ()
    deadline: datetime | None = None
    priority: Literal["P0", "P1", "P2"] = "P1"
    notes: str | None = None


__all__ = ["ModelDispatchItem"]
