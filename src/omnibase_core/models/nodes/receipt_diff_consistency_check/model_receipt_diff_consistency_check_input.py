# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Typed input for the receipt diff-consistency COMPUTE validator."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelReceiptDiffConsistencyCheckInput(BaseModel):
    """Changed receipt files plus the PR's parsed ``git diff --name-status``."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    receipt_paths: list[str] = Field(
        default_factory=list,
        description="Receipt YAML files changed on the PR (the receipts to check).",
    )
    name_status: list[tuple[str, str]] = Field(
        default_factory=list,
        description="(status, path) pairs parsed from the PR name-status diff.",
    )
