#!/usr/bin/env python3
"""
RSD Priority Factor Breakdown Model - ONEX Standards Compliant.

Strongly-typed model for detailed priority factor breakdown.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.rsd.model_factor_detail import ModelFactorDetail


class ModelPriorityFactorBreakdown(BaseModel):
    """
    Model for detailed breakdown of RSD priority calculation factors.

    Provides complete transparency into how each of the 5 RSD algorithm
    factors contributed to the final priority score for a ticket.
    """

    ticket_id: str = Field(description="Ticket ID this breakdown applies to")

    dependency_distance: ModelFactorDetail = Field(
        description="Dependency distance factor details",
    )

    failure_surface: ModelFactorDetail = Field(
        description="Failure surface factor details",
    )

    time_decay: ModelFactorDetail = Field(description="Time decay factor details")

    agent_utility: ModelFactorDetail = Field(description="Agent utility factor details")

    user_weighting: ModelFactorDetail = Field(
        description="User weighting factor details",
    )

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        validate_assignment = True
