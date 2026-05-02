# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input snapshot for deterministic OCC merge eligibility."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ModelOccEligibilityInput(BaseModel):
    """Immutable PR/OCC snapshot used for deterministic eligibility."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repo: str = Field(..., min_length=1)
    pr_number: int = Field(..., ge=1)
    pr_title: str = Field(default="")
    pr_body: str = Field(default="")
    pr_branch: str = Field(default="")
    pr_commit_shas: tuple[str, ...] = Field(default_factory=tuple)
    pr_commit_texts: tuple[str, ...] = Field(default_factory=tuple)
    occ_commit_sha: str = Field(..., pattern=r"^[0-9a-f]{40}$")
    contracts_dir: Path
    receipts_dir: Path


__all__ = ["ModelOccEligibilityInput"]
