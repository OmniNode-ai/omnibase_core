"""
Statistics model for work classification batches.

Provides strongly typed statistics structure for batches.
"""

from pydantic import BaseModel, Field


class ModelBatchStatistics(BaseModel):
    """Statistics for work classification batches."""

    overnight_safe_count: int = Field(
        default=0,
        description="Count of overnight safe items",
    )
    day_shift_count: int = Field(default=0, description="Count of day shift items")
    human_only_count: int = Field(default=0, description="Count of human-only items")
    deferred_count: int = Field(default=0, description="Count of deferred items")
    average_risk_score: float = Field(
        default=0.0,
        description="Average risk score across batch",
    )
    average_confidence: float = Field(
        default=0.0,
        description="Average confidence across batch",
    )
    processing_time_seconds: float = Field(
        default=0.0,
        description="Time taken to process batch",
    )
    classification_errors: int = Field(
        default=0,
        description="Number of classification errors",
    )
