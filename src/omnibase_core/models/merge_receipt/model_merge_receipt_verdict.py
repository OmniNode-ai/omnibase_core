# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The would-refuse verdict for one examined pull request (OMN-21926)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelMergeReceiptVerdict(BaseModel):
    """Whether one runtime-affecting pull request would be refused, and why."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str = Field(description="Repository name")
    number: int = Field(description="Pull request number")
    head_sha: str = Field(description="Head the verdict is for")
    would_refuse: bool = Field(
        description="True when no counted receipt names the head"
    )
    causes: tuple[str, ...] = Field(
        description="Rule ids of every cause that applies, empty when it would not refuse"
    )
