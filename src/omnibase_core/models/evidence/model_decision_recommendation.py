"""Decision recommendation model for corpus replay evidence reports.

This model represents actionable recommendations generated from corpus replay
evidence analysis (OMN-1199).

Thread Safety:
    ModelDecisionRecommendation is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelDecisionRecommendation(BaseModel):
    """Actionable recommendation from corpus replay evidence analysis.

    This model encapsulates the decision recommendation output from analyzing
    corpus replay evidence, including the action to take, confidence level,
    and supporting rationale.

    Attributes:
        action: Recommended action (approve, review, reject).
        confidence: Confidence in the recommendation (0.0 - 1.0).
        blockers: List of blocking issues that must be resolved.
        warnings: List of warning issues that should be reviewed.
        next_steps: Ordered list of recommended next steps.
        rationale: Human-readable explanation for the recommendation.
        generated_at: When this recommendation was generated.

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it
        thread-safe for concurrent read access.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    action: Literal["approve", "review", "reject"] = Field(
        description="Recommended action based on evidence analysis"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the recommendation (0.0 - 1.0)",
    )
    blockers: list[str] = Field(
        default_factory=list,
        description="List of blocking issues that must be resolved",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="List of warning issues that should be reviewed",
    )
    next_steps: list[str] = Field(
        default_factory=list,
        description="Ordered list of recommended next steps",
    )
    rationale: str = Field(
        default="",
        description="Human-readable explanation for the recommendation",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description=(
            "When this recommendation was generated. May differ from the report's "
            "generated_at if the recommendation is reused across multiple formats."
        ),
    )


__all__ = ["ModelDecisionRecommendation"]
