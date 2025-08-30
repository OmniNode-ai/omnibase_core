#!/usr/bin/env python3
"""
RSD Metrics Model - ONEX Standards Compliant.

Strongly-typed model for RSD algorithm performance and quality metrics.
"""

from pydantic import BaseModel, Field


class ModelRSDMetrics(BaseModel):
    """
    Model for RSD algorithm performance and quality metrics.

    Tracks performance characteristics and quality indicators
    for the RSD prioritization algorithm execution.
    """

    total_tickets_processed: int = Field(
        description="Total number of tickets processed",
        ge=0,
    )

    average_processing_time_ms: float = Field(
        description="Average processing time per ticket in milliseconds",
        ge=0.0,
    )

    cache_hit_rate: float = Field(
        description="Cache hit rate percentage (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    algorithm_version: str = Field(description="Version of RSD algorithm used")

    quality_score: float = Field(
        description="Algorithm quality score (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        validate_assignment = True
