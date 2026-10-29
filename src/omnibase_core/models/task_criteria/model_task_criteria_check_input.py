# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input to the pure task-criteria check (OMN-21535)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)


class ModelTaskCriteriaCheckInput(BaseModel):
    """The facts of one document and the contract that defines its rules."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    source_name: str = Field(
        description="Name of the document (a path or a ticket payload name); each rule's "
        "source pattern selects the documents it judges"
    )
    text: str = Field(
        description="Plan, ticket description, brief, job.json, rules text or contract criteria"
    )
    repository_lifecycle: dict[str, str] = Field(
        default_factory=dict,
        description="Lifecycle state by repository name, the data of the lifecycle rule",
    )
    contract: ModelValidatorSubcontract = Field(
        description="Task-criteria validation rules"
    )
