# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Typed input for the pull-request workflow ratchet COMPUTE validator."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelPullRequestWorkflowRatchetCheckInput(BaseModel):
    """Repository, registry and waiver-expiry horizon the ratchet is judged at."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo_root: str = Field(min_length=1, description="Repository root.")
    registry_path: str = Field(
        min_length=1, description="Path to the budget registry YAML."
    )
    horizon_days: int = Field(
        default=0,
        ge=0,
        description="Days before expiry at which a waiver already fails.",
    )
