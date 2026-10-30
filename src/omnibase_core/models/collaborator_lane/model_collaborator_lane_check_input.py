# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input to the pure collaborator-lane check (OMN-21599)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)


class ModelCollaboratorLaneCheckInput(BaseModel):
    """One lane brief, proof rule text or placement declaration and the rules that judge it."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    source_name: str = Field(
        description="Name of the document (a path); each rule's source pattern selects the "
        "documents it judges"
    )
    text: str = Field(
        description="Lane brief, job.json, proof rule text, runbook or placement YAML"
    )
    contract: ModelValidatorSubcontract = Field(
        description="Collaborator-lane validation rules"
    )
