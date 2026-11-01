# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input to the pure pin needs/provides check (OMN-21879)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.pin_needs_provides.model_pin_needs_declaration import (
    ModelPinNeedsDeclaration,
)
from omnibase_core.models.pin_needs_provides.model_pin_provides_declaration import (
    ModelPinProvidesDeclaration,
)


class ModelPinNeedsProvidesCheckInput(BaseModel):
    """A caller file or a diff of caller files, both declarations and the rules."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    source_name: str = Field(
        description="Name of the document; a diff is selected by the contract's diff pattern"
    )
    text: str = Field(description="Caller file text, or a unified diff of caller files")
    needs: ModelPinNeedsDeclaration = Field(
        description="What each verifier version needs"
    )
    provides: ModelPinProvidesDeclaration = Field(
        description="What each caller provides"
    )
    contract: ModelValidatorSubcontract = Field(
        description="Pin needs/provides validation rules"
    )
