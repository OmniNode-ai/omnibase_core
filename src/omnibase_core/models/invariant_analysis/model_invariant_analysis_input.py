# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Facts and configuration for one document (OMN-21565)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)

from .model_invariant_analysis_overlay import ModelInvariantAnalysisOverlay
from .model_invariant_registry import ModelInvariantRegistry

__all__ = ["ModelInvariantAnalysisInput"]


class ModelInvariantAnalysisInput(BaseModel):
    """Facts and configuration for one document."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    path: str = Field(description="Document path relative to scan root")
    text: str = Field(description="Document content")
    registry: ModelInvariantRegistry | None = Field(
        description="Registry, absent when invalid"
    )
    overlay: ModelInvariantAnalysisOverlay = Field(
        description="Repository configuration"
    )
    contract: ModelValidatorSubcontract = Field(description="Validation rule data")
    registry_error: str | None = Field(
        default=None, description="Registry construction failure"
    )
