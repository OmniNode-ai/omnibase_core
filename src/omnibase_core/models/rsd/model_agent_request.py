#!/usr/bin/env python3
"""
RSD Agent Request Model - ONEX Standards Compliant.

Strongly-typed model for agent ticket requests in RSD algorithm.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_rsd_agent_request_type import EnumRSDAgentRequestType


class ModelAgentRequest(BaseModel):
    """
    Model for tracking agent ticket requests for priority boosting.

    Used in RSD algorithm to track and weight agent-initiated requests
    for ticket prioritization adjustments based on agent authority and urgency.
    """

    request_id: str = Field(description="Unique request identifier")

    agent_id: str = Field(description="Agent making the request")

    ticket_id: str = Field(description="Ticket being requested")

    request_type: EnumRSDAgentRequestType = Field(description="Type of agent request")

    priority_boost: float = Field(
        description="Priority boost factor (0.0-2.0)",
        ge=0.0,
        le=2.0,
    )

    reason: str = Field(description="Reason for the request")

    timestamp: datetime = Field(
        description="When the request was made",
        default_factory=datetime.now,
    )

    processed: bool = Field(
        description="Whether request has been processed",
        default=False,
    )

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        validate_assignment = True
        json_encoders = {datetime: lambda v: v.isoformat()}
