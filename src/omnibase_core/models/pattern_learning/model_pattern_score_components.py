"""Model for pattern scoring components.

Provides decomposed scoring components for pattern confidence calculations
in the ONEX intelligence system.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelPatternScoreComponents(BaseModel):
    """Decomposed scoring components for pattern confidence.

    This model holds the individual components that contribute to a pattern's
    overall confidence score. Each component is normalized to the range [0.0, 1.0].

    The rolled-up confidence score is computed as a weighted average:
        confidence = 0.4 * label_agreement + 0.3 * cluster_cohesion + 0.3 * frequency_factor

    Warning:
        NEVER make downstream decisions solely on the confidence field.
        The rolled-up confidence score is for convenience only.
        Always consider individual components for decision-making.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    label_agreement: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Agreement between labels in the cluster (0.0-1.0)",
    )

    cluster_cohesion: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Cohesion of the embedding cluster (0.0-1.0)",
    )

    frequency_factor: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalized frequency of pattern occurrence (0.0-1.0)",
    )

    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Derived confidence (0.4*agreement + 0.3*cohesion + 0.3*frequency). WARNING: Always inspect individual components for decision-making, not just this rolled-up value.",
    )


__all__ = ["ModelPatternScoreComponents"]
