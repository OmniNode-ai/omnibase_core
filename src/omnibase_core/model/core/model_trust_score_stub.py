"""
Trust score stub model for ONEX node metadata.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelTrustScoreStub(BaseModel):
    """Trust score information for ONEX nodes."""

    runs: int = Field(..., description="Number of runs")
    failures: int = Field(..., description="Number of failures")
    trust_score: Optional[float] = Field(None, description="Trust score (optional)")
