# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelTriageFinding — single actionable triage finding (OMN-9322)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_triage_blast_radius import EnumTriageBlastRadius
from omnibase_core.enums.enum_triage_freshness import EnumTriageFreshness
from omnibase_core.enums.enum_triage_severity import EnumTriageSeverity


class ModelTriageFinding(BaseModel):
    """A single actionable triage finding.

    Findings are read-only claims — nothing in this model mutates system state.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_probe: str = Field(description="Probe name that produced this finding")
    severity: EnumTriageSeverity
    freshness: EnumTriageFreshness
    blast_radius: EnumTriageBlastRadius
    message: str = Field(description="Human-readable one-line summary")
    evidence_paths: list[str] = Field(
        default_factory=list,
        description="Absolute paths (or URLs) where evidence can be inspected",
    )
    related_tickets: list[str] = Field(
        default_factory=list,
        description="Existing Linear ticket IDs referenced by this finding",
    )

    @property
    def rank_score(self) -> int:
        """Composite rank: severity.weight * blast_radius.weight + freshness.weight."""
        return self.severity.weight * self.blast_radius.weight + self.freshness.weight
