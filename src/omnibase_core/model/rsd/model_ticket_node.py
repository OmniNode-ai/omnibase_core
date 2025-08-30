#!/usr/bin/env python3
"""
RSD Ticket Node Model - ONEX Standards Compliant.

Strongly-typed model for ticket nodes in dependency graph visualization.
"""

from pydantic import BaseModel, Field

from omnibase_core.model.rsd.model_ticket_metadata import ModelTicketMetadata


class ModelTicketNode(BaseModel):
    """
    Model for graph visualization node representing a ticket.

    Used in RSD algorithm for visualizing tickets in dependency graphs
    with their calculated priority scores and positioning information.
    """

    ticket_id: str = Field(description="Unique ticket identifier")

    priority_score: float = Field(
        description="Calculated priority score (0.0-100.0)",
        ge=0.0,
        le=100.0,
    )

    node_size: float = Field(
        description="Visual size of node based on importance",
        gt=0.0,
    )

    position_x: float = Field(description="X coordinate for graph layout")

    position_y: float = Field(description="Y coordinate for graph layout")

    metadata: ModelTicketMetadata = Field(
        description="Additional node metadata for rendering",
        default_factory=ModelTicketMetadata,
    )

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        validate_assignment = True
