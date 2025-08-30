#!/usr/bin/env python3
"""
RSD Ticket Cluster Model - ONEX Standards Compliant.

Strongly-typed model for ticket clustering and theme detection in RSD algorithm.
"""

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class ModelTicketCluster(BaseModel):
    """
    Model for grouping related tickets by theme.

    Used by ML clustering algorithms to group tickets into
    logical themes or epics for better organization in the
    RSD prioritization system.
    """

    cluster_id: str = Field(description="Unique identifier for this cluster")

    cluster_name: str = Field(description="Human-readable name for the cluster theme")

    ticket_ids: List[str] = Field(
        description="List of ticket IDs belonging to this cluster", default_factory=list
    )

    theme: str = Field(description="Identified theme or epic description")

    confidence_score: float = Field(
        description="Clustering algorithm confidence score (0.0-1.0)", ge=0.0, le=1.0
    )

    created_at: datetime = Field(
        description="When this cluster was created", default_factory=datetime.now
    )

    updated_at: datetime = Field(
        description="Last update timestamp", default_factory=datetime.now
    )

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        validate_assignment = True
        json_encoders = {datetime: lambda v: v.isoformat()}
