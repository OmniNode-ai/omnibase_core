# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Provenance Decision Score Model.

Provides ModelProvenanceDecisionScore, a per-candidate scoring breakdown for a
single decision in the Decision Provenance system.

The public alias ``DecisionScore`` is exported for use by consumers of the
Decision Provenance API via ``omnibase_core.contracts``.

See Also:
    model_provenance_decision_record.py: The parent ModelProvenanceDecisionRecord model.
    OMN-2350: Decision Provenance epic.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelProvenanceDecisionScore(BaseModel):
    """Per-candidate scoring breakdown for a single decision.

    Captures how a single candidate was evaluated during a decision, including
    the aggregate score and a fine-grained breakdown by scoring dimension.

    This model is frozen (immutable) because scoring results are facts about
    what happened during a decision — they must not be altered after emission.

    Attributes:
        candidate: Identifier of the candidate being scored (e.g., model name,
            workflow ID, tool name).
        score: Aggregate score for this candidate. The scoring range is not
            strictly enforced to allow flexibility in different decision contexts.
        breakdown: Per-dimension scores keyed by dimension name (e.g.,
            ``{"accuracy": 0.95, "latency": 0.89}``). Values are floats and
            may use any range meaningful to the scoring context.

    Example::

        score = ModelProvenanceDecisionScore(
            candidate="gpt-4o",
            score=0.91,
            breakdown={"quality": 0.94, "cost": 0.88},
        )
    """

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
        from_attributes=True,
    )

    candidate: str = Field(
        ...,
        description="Identifier of the candidate being scored",
    )
    score: float = Field(
        ...,
        description="Aggregate score for this candidate",
    )
    breakdown: dict[str, float] = Field(
        ...,
        description="Per-dimension scores keyed by dimension name",
    )


# Public alias for Decision Provenance API consumers
DecisionScore = ModelProvenanceDecisionScore

__all__ = ["ModelProvenanceDecisionScore", "DecisionScore"]
