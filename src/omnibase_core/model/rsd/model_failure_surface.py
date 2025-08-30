#!/usr/bin/env python3
"""
RSD Failure Surface Model - ONEX Standards Compliant.

Strongly-typed model for failure surface calculations in RSD algorithm.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelFailureSurface(BaseModel):
    """
    Model for calculating failure impact surface for ticket prioritization.

    Used in RSD algorithm to assess the potential impact of ticket failures
    on validators, replay logs, and test suites to inform prioritization decisions.
    """

    ticket_id: str = Field(description="Ticket ID for failure surface calculation")

    validator_dependencies: list[str] = Field(
        description="List of validator components that depend on this ticket",
        default_factory=list,
    )

    replay_log_references: list[str] = Field(
        description="List of replay logs that reference this ticket",
        default_factory=list,
    )

    test_suite_impacts: list[str] = Field(
        description="List of test suites impacted by this ticket",
        default_factory=list,
    )

    calculated_score: float = Field(
        description="Calculated failure surface score (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    last_calculated: datetime = Field(
        description="When the score was last calculated",
        default_factory=datetime.now,
    )

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        validate_assignment = True
        json_encoders = {datetime: lambda v: v.isoformat()}
