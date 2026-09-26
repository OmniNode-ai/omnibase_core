# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelADRSummary — minimal ADR projection for context injection (OMN-11928)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.context.model_context_provenance import ModelContextProvenance
from omnibase_core.types.type_semantic_id import AdrId

__all__ = ["ModelADRSummary"]


class ModelADRSummary(BaseModel):
    """Minimal ADR projection for context injection."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    adr_id: AdrId = Field(description="Stable human-readable ADR identifier")
    title: str = Field(description="ADR title")
    decision: str = Field(description="One-sentence decision summary")
    status: Literal["accepted", "deprecated", "superseded", "proposed"] = Field(
        description="ADR lifecycle status"
    )
    provenance: ModelContextProvenance = Field(description="Source provenance")
