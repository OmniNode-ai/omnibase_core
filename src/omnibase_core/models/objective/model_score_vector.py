# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Score vector model — the only scoring primitive in OmniNode.

Single scalar rewards create distortion. Agents optimize for the scalar
at the expense of unmeasured properties. The ScoreVector is a structural
defense against Goodhart's Law.

Part of the objective functions and reward architecture (OMN-2537).
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = ["ModelScoreVector"]


class ModelScoreVector(BaseModel):
    """Multi-dimensional score vector for run evaluation.

    No single scalar reward is used anywhere in the system. This vector
    is the only scoring primitive. Lexicographic ordering (declared in
    ObjectiveSpec) ensures correctness cannot be traded against cost savings.

    All fields are normalized to [0.0, 1.0]:
    - 1.0 = perfect / fully passing
    - 0.0 = failed / worst case

    For inverted metrics (cost, latency), lower values in the real world
    map to higher scores here: 1.0 = minimum cost/latency, 0.0 = worst.

    Attributes:
        correctness: Gate-derived binary: 1.0 if all gates pass, 0.0 if any fail.
        safety: Security, PII, and blacklist gate composite score.
        cost: Inverted cost score: lower cost = higher score (1.0 = budget floor).
        latency: Inverted latency score: lower latency = higher score.
        maintainability: Complexity delta and test coverage composite score.
        human_time: Retries, interventions, and review cycle count (inverted).
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    correctness: float = Field(
        ge=0.0,
        le=1.0,
        description="Gate-derived correctness: 1.0 if all gates pass, 0.0 if any gate fails",
    )
    safety: float = Field(
        ge=0.0,
        le=1.0,
        description="Security, PII, and blacklist gate composite score",
    )
    cost: float = Field(
        ge=0.0,
        le=1.0,
        description="Inverted cost score: lower cost = higher score (1.0 = at budget floor)",
    )
    latency: float = Field(
        ge=0.0,
        le=1.0,
        description="Inverted latency score: lower latency = higher score",
    )
    maintainability: float = Field(
        ge=0.0,
        le=1.0,
        description="Cyclomatic complexity delta and test coverage composite score",
    )
    human_time: float = Field(
        ge=0.0,
        le=1.0,
        description="Inverted human intervention score: fewer retries/reviews = higher score",
    )

    @classmethod
    def zero(cls) -> "ModelScoreVector":
        """Return an all-zero score vector representing complete failure.

        Used when all hard gates fail — no shaped reward is computed.
        The zero vector is the canonical representation of a failed run.

        Returns:
            ModelScoreVector with all fields set to 0.0.
        """
        return cls(
            correctness=0.0,
            safety=0.0,
            cost=0.0,
            latency=0.0,
            maintainability=0.0,
            human_time=0.0,
        )

    @model_validator(mode="after")
    def validate_all_fields_in_range(self) -> "ModelScoreVector":
        """Validate all score fields are within [0.0, 1.0].

        Pydantic Field(ge=0.0, le=1.0) handles this, but explicit validation
        documents the contract clearly.

        Returns:
            Self after validation.
        """
        # Pydantic ge/le constraints handle this — this validator documents intent
        return self
