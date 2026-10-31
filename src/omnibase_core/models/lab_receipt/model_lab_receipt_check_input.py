# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input to the pure lab-receipt check (OMN-21823)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.lab_receipt.model_lab_receipt_document import (
    ModelLabReceiptDocument,
)


class ModelLabReceiptCheckInput(BaseModel):
    """The document to judge and the contract that defines its rules."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    source_name: str = Field(
        description="Name of the document; each rule's source pattern selects the "
        "documents it judges"
    )
    document: ModelLabReceiptDocument = Field(description="Phase and facts")
    contract: ModelValidatorSubcontract = Field(description="Lab-receipt rules")
