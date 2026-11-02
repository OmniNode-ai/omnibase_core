# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input to the pure merge-side receipt check (OMN-21926)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.merge_receipt.model_merge_receipt_pr import (
    ModelMergeReceiptPr,
)


class ModelMergeReceiptCheckInput(BaseModel):
    """The pull requests to judge and the contract that defines the rules."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    source_name: str = Field(
        description="Name of the document; each rule's source pattern selects the "
        "documents it judges"
    )
    pull_requests: tuple[ModelMergeReceiptPr, ...] = Field(
        description="Open pull requests to examine"
    )
    contract: ModelValidatorSubcontract = Field(description="Merge-receipt rules")
