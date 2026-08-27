# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""On-disk locations declared in ``~/.onex/config.yaml``."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelCliUserConfigPaths(BaseModel):
    """On-disk locations ONEX reads and writes for this user."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        from_attributes=True,
        frozen=True,
    )

    state_dir: str = Field(
        default="~/.onex/state", description="Directory for durable local state"
    )
    log_dir: str = Field(default="~/.onex/logs", description="Directory for local logs")
    worktrees_root: str = Field(
        default="~/omni_worktrees", description="Root for per-ticket git worktrees"
    )


__all__ = ["ModelCliUserConfigPaths"]
