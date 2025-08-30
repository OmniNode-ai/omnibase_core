#!/usr/bin/env python3
"""
RSD Factor Detail Model - ONEX Standards Compliant.

Strongly-typed model for individual priority factor details.
"""

from pydantic import BaseModel, Field


class ModelFactorDetail(BaseModel):
    """
    Model for details of individual priority factor in RSD algorithm.

    Contains detailed breakdown of how a single factor contributes
    to the overall priority score including raw values and explanations.
    """

    raw_value: float = Field(description="Raw calculated value before normalization")

    normalized_score: float = Field(
        description="Normalized score (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    weight: float = Field(description="Weight applied to this factor", ge=0.0, le=1.0)

    contribution: float = Field(
        description="Final contribution to overall score",
        ge=0.0,
    )

    explanation: str = Field(
        description="Human-readable explanation of the factor calculation",
    )

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        validate_assignment = True
