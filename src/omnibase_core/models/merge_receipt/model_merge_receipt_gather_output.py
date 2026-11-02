# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Facts gathered for the merge-side receipt check (OMN-21926)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.merge_receipt.model_merge_receipt_pr import (
    ModelMergeReceiptPr,
)


class ModelMergeReceiptGatherOutput(BaseModel):
    """Open pull requests as facts, the ones left out, and the slot proof seconds."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    pull_requests: tuple[ModelMergeReceiptPr, ...] = Field(
        description="Open pull requests whose changed paths could be read"
    )
    unreadable: tuple[str, ...] = Field(
        description="repo#number of open pull requests whose changed paths could not be read"
    )
    slot_seconds: tuple[float, ...] = Field(
        description="Seconds from each pre-PR slot HOLD to its RELEASE"
    )
