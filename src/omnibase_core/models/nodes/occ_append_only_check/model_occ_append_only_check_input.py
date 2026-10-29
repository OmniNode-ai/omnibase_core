# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Parsed contracts and git change lists consumed by the OCC append-only validator."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelOccAppendOnlyCheckInput"]


class ModelOccAppendOnlyCheckInput(BaseModel):
    """Everything the append-only check needs, already read from git and disk.

    ``receipt_diff`` holds ``(git_status, path)`` pairs. ``branch_history`` holds
    one ``(commit, git_status, path, prior_text, new_text)`` tuple per receipt
    path each branch commit touched (OMN-19050).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    base_contract: dict[str, object] | None = Field(
        default=None,
        description="Contract at the merge base, or None when it is net-new.",
    )
    head_contract: dict[str, object] | None = Field(
        default=None, description="Contract at the PR head."
    )
    receipt_diff: tuple[tuple[str, str], ...] = Field(default=())
    branch_history: tuple[tuple[str, str, str, str | None, str | None], ...] = Field(
        default=()
    )
