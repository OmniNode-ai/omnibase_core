# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelDirectModelCallCheckRequest: what the EFFECT node gathers (OMN-20295)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelDirectModelCallCheckRequest"]


class ModelDirectModelCallCheckRequest(BaseModel):
    """Which repository to read, and which baseline and base ref to read with it."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str = Field(description="Repository name in policy.yaml")
    repo_root: str = Field(default=".", description="Repository root directory")
    baseline_path: str | None = Field(
        default=None, description="Repository-relative path of the committed baseline"
    )
    base_ref: str | None = Field(
        default=None, description="Git ref whose baseline this one may only shrink from"
    )
