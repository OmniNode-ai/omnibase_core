"""
ModelRouteHop: Individual hop in routing audit trail

This model tracks each hop in the routing path for audit and debugging purposes.
Follows AMQP envelope pattern for distributed event routing.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from omnibase_core.models.core.model_route_hop_metadata import ModelRouteHopMetadata


class ModelRouteHop(BaseModel):
    """
    Individual hop in the routing audit trail.

    Records details of each node/service that processes the envelope
    during multi-hop routing for debugging and audit purposes.
    """

    # Hop identification
    hop_id: UUID = Field(default=..., description="Unique identifier for this hop")
    node_id: UUID = Field(
        default=..., description="ID of the node that processed this hop"
    )
    service_name: str | None = Field(
        default=None, description="Service name if applicable"
    )

    # Timing information
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this hop was processed",
    )
    processing_duration_ms: int | None = Field(
        default=None,
        description="Time spent processing at this hop in milliseconds",
    )

    # Routing information
    hop_type: str = Field(
        default=...,
        description="Type of hop: 'source', 'router', 'destination'",
    )
    routing_decision: str | None = Field(
        default=None,
        description="Routing decision made at this hop",
    )
    next_hop: str | None = Field(default=None, description="Address of next hop chosen")

    # Metadata and debugging
    metadata: ModelRouteHopMetadata = Field(
        default_factory=ModelRouteHopMetadata,
        description="Additional hop-specific metadata",
    )
    error_info: str | None = Field(
        default=None,
        description="Error information if hop failed",
    )

    # Performance metrics
    queue_depth: int | None = Field(default=None, description="Queue depth at this hop")
    load_factor: float | None = Field(
        default=None,
        description="Load factor (0.0-1.0) at this hop",
    )

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        """Serialize datetime to ISO format."""
        return value.isoformat()

    @classmethod
    def create_source_hop(
        cls,
        node_id: UUID,
        service_name: str | None = None,
        **kwargs: Any,
    ) -> "ModelRouteHop":
        """Create a source hop (where the event originated)."""
        return cls(
            hop_id=uuid4(),
            node_id=node_id,
            service_name=service_name,
            hop_type="source",
            **kwargs,
        )

    @classmethod
    def create_router_hop(
        cls,
        node_id: UUID,
        routing_decision: str,
        next_hop: str,
        **kwargs: Any,
    ) -> "ModelRouteHop":
        """Create a router hop (intermediate routing node)."""
        return cls(
            hop_id=uuid4(),
            node_id=node_id,
            hop_type="router",
            routing_decision=routing_decision,
            next_hop=next_hop,
            **kwargs,
        )

    @classmethod
    def create_destination_hop(
        cls,
        node_id: UUID,
        service_name: str | None = None,
        **kwargs: Any,
    ) -> "ModelRouteHop":
        """Create a destination hop (final recipient)."""
        return cls(
            hop_id=uuid4(),
            node_id=node_id,
            service_name=service_name,
            hop_type="destination",
            **kwargs,
        )

    def mark_error(self, error_message: str) -> None:
        """Mark this hop as having encountered an error."""
        self.error_info = error_message

    def set_performance_metrics(
        self,
        processing_duration_ms: int,
        queue_depth: int | None = None,
        load_factor: float | None = None,
    ) -> None:
        """Set performance metrics for this hop."""
        self.processing_duration_ms = processing_duration_ms
        if queue_depth is not None:
            self.queue_depth = queue_depth
        if load_factor is not None:
            self.load_factor = load_factor

    def __str__(self) -> str:
        """Human-readable representation of the hop."""
        return f"{self.hop_type}:{self.node_id} @ {self.timestamp.isoformat()}"
