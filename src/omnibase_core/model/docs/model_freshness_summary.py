"""
Freshness Summary Model

Summary statistics for freshness analysis.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelFreshnessSummary(BaseModel):
    """Summary statistics for freshness analysis."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    total_documents: int = Field(ge=0, description="Total number of documents analyzed")
    fresh_count: int = Field(ge=0, description="Number of fresh documents")
    stale_count: int = Field(ge=0, description="Number of stale documents")
    critical_count: int = Field(
        ge=0,
        description="Number of critically stale documents",
    )
    avg_freshness_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Average freshness score across all documents",
    )
    oldest_document: str | None = Field(
        default=None,
        description="Path to the oldest document",
    )
    newest_document: str | None = Field(
        default=None,
        description="Path to the newest document",
    )
