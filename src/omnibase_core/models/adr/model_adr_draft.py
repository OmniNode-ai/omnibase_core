# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ADR draft model produced by the extraction pipeline (OMN-10691)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.adr.model_adr_extraction_metadata import (
    ModelADRExtractionMetadata,
)


class ModelADRDraft(BaseModel):
    """A proposed ADR in Proposed state, ready for human review."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    status: Literal["Proposed"] = Field(
        default="Proposed", description="Always 'Proposed'"
    )
    date: datetime = Field(description="Date the draft was generated")
    title: str = Field(description="ADR title")
    context: str = Field(description="Context and problem statement")
    decision: str = Field(description="The decision that was made")
    consequences: str = Field(description="Consequences of the decision")
    alternatives_considered: list[str] = Field(
        default_factory=list, description="Alternatives that were evaluated"
    )
    supersedes: list[str] = Field(
        default_factory=list, description="IDs of superseded ADRs"
    )
    source_evidence: list[str] = Field(
        default_factory=list, description="Segment IDs providing evidence"
    )
    extraction_metadata: ModelADRExtractionMetadata = Field(
        description="Provenance metadata from the extraction pipeline"
    )


__all__ = ["ModelADRDraft"]
