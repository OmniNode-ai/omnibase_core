# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Deterministic result of the merge-side receipt check (OMN-21926)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.merge_receipt.model_merge_receipt_verdict import (
    ModelMergeReceiptVerdict,
)


class ModelMergeReceiptCheckResult(BaseModel):
    """Issues, per-PR verdicts and counts. The exit code is always zero: report-only."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    issues: tuple[ModelValidationIssue, ...] = Field(
        description="Enabled rule violations, one per cause per pull request"
    )
    verdicts: tuple[ModelMergeReceiptVerdict, ...] = Field(
        description="One verdict per runtime-affecting pull request"
    )
    examined: int = Field(description="Runtime-affecting pull requests examined")
    would_refuse: int = Field(description="Of those, how many would be refused")
    skipped: int = Field(
        description="Pull requests examined but not runtime-affecting, so not counted"
    )
    exit_code: int = Field(
        description="Always zero; the check never fails a pull request"
    )
