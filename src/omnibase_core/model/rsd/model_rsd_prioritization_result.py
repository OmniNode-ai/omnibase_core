#!/usr/bin/env python3
"""
RSD Prioritization Result Model - ONEX Standards Compliant.

Strongly-typed model for RSD algorithm prioritization results.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelRSDPrioritizationResult(BaseModel):
    """
    Model for complete RSD prioritization result with scores and metadata.

    Contains the complete output of RSD 5-factor algorithm calculation
    for a single ticket including all factor scores and processing metadata.
    """

    ticket_id: str = Field(description="Unique ticket identifier")

    overall_score: float = Field(
        description="Final weighted priority score (0.0-100.0)",
        ge=0.0,
        le=100.0,
    )

    dependency_distance_score: float = Field(
        description="Dependency distance factor score (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    failure_surface_score: float = Field(
        description="Failure surface factor score (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    time_decay_score: float = Field(
        description="Time decay factor score (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    agent_utility_score: float = Field(
        description="Agent utility factor score (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    user_weighting_score: float = Field(
        description="User weighting factor score (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    calculated_at: datetime = Field(
        description="When the priority was calculated",
        default_factory=datetime.now,
    )

    processing_time_ms: float = Field(
        description="Time taken to calculate priority in milliseconds",
        gt=0.0,
    )

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        validate_assignment = True
        json_encoders = {datetime: lambda v: v.isoformat()}
