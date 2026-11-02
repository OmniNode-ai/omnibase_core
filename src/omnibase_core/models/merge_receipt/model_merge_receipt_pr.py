# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Facts about one open pull request for the merge-side receipt check (OMN-21926)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.merge_receipt.model_merge_receipt_record import (
    ModelMergeReceiptRecord,
)


class ModelMergeReceiptPr(BaseModel):
    """The head, body, changed paths and receipts of one pull request."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str = Field(description="Repository name")
    number: int = Field(description="Pull request number")
    head_sha: str = Field(description="Full sha of the pull request head")
    head_ref: str = Field(default="", description="Head branch name")
    body: str = Field(default="", description="Pull request body as typed")
    changed_paths: tuple[str, ...] = Field(
        default_factory=tuple, description="Paths the pull request changes"
    )
    receipts: tuple[ModelMergeReceiptRecord, ...] = Field(
        default_factory=tuple,
        description="Every receipt record found for the repository, any head",
    )
