"""
Trust score stub model for ONEX node metadata.
"""

from pydantic import BaseModel, Field


class ModelTrustScoreStub(BaseModel):
    """Trust score information for ONEX nodes."""

    runs: int = Field(..., description="Number of runs")
    failures: int = Field(..., description="Number of failures")
    trust_score: float | None = Field(None, description="Trust score (optional)")
