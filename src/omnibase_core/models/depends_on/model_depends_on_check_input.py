# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input to the pure depends-on check (OMN-24537)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.depends_on.model_depends_on_facts import ModelDependsOnFacts


class ModelDependsOnCheckInput(BaseModel):
    """A judged document, the world the facts describe and the rules.

    ``facts`` is None when no facts were supplied; no fact source never reads
    as a fact source that holds everything.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    source_name: str = Field(description="Name of the judged document")
    text: str = Field(description="Document text")
    facts: ModelDependsOnFacts | None = Field(
        description="What exists in the world by kind, or None when unsupplied"
    )
    contract: ModelValidatorSubcontract = Field(
        description="Depends-on validation rules"
    )
