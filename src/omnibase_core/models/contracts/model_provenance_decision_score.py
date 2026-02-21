# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Decision Provenance Score Model.

Provides the ModelProvenanceDecisionScore class, which represents the
per-candidate scoring breakdown for a provenance decision record.

This model is part of the Decision Provenance system (OMN-2350), designed
to support auditability and reproducibility of agent decisions.

Design Decisions:
    - frozen=True: Immutable after creation — provenance artifacts must not be mutated.
    - No implicit defaults: All fields must be explicitly provided by callers.
    - Separate from DecisionRecord: Allows per-candidate breakdown without flattening.
    - breakdown as MappingProxyType: The breakdown field is stored as a read-only
      types.MappingProxyType. The field_validator validate_breakdown_keys returns
      types.MappingProxyType(validated_dict) after key validation; Pydantic v2
      stores the validator return value directly, so no frozen bypass is needed.
      In-place mutation of breakdown raises TypeError.

See Also:
    model_provenance_decision_record.py: Main provenance record model.
    OMN-2350: Decision Provenance epic.
"""

from __future__ import annotations

import types
from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelProvenanceDecisionScore(BaseModel):
    """Per-candidate scoring breakdown for a decision provenance record.

    Captures the score and detailed breakdown for a single candidate
    evaluated during a decision. Used within ModelProvenanceDecisionRecord
    to provide full auditability of how each candidate was scored.

    Attributes:
        candidate: Identifier for the candidate being scored.
        score: Aggregate score for this candidate.
        breakdown: Per-criterion score contributions (not necessarily summing to
            score — no summation invariant is enforced). Stored as a
            read-only MappingProxyType after construction; in-place mutation
            raises TypeError.

    Example:
        >>> score = ModelProvenanceDecisionScore(
        ...     candidate="claude-3-opus",
        ...     score=0.87,
        ...     breakdown={"quality": 0.45, "speed": 0.25, "cost": 0.17},
        ... )
        >>> score.candidate
        'claude-3-opus'
        >>> score.score
        0.87
    """

    model_config = ConfigDict(
        frozen=True,
        # extra="ignore" intentional: contract/external model — forward-compatible with event bus
        extra="ignore",
        from_attributes=True,
    )

    candidate: str = Field(
        ...,
        min_length=1,
        description="Identifier for the candidate being scored",
    )

    # Design decision: score range is intentionally unbounded.
    # Negative scores are valid (e.g., penalty-based scoring systems where
    # a candidate receives a negative weight for constraint violations).
    # Values >1.0 are valid for raw un-normalised metrics before calibration.
    # Downstream consumers that require a normalised [0.0, 1.0] range must
    # clamp or validate the value themselves — this model does not impose that
    # constraint because the provenance system must faithfully record whatever
    # score was produced, not silently truncate it.
    score: float = Field(
        ...,
        description=(
            "Aggregate score for this candidate. Range is intentionally unbounded: "
            "negative values are valid for penalty-based systems; values >1.0 are "
            "valid for raw un-normalised metrics. See module docstring for rationale."
        ),
    )

    breakdown: Mapping[str, float] = Field(
        ...,
        description=(
            "Per-criterion score contributions. Stored as a read-only "
            "MappingProxyType after construction; in-place mutation raises TypeError. "
            "Keys must be non-empty strings. Values are unbounded floats."
        ),
    )

    @field_validator("breakdown")
    @classmethod
    def validate_breakdown_keys(cls, v: dict[str, float]) -> Mapping[str, float]:
        for key in v:
            if not key:
                raise ValueError(
                    "breakdown keys must be non-empty strings; "
                    "found an empty string key"
                )
        return types.MappingProxyType(v)


# Public alias for API surface
DecisionScore = ModelProvenanceDecisionScore

__all__ = ["DecisionScore", "ModelProvenanceDecisionScore"]
