# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input to the pure plan-invariant check (OMN-21559)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)


class ModelPlanInvariantCheckInput(BaseModel):
    """The facts of one document and the contract that defines its rules."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    source_name: str = Field(
        description="Name of the plan document; each rule's "
        "source pattern selects the documents it judges"
    )
    text: str = Field(description="Markdown plan text declaring tasks and invariants")
    contract: ModelValidatorSubcontract = Field(
        description="Plan-invariant validation rules"
    )
    task_criteria_contract: ModelValidatorSubcontract = Field(
        description="Committed K12 task and criterion rules, including the falsifier predicate"
    )
