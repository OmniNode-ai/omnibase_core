import json
import uuid
from typing import Dict, Optional

from pydantic import Field

from omnibase_core.models.core.model_onex_event import ModelOnexEvent

"""
ModelEventEnvelope: Event envelope for distributed routing

This model implements the AMQP-style envelope pattern that separates
routing logic from event data. Enables multi-hop routing with audit trails
while keeping the original event payload unchanged.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.core.model_semver import ModelSemVer

from .model_onex_event import ModelOnexEvent
from .model_route_hop import ModelRouteHop
from .model_route_spec import ModelRouteSpec


class ModelEventEnvelope(BaseModel):
    """
    Event envelope for distributed multi-hop routing.

    Wraps events with routing information while keeping the original
    payload unchanged. Follows AMQP envelope pattern for enterprise
    service bus compatibility.
    """

    # Envelope identification
    envelope_id: UUID = Field(
        default_factory=uuid4,
        description="Unique envelope identifier",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the envelope was created",
    )

    # Routing information
    route_spec: ModelRouteSpec = Field(
        default=...,
        description="Routing specification and strategy",
    )
    trace: list[ModelRouteHop] = Field(
        default_factory=list,
        description="Routing audit trail",
    )

    # Event payload (unchanged by routers)
    payload: ModelOnexEvent = Field(
        default=..., description="The actual event being routed"
    )

    # Envelope metadata
    source_node_id: UUID = Field(default=..., description="Original source node ID")
    envelope_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Envelope format version",
    )
    correlation_id: UUID = Field(
        default=...,
        description="Correlation ID for request/response tracking",
    )

    # Status tracking
    current_hop_count: int = Field(default=0, description="Number of hops taken so far")
    is_delivered: bool = Field(
        default=False,
        description="Whether envelope has been delivered",
    )
    delivery_attempts: int = Field(default=0, description="Number of delivery attempts")

    # Optional metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional envelope metadata",
    )

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)},
    )

    @classmethod
    def create_direct(
        cls,
        payload: ModelOnexEvent,
        destination: str,
        source_node_id: str,
        **kwargs: Any,
    ) -> "ModelEventEnvelope":
        """Create envelope for direct routing to destination."""
        route_spec = ModelRouteSpec.create_direct_route(destination)

        envelope = cls(
            payload=payload,
            route_spec=route_spec,
            source_node_id=source_node_id,
            **kwargs,
        )

        # Add source hop to trace
        envelope.add_source_hop(source_node_id)
        return envelope

    @classmethod
    def create_explicit_route(
        cls,
        payload: ModelOnexEvent,
        destination: str,
        hops: list[str],
        source_node_id: str,
        **kwargs: Any,
    ) -> "ModelEventEnvelope":
        """Create envelope with explicit routing path."""
        route_spec = ModelRouteSpec.create_explicit_route(destination, hops)

        envelope = cls(
            payload=payload,
            route_spec=route_spec,
            source_node_id=source_node_id,
            **kwargs,
        )

        # Add source hop to trace
        envelope.add_source_hop(source_node_id)
        return envelope

    @classmethod
    def create_anycast(
        cls,
        payload: ModelOnexEvent,
        service_pattern: str,
        source_node_id: str,
        **kwargs: Any,
    ) -> "ModelEventEnvelope":
        """Create envelope for anycast routing to service."""
        route_spec = ModelRouteSpec.create_anycast_route(service_pattern)

        envelope = cls(
            payload=payload,
            route_spec=route_spec,
            source_node_id=source_node_id,
            **kwargs,
        )

        # Add source hop to trace
        envelope.add_source_hop(source_node_id)
        return envelope

    @classmethod
    def create_broadcast(
        cls,
        payload: ModelOnexEvent,
        source_node_id: str,
        **kwargs: Any,
    ) -> "ModelEventEnvelope":
        """Create envelope for broadcast routing."""
        route_spec = ModelRouteSpec.create_broadcast_route()

        envelope = cls(
            payload=payload,
            route_spec=route_spec,
            source_node_id=source_node_id,
            **kwargs,
        )

        # Add source hop to trace
        envelope.add_source_hop(source_node_id)
        return envelope

    def add_source_hop(self, node_id: str, service_name: str | None = None) -> None:
        """Add source hop to the trace."""
        hop = ModelRouteHop.create_source_hop(
            UUID(node_id) if isinstance(node_id, str) else node_id, service_name
        )
        self.trace.append(hop)

    def add_router_hop(
        self,
        node_id: str,
        routing_decision: str,
        next_hop: str,
        **kwargs: Any,
    ) -> None:
        """Add a router hop to the trace."""
        hop = ModelRouteHop.create_router_hop(
            UUID(node_id) if isinstance(node_id, str) else node_id,
            routing_decision,
            next_hop,
            **kwargs,
        )
        self.trace.append(hop)
        self.current_hop_count += 1

    def add_destination_hop(
        self,
        node_id: str,
        service_name: str | None = None,
    ) -> None:
        """Add destination hop and mark as delivered."""
        hop = ModelRouteHop.create_destination_hop(
            UUID(node_id) if isinstance(node_id, str) else node_id, service_name
        )
        self.trace.append(hop)
        self.is_delivered = True

    def consume_next_hop(self) -> str | None:
        """Get the next hop from the route specification."""
        return self.route_spec.consume_next_hop()

    def add_hop_to_route(self, hop_address: str) -> None:
        """Add a hop to the route (for dynamic routing)."""
        self.route_spec.add_hop_to_route(hop_address)

    def increment_hop_count(self) -> int:
        """Increment and return the hop count."""
        self.current_hop_count += 1
        return self.current_hop_count

    def decrement_ttl(self) -> int:
        """Decrement TTL in route spec and return new value."""
        return self.route_spec.decrement_ttl()

    def is_ttl_expired(self) -> bool:
        """Check if TTL has expired."""
        return self.route_spec.is_expired()

    def is_at_destination(self, current_address: str) -> bool:
        """Check if we've reached the final destination."""
        return self.route_spec.is_at_destination(current_address)

    def has_remaining_hops(self) -> bool:
        """Check if there are remaining explicit hops."""
        return self.route_spec.has_remaining_hops()

    def mark_delivery_attempt(self) -> int:
        """Mark a delivery attempt and return new count."""
        self.delivery_attempts += 1
        return self.delivery_attempts

    def mark_error(self, error_message: str) -> None:
        """Mark the last hop with an error."""
        if self.trace:
            self.trace[-1].mark_error(error_message)

    def set_correlation_id(self, correlation_id: UUID) -> None:
        """Set correlation ID for request/response patterns."""
        self.correlation_id = correlation_id

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the envelope."""
        self.metadata[key] = value

    def get_routing_path(self) -> list[str]:
        """Get the complete routing path from trace."""
        return [f"{hop.hop_type}:{hop.node_id}" for hop in self.trace]

    def get_last_hop(self) -> ModelRouteHop | None:
        """Get the last hop from the trace."""
        return self.trace[-1] if self.trace else None

    def can_continue_routing(self) -> bool:
        """Check if routing can continue (TTL not expired, not delivered)."""
        return not self.is_ttl_expired() and not self.is_delivered

    def validate_routing_state(self) -> list[str]:
        """Validate the current routing state and return any issues."""
        issues = []

        if self.is_ttl_expired():
            issues.append("TTL expired")

        if self.current_hop_count > 100:  # Sanity check for routing loops
            issues.append("Excessive hop count - possible routing loop")

        if self.delivery_attempts > 10:
            issues.append("Excessive delivery attempts")

        if not self.trace:
            issues.append("No trace hops recorded")

        return issues

    def clone_for_retry(self) -> "ModelEventEnvelope":
        """Create a copy of this envelope for retry delivery."""
        # Create a new envelope with the same payload and route spec
        new_envelope = ModelEventEnvelope(
            payload=self.payload.model_copy(deep=True),
            route_spec=self.route_spec.model_copy(deep=True),
            source_node_id=self.source_node_id,
            correlation_id=self.correlation_id,
            metadata=self.metadata.copy(),
        )

        # Copy trace but reset delivery state
        new_envelope.trace = [hop.model_copy(deep=True) for hop in self.trace]
        new_envelope.current_hop_count = self.current_hop_count
        new_envelope.delivery_attempts = self.delivery_attempts + 1

        return new_envelope

    def __str__(self) -> str:
        """Human-readable representation of the envelope."""
        path = " -> ".join(self.get_routing_path()) if self.trace else "no hops"
        status = "delivered" if self.is_delivered else "in-transit"
        return f"Envelope[{self.envelope_id[:8]}] {status}: {path} (TTL: {self.route_spec.ttl})"
