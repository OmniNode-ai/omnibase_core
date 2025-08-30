"""
Quality metrics model for adaptive chunking results.

Provides comprehensive quality assessment for LangExtract-enhanced chunking.
"""

from pydantic import BaseModel, Field


class ModelModelChunkingQualityMetrics(BaseModel):
    """Quality metrics for adaptive chunking results."""

    total_chunks: int = Field(..., description="Total number of chunks created")
    avg_chunk_size: float = Field(..., description="Average chunk size in characters")
    chunk_size_variance: float = Field(
        default=0.0, description="Variance in chunk sizes"
    )
    semantic_coherence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Average semantic coherence across chunks",
    )
    entity_preservation_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Score for entity preservation quality"
    )
    pattern_coverage_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Coverage of LangExtract patterns"
    )
    boundary_accuracy_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Accuracy of semantic boundary detection",
    )
    intelligence_utilization_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="How well LangExtract intelligence was utilized",
    )
    processing_time_ms: float = Field(
        ..., description="Processing time in milliseconds"
    )
    adaptive_efficiency_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall efficiency of adaptive chunking",
    )
