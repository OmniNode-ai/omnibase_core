# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input to the pure diagram-drift check (OMN-21510)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)


class ModelDiagramDriftCheckInput(BaseModel):
    """One document's text and the contract that defines the check's rules."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    source_name: str = Field(
        description="Name of the document; each rule's source pattern selects the documents it judges"
    )
    text: str = Field(
        description="Document text; the markers inside it name the contracts and views"
    )
    contract: ModelValidatorSubcontract = Field(
        description="Diagram-drift validation rules"
    )
