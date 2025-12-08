"""Service registration model - implements ProtocolServiceRegistration."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.protocols import (
    LiteralHealthStatus,
    LiteralInjectionScope,
    LiteralServiceLifecycle,
)

from .model_service_metadata import ModelServiceMetadata

# Type alias for registration status
LiteralRegistrationStatus = Literal[
    "registered", "unregistered", "failed", "pending", "conflict", "invalid"
]


class ModelServiceRegistration(BaseModel):
    """
    Service registration information.

    Implements ProtocolServiceRegistration from omnibase_spi.
    Tracks service registration state including lifecycle, health,
    and access statistics.

    Attributes:
        registration_id: Unique registration identifier
        service_metadata: Comprehensive service metadata
        lifecycle: Lifecycle pattern (singleton, transient, scoped, etc.)
        scope: Injection scope (global, request, session, etc.)
        dependencies: List of service dependencies (simplified for v1.0)
        registration_status: Current registration status
        health_status: Service health status
        registration_time: When service was registered
        last_access_time: When service was last accessed
        access_count: Number of times service was accessed
        instance_count: Number of active instances
        max_instances: Maximum allowed instances (for pooled lifecycle)

    Example:
        ```python
        from uuid import UUID
        registration = ModelServiceRegistration(
            registration_id=UUID("12345678-1234-5678-1234-567812345678"),
            service_metadata=metadata,
            lifecycle="singleton",
            scope="global",
            registration_status="registered",
        )
        ```
    """

    registration_id: UUID = Field(description="Unique registration ID")
    service_metadata: ModelServiceMetadata = Field(description="Service metadata")
    lifecycle: LiteralServiceLifecycle = Field(description="Lifecycle pattern")
    scope: LiteralInjectionScope = Field(description="Injection scope")
    dependencies: list[str] = Field(
        default_factory=list,
        description="Service dependency names (simplified for v1.0)",
    )
    registration_status: LiteralRegistrationStatus = Field(
        default="registered",
        description="Registration status",
    )
    health_status: LiteralHealthStatus = Field(
        default="healthy",
        description="Service health status",
    )
    registration_time: datetime = Field(
        default_factory=datetime.now,
        description="Registration timestamp",
    )
    last_access_time: datetime | None = Field(
        default=None,
        description="Last access timestamp",
    )
    access_count: int = Field(default=0, description="Access count")
    instance_count: int = Field(default=0, description="Active instance count")
    max_instances: int | None = Field(
        default=None,
        description="Maximum instances (pooled lifecycle)",
    )

    async def validate_registration(self) -> bool:
        """
        Validate registration is valid and complete.

        Returns:
            True if registration is valid
        """
        return (
            self.registration_status == "registered"
            and self.health_status != "unhealthy"
            and self.service_metadata is not None
        )

    def is_active(self) -> bool:
        """
        Check if registration is currently active.

        Returns:
            True if registration is active and healthy
        """
        return (
            self.registration_status == "registered" and self.health_status == "healthy"
        )

    def mark_accessed(self) -> None:
        """Update access tracking."""
        self.last_access_time = datetime.now()
        self.access_count += 1

    def increment_instance_count(self) -> None:
        """Increment active instance count."""
        self.instance_count += 1

    def decrement_instance_count(self) -> None:
        """Decrement active instance count."""
        if self.instance_count > 0:
            self.instance_count -= 1
