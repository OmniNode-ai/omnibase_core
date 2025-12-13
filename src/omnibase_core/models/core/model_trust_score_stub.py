"""
Trust score stub model for ONEX node metadata.
"""

from pydantic import BaseModel, Field


class ModelTrustScoreStub(BaseModel):
    """Trust score information for ONEX nodes."""

    runs: int = Field(default=..., description="Number of runs")
    failures: int = Field(default=..., description="Number of failures")
    trust_score: float | None = Field(
        default=None, description="Trust score (optional)"
    )
