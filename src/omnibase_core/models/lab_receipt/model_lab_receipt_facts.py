# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed facts for the lab-receipt checker (OMN-21823)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.lab_receipt.model_lab_receipt_changed_file import (
    ModelLabReceiptChangedFile,
)
from omnibase_core.models.lab_receipt.model_lab_receipt_criterion import (
    ModelLabReceiptCriterion,
)
from omnibase_core.models.lab_receipt.model_lab_receipt_lab_read import (
    ModelLabReceiptLabRead,
)
from omnibase_core.models.lab_receipt.model_lab_receipt_record import (
    ModelLabReceiptRecord,
)


class ModelLabReceiptFacts(BaseModel):
    """Everything the checker reads about one pull request.

    ``lab_reads`` is None when no lab was read; a verify run with None is refused.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repository: str = Field(description="Identity of the repository the PR changes")
    head_sha: str = Field(description="Full sha of the PR head")
    changed_files: tuple[ModelLabReceiptChangedFile, ...] = Field(
        default_factory=tuple, description="Paths the PR changes against its base"
    )
    criteria: tuple[ModelLabReceiptCriterion, ...] = Field(
        default_factory=tuple, description="Criteria of the tickets the PR cites"
    )
    receipts: tuple[ModelLabReceiptRecord, ...] = Field(
        default_factory=tuple, description="Receipt records found for the PR"
    )
    lab_reads: tuple[ModelLabReceiptLabRead, ...] | None = Field(
        default=None, description="Lab host install reads, supplied in the verify phase"
    )
