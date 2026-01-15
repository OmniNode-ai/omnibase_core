"""
ModelRouteSpec: Routing specifications and strategy

This model defines how events should be routed through the distributed system.
Supports various routing patterns including explicit routing, dynamic routing,
anycast, and constraint-based routing.
"""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.core.model_routing_constraints import ModelRoutingConstraints
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelRouteSpec(BaseModel):
    """
    Routing specification for event envelopes.

    Defines destination, routing path, strategy, and constraints
    for multi-hop event routing in distributed systems.
    """

    model_config = ConfigDict(extra="forbid", frozen=False)

    # Core routing information
    final_destination: str = Field(
        default=...,
        description="Ultimate destination address (node://, service://, etc.)",
    )
    remaining_hops: list[str] = Field(
        default_factory=list,
        description="Explicit routing path (if any)",
    )

    # Routing strategy
    routing_strategy: str = Field(
        default="dynamic",
        description="Routing strategy: 'explicit', 'dynamic', 'anycast', 'broadcast'",
    )

    # Routing constraints
    constraints: ModelRoutingConstraints = Field(
        default_factory=ModelRoutingConstraints,
        description="Routing constraints and preferences",
    )

    # Control parameters
    ttl: int = Field(
        default=32,
        description="Time-to-live (max hops) to prevent routing loops",
    )
    priority: int = Field(
        default=5,
        description="Routing priority (1=highest, 10=lowest)",
    )

    # Optional routing preferences
    preferred_regions: list[str] = Field(
        default_factory=list,
        description="Preferred routing regions",
    )
    avoid_nodes: list[str] = Field(
        default_factory=list,
        description="Nodes to avoid in routing",
    )

    # Delivery requirements
    delivery_mode: str = Field(
        default="best_effort",
        description="Delivery mode: 'best_effort', 'guaranteed', 'at_least_once'",
    )
    timeout_ms: int | None = Field(
        default=None,
        description="Maximum routing timeout in milliseconds",
    )

    @field_validator("final_destination")
    @classmethod
    def validate_destination_address(cls, v: str) -> str:
        """Validate destination address format."""
        valid_patterns = [
            r"^node://[a-f0-9-]+$",  # node://uuid
            r"^service://[\w-]+$",  # service://name
            r"^broadcast://all$",  # broadcast://all
            r"^group://[\w-]+$",  # group://name
            r"^region://[\w-]+/service/[\w-]+$",  # region://region/service/name
        ]

        if not any(re.match(pattern, v) for pattern in valid_patterns):
            msg = f"Invalid destination address format: {v}"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    @field_validator("remaining_hops")
    @classmethod
    def validate_hop_addresses(cls, v: list[str]) -> list[str]:
        """Validate hop address formats."""
        for hop in v:
            # Use same validation as final_destination
            valid_patterns = [
                r"^node://[a-f0-9-]+$",
                r"^service://[\w-]+$",
                r"^region://[\w-]+/service/[\w-]+$",
            ]
            if not any(re.match(pattern, hop) for pattern in valid_patterns):
                msg = f"Invalid hop address format: {hop}"
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                )
        return v

    @field_validator("routing_strategy")
    @classmethod
    def validate_routing_strategy(cls, v: str) -> str:
        """Validate routing strategy."""
        valid_strategies = ["explicit", "dynamic", "anycast", "broadcast", "multicast"]
        if v not in valid_strategies:
            msg = f"Invalid routing strategy: {v}. Must be one of {valid_strategies}"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    @field_validator("delivery_mode")
    @classmethod
    def validate_delivery_mode(cls, v: str) -> str:
        """Validate delivery mode."""
        valid_modes = ["best_effort", "guaranteed", "at_least_once", "at_most_once"]
        if v not in valid_modes:
            msg = f"Invalid delivery mode: {v}. Must be one of {valid_modes}"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    @field_validator("ttl")
    @classmethod
    def validate_ttl(cls, v: int) -> int:
        """Validate TTL is reasonable."""
        if v < 1 or v > 255:
            msg = "TTL must be between 1 and 255"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: int) -> int:
        """Validate priority range."""
        if v < 1 or v > 10:
            msg = "Priority must be between 1 (highest) and 10 (lowest)"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    @classmethod
    def create_direct_route(
        cls, destination: str, **kwargs: object
    ) -> "ModelRouteSpec":
        """Create a direct route to destination with dynamic routing."""
        # NOTE(OMN-1302): kwargs forwarded to Pydantic model constructor, types verified by Pydantic validation.
        return cls(final_destination=destination, routing_strategy="dynamic", **kwargs)  # type: ignore[arg-type]

    @classmethod
    def create_explicit_route(
        cls,
        destination: str,
        hops: list[str],
        **kwargs: object,
    ) -> "ModelRouteSpec":
        """Create an explicit route through specified hops."""
        # NOTE(OMN-1302): kwargs forwarded to Pydantic model constructor, types verified by Pydantic validation.
        return cls(
            final_destination=destination,
            remaining_hops=hops.copy(),
            routing_strategy="explicit",
            **kwargs,  # type: ignore[arg-type]
        )

    @classmethod
    def create_anycast_route(
        cls, service_pattern: str, **kwargs: object
    ) -> "ModelRouteSpec":
        """Create anycast route to any instance of a service."""
        # NOTE(OMN-1302): kwargs forwarded to Pydantic model constructor, types verified by Pydantic validation.
        return cls(
            final_destination=service_pattern,
            routing_strategy="anycast",
            **kwargs,  # type: ignore[arg-type]
        )

    @classmethod
    def create_broadcast_route(cls, **kwargs: object) -> "ModelRouteSpec":
        """Create broadcast route to all nodes."""
        # NOTE(OMN-1302): kwargs forwarded to Pydantic model constructor, types verified by Pydantic validation.
        return cls(
            final_destination="broadcast://all",
            routing_strategy="broadcast",
            **kwargs,  # type: ignore[arg-type]
        )

    def add_constraint(self, key: str, value: ModelSchemaValue) -> None:
        """Add a routing constraint."""
        self.constraints.custom_constraints[key] = value

    def set_latency_constraint(self, max_latency_ms: int) -> None:
        """Set maximum acceptable latency constraint."""
        self.constraints.max_latency_ms = max_latency_ms

    def set_region_constraint(self, allowed_regions: list[str]) -> None:
        """Set allowed regions constraint."""
        self.constraints.allowed_regions = allowed_regions

    def set_security_constraint(self, min_security_level: str) -> None:
        """Set minimum security level constraint."""
        self.constraints.min_security_level = min_security_level

    def consume_next_hop(self) -> str | None:
        """Consume and return the next hop from remaining_hops."""
        if self.remaining_hops:
            return self.remaining_hops.pop(0)
        return None

    def add_hop_to_route(self, hop_address: str) -> None:
        """Add a hop to the remaining route (for dynamic routing)."""
        self.remaining_hops.append(hop_address)

    def decrement_ttl(self) -> int:
        """Decrement TTL and return new value."""
        self.ttl -= 1
        return self.ttl

    def is_expired(self) -> bool:
        """Check if TTL has expired."""
        return self.ttl <= 0

    def is_at_destination(self, current_address: str) -> bool:
        """Check if we've reached the final destination."""
        return current_address == self.final_destination

    def has_remaining_hops(self) -> bool:
        """Check if there are remaining explicit hops."""
        return len(self.remaining_hops) > 0

    def __str__(self) -> str:
        """Human-readable representation of the route spec."""
        hops_str = (
            " -> ".join(self.remaining_hops) if self.remaining_hops else "dynamic"
        )
        return f"{self.routing_strategy}: {hops_str} -> {self.final_destination} (TTL: {self.ttl})"
