# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The document a consumer hands the merge-receipt validator (OMN-21926)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.merge_receipt.model_merge_receipt_pr import (
    ModelMergeReceiptPr,
)


class ModelMergeReceiptDocument(BaseModel):
    """The open pull requests to judge; the file form of the check input."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    pull_requests: tuple[ModelMergeReceiptPr, ...] = Field(
        description="Open pull requests with their heads, bodies, paths and receipts"
    )
