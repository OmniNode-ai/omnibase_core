"""Service instance model - implements ProtocolDIServiceInstance."""

from datetime import datetime
from typing import Any
from uuid import UUID

from omnibase_spi.protocols.container import (
    LiteralInjectionScope,
    LiteralServiceLifecycle,
)
from pydantic import BaseModel, Field


class ModelServiceInstance(BaseModel):
    """
    Service instance information.

    Implements ProtocolDIServiceInstance from omnibase_spi.
    Tracks active service instances with lifecycle and scope information.

    Attributes:
        instance_id: Unique identifier for this instance
        service_registration_id: ID of the service registration
        instance: The actual service instance (stored as Any)
        lifecycle: Lifecycle pattern (singleton, transient, scoped, etc.)
        scope: Injection scope (global, request, session, etc.)
        created_at: When this instance was created
        last_accessed: When this instance was last accessed
        access_count: Number of times this instance was accessed
        is_disposed: Whether this instance has been disposed
        metadata: Additional instance metadata

    Example:
        ```python
        instance = ModelServiceInstance(
            instance_id="inst-456",
            service_registration_id="reg-123",
            instance=logger_instance,
            lifecycle="singleton",
            scope="global",
        )
        ```
    """

    model_config = {"arbitrary_types_allowed": True}

    instance_id: UUID = Field(description="Unique instance identifier")
    service_registration_id: UUID = Field(description="Registration ID")
    instance: Any = Field(description="Actual service instance")
    lifecycle: LiteralServiceLifecycle = Field(description="Lifecycle pattern")
    scope: LiteralInjectionScope = Field(description="Injection scope")
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Creation timestamp",
    )
    last_accessed: datetime = Field(
        default_factory=datetime.now,
        description="Last access timestamp",
    )
    access_count: int = Field(default=0, description="Access count")
    is_disposed: bool = Field(default=False, description="Disposal status")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )

    async def validate_instance(self) -> bool:
        """
        Validate instance is still valid.

        Returns:
            True if instance is valid and not disposed
        """
        return not self.is_disposed and self.instance is not None

    def is_active(self) -> bool:
        """
        Check if instance is active.

        Returns:
            True if instance is not disposed
        """
        return not self.is_disposed

    def mark_accessed(self) -> None:
        """Update access tracking."""
        self.last_accessed = datetime.now()
        self.access_count += 1

    def dispose(self) -> None:
        """Mark instance as disposed."""
        self.is_disposed = True
        self.instance = None
