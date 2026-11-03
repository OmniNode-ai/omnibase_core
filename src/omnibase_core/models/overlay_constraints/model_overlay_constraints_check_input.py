# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input to the pure overlay-constraints check (OMN-22185)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.overlay_constraints.model_overlay_constraints_declaration import (
    ModelOverlayConstraintsDeclaration,
)


class ModelOverlayConstraintsCheckInput(BaseModel):
    """A contract's declaration, the overlay's values and the validation rules."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    source_name: str = Field(description="Name of the document the declaration is from")
    declaration: ModelOverlayConstraintsDeclaration = Field(
        description="The contract's overlay_constraints block"
    )
    values: dict[str, object] = Field(
        description="Overlay key to value; every key a relation names must be a number"
    )
    contract: ModelValidatorSubcontract = Field(
        description="Overlay-constraints validation rules"
    )
