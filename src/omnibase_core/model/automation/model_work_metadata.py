"""
Metadata model for work classification assessments.

Provides strongly typed metadata structure for work assessments.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelWorkMetadata(BaseModel):
    """Metadata for work classification assessments."""

    assessment_version: str = Field(
        default="1.0.0", description="Version of assessment algorithm"
    )
    confidence_factors: dict[str, float] = Field(
        default_factory=dict, description="Factors contributing to confidence score"
    )
    similar_work_count: int = Field(
        default=0, description="Number of similar work items found"
    )
    historical_success_rate: float = Field(
        default=0.0, description="Success rate of similar work"
    )
    recommended_agent_tier: str = Field(
        default="standard", description="Recommended agent performance tier"
    )
    safety_checks_passed: int = Field(
        default=0, description="Number of safety checks passed"
    )
    safety_checks_failed: int = Field(
        default=0, description="Number of safety checks failed"
    )
    notes: Optional[str] = Field(None, description="Additional assessment notes")
