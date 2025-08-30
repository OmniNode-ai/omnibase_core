#!/usr/bin/env python3
"""
RSD Ticket Edge Model - ONEX Standards Compliant.

Strongly-typed model for edges in ticket dependency graphs.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.tools.rsd.shared.enums.enum_rsd_edge_type import \
    EnumRSDEdgeType


class ModelTicketEdge(BaseModel):
    """
    Model for graph edge relationships between tickets.

    Used in RSD algorithm to represent dependency relationships
    between tickets with their types and weights.
    """

    source_ticket_id: str = Field(
        description="Source ticket ID in dependency relationship"
    )

    target_ticket_id: str = Field(
        description="Target ticket ID in dependency relationship"
    )

    edge_type: EnumRSDEdgeType = Field(
        description="Type of relationship between tickets"
    )

    weight: float = Field(
        description="Strength of relationship (0.0-1.0)", ge=0.0, le=1.0
    )

    created_at: datetime = Field(
        description="When this edge was created", default_factory=datetime.now
    )

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        validate_assignment = True
        json_encoders = {datetime: lambda v: v.isoformat()}
