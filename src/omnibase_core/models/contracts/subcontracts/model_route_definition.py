import uuid
from typing import Any

from pydantic import Field

"""
Route Definition Model - ONEX Standards Compliant.

Individual model for route definition.
Part of the Routing Subcontract Model family.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ModelRouteDefinition(BaseModel):
    """
    Route definition for ONEX microservices routing.

    Defines routing rules, conditions, service targets,
    and transformation logic for request forwarding in ONEX ecosystem.
    """

    route_id: UUID = Field(default_factory=uuid4, description="Unique route identifier")

    route_name: str = Field(..., description="Unique name for the route", min_length=1)

    route_pattern: str = Field(
        ...,
        description="Pattern for matching requests (supports service discovery patterns)",
        min_length=1,
    )

    method: str | None = Field(
        default=None,
        description="HTTP method filter (GET, POST, etc.)",
    )

    conditions: list[str] = Field(
        default_factory=list,
        description="Conditions for route matching (supports service mesh conditions)",
    )

    service_targets: list[str] = Field(
        ...,
        description="Target microservice endpoints for routing",
        min_length=1,
    )

    weight: int = Field(
        default=100,
        description="Route weight for load balancing",
        ge=0,
        le=1000,
    )

    priority: int = Field(
        default=1,
        description="Route priority for conflict resolution",
        ge=1,
    )

    timeout_ms: int = Field(
        default=30000,
        description="Timeout for route requests",
        ge=100,
    )

    retry_enabled: bool = Field(
        default=True,
        description="Enable retry for failed requests",
    )

    max_retries: int = Field(default=3, description="Maximum number of retries", ge=0)

    # ONEX microservices specific features
    service_mesh_enabled: bool = Field(
        default=True,
        description="Enable service mesh integration",
    )

    correlation_id_required: bool = Field(
        default=True,
        description="Require correlation ID for request tracking",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
