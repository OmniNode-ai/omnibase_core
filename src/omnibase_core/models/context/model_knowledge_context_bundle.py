# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelKnowledgeContextBundle — injectable knowledge context bundle (OMN-11928)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.context.model_adr_summary import ModelADRSummary
from omnibase_core.models.context.model_antipattern_summary import (
    ModelAntipatternSummary,
)
from omnibase_core.models.context.model_graph_snapshot import ModelGraphSnapshot
from omnibase_core.models.context.model_learning_match import ModelLearningMatch

__all__ = ["ModelKnowledgeContextBundle"]

BundleLevel = Literal["L0", "L1", "L2", "L3"]

_L2_MARKDOWN_CAP = 4000


class ModelKnowledgeContextBundle(BaseModel):
    """Injectable knowledge context bundle for agent sessions.

    Bundle levels:
        L0 — antipatterns only
        L1 — + ADRs
        L2 — + architecture context (markdown output capped at 4000 chars)
        L3 — + dependency graph + prior learnings
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    repo: str = Field(description="Repository this bundle was built for")
    ticket_id: str | None = Field(
        default=None, description="Optional Linear ticket that scoped this bundle"
    )
    architecture_context: str = Field(
        description="Free-text architecture summary from Repowise get_answer"
    )
    relevant_adrs: tuple[ModelADRSummary, ...] = Field(
        default=(), description="ADRs applicable to this repo/ticket"
    )
    applicable_antipatterns: tuple[ModelAntipatternSummary, ...] = Field(
        default=(), description="Antipatterns applicable to this repo/ticket"
    )
    prior_learnings: tuple[ModelLearningMatch, ...] = Field(
        default=(), description="Prior learnings matched by semantic similarity"
    )
    dependency_graph: ModelGraphSnapshot | None = Field(
        default=None, description="Dependency graph snapshot (L3 only)"
    )
    bundle_level: BundleLevel = Field(description="Completeness tier of this bundle")
    degraded: bool = Field(
        default=False, description="True when one or more backends failed"
    )
    degraded_backends: tuple[str, ...] = Field(
        default=(), description="Names of backends that failed during assembly"
    )
    missing_sections: tuple[str, ...] = Field(
        default=(), description="Section names omitted due to backend failure"
    )
    bundle_hash: str = Field(
        description="Deterministic hash over all content fields for cache keying"
    )
    generated_at: datetime = Field(
        description="UTC timestamp when bundle was assembled"
    )

    @field_validator("bundle_level", mode="before")
    @classmethod
    def _validate_bundle_level(cls, v: str) -> str:
        if v not in ("L0", "L1", "L2", "L3"):
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(f"bundle_level must be one of L0/L1/L2/L3, got {v!r}")
        return v

    def to_markdown(self) -> str:
        """Render bundle as injectable context markdown.

        L2 output is hard-capped at 4000 characters.
        """
        parts: list[str] = []
        parts.append(f"# Knowledge Context — {self.repo}")
        if self.ticket_id:
            parts.append(f"**Ticket:** {self.ticket_id}")
        parts.append(f"**Bundle level:** {self.bundle_level}")
        if self.degraded:
            backends = (
                ", ".join(self.degraded_backends)
                if self.degraded_backends
                else "unknown"
            )
            parts.append(f"> **DEGRADED** — backends unavailable: {backends}")
            if self.missing_sections:
                parts.append(f"> Missing sections: {', '.join(self.missing_sections)}")

        # L0+: antipatterns
        if self.applicable_antipatterns:
            parts.append("\n## Antipatterns")
            for ap in self.applicable_antipatterns:
                parts.append(
                    f"- **{ap.name}** [{ap.severity}] ({ap.category}): {ap.description}"
                )

        # L1+: ADRs
        if self.bundle_level in ("L1", "L2", "L3") and self.relevant_adrs:
            parts.append("\n## ADR Decisions")
            for adr in self.relevant_adrs:
                parts.append(
                    f"- **{adr.adr_id}** ({adr.status}): {adr.title} — {adr.decision}"
                )

        # L2+: architecture context
        if self.bundle_level in ("L2", "L3") and self.architecture_context:
            parts.append("\n## Architecture Context")
            parts.append(self.architecture_context)

        # L3: prior learnings + graph
        if self.bundle_level == "L3":
            if self.prior_learnings:
                parts.append("\n## Prior Learnings")
                for lm in self.prior_learnings:
                    parts.append(f"- [{lm.relevance_score:.2f}] {lm.summary}")
            if self.dependency_graph is not None:
                parts.append("\n## Dependency Graph")
                parts.append(
                    f"Nodes: {self.dependency_graph.node_count}, "
                    f"Edges: {self.dependency_graph.edge_count}"
                )
                parts.append(self.dependency_graph.summary)

        result = "\n".join(parts)

        if self.bundle_level == "L2" and len(result) > _L2_MARKDOWN_CAP:
            result = result[:_L2_MARKDOWN_CAP]

        return result
