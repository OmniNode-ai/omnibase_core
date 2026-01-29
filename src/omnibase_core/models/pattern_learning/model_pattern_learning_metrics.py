"""Model for pattern learning metrics."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelPatternLearningMetrics(BaseModel):
    """Metrics for detecting silent degradation in pattern learning.

    These metrics should be monitored over time to detect:
    - Declining pattern quality (mean_confidence dropping)
    - Label drift (mean_label_agreement declining)
    - Clustering issues (mean_cluster_cohesion declining)
    - Processing anomalies (unusually high discard/merge rates)
    """

    input_count: int = Field(ge=0, description="Total input samples processed")
    cluster_count: int = Field(ge=0, description="Number of clusters formed")
    candidate_count: int = Field(ge=0, description="Patterns promoted to candidate")
    learned_count: int = Field(ge=0, description="Patterns fully learned")
    discarded_count: int = Field(ge=0, description="Patterns discarded (low quality)")
    merged_count: int = Field(ge=0, description="Patterns merged (duplicates)")
    mean_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Average confidence across learned patterns",
    )
    mean_label_agreement: float = Field(
        ge=0.0,
        le=1.0,
        description="Average label agreement across clusters",
    )
    mean_cluster_cohesion: float = Field(
        ge=0.0,
        le=1.0,
        description="Average cluster cohesion score",
    )
    processing_time_ms: float = Field(
        ge=0.0,
        description="Total processing time in milliseconds",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )


__all__ = ["ModelPatternLearningMetrics"]
