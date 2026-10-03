# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Output contract for the sprint-roll APPLY effect node (OMN-20397).

`writes` is empty on a dry run, and that is the assertion the dry-run case rests on:
the node is judged by what it sent, not by what it said it would send.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.sprint_roll.model_sprint_roll_write import (
    ModelSprintRollWrite,
)

__all__ = ["ModelSprintRollApplyResult"]


class ModelSprintRollApplyResult(BaseModel):
    """What the roll actually changed, and where its undo record lives."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    dry_run: bool
    writes: tuple[ModelSprintRollWrite, ...] = Field(default_factory=tuple)
    manifest_path: Path | None = None
    read_calls: int = 0
    write_calls: int = 0
