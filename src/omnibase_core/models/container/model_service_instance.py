"""Service instance model - implements ProtocolManagedServiceInstance."""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums import EnumInjectionScope, EnumServiceLifecycle
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelServiceInstance(BaseModel):
    """
    Service instance information.

    Implements ProtocolManagedServiceInstance.
    Tracks active service instances with lifecycle and scope information.

    Attributes:
        instance_id: Unique identifier for this instance
        service_registration_id: ID of the service registration
        instance: The actual service instance (stored as object)
        lifecycle: Lifecycle pattern (singleton, transient, scoped, etc.)
        scope: Injection scope (global, request, session, etc.)
        created_at: When this instance was created
        last_accessed: When this instance was last accessed
        access_count: Number of times this instance was accessed
        is_disposed: Whether this instance has been disposed
        metadata: Additional instance metadata

    Example:
        ```python
        from uuid import UUID
        from omnibase_core.enums import EnumServiceLifecycle, EnumInjectionScope
        instance = ModelServiceInstance(
            instance_id=UUID("12345678-1234-5678-1234-567812345678"),
            service_registration_id=UUID("87654321-4321-8765-4321-876543218765"),
            instance=logger_instance,
            lifecycle=EnumServiceLifecycle.SINGLETON,
            scope=EnumInjectionScope.GLOBAL,
        )
        ```
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=False,
        from_attributes=True,
        arbitrary_types_allowed=True,
    )

    instance_id: UUID = Field(description="Unique instance identifier")
    service_registration_id: UUID = Field(description="Registration ID")
    instance: object | None = Field(default=None, description="Actual service instance")
    lifecycle: EnumServiceLifecycle = Field(description="Lifecycle pattern")
    scope: EnumInjectionScope = Field(description="Injection scope")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp",
    )
    last_accessed: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last access timestamp",
    )
    access_count: int = Field(default=0, description="Access count")
    is_disposed: bool = Field(default=False, description="Disposal status")
    metadata: SerializedDict = Field(
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
        self.last_accessed = datetime.now(UTC)
        self.access_count += 1

    def dispose(self) -> None:
        """Mark instance as disposed."""
        self.is_disposed = True
        self.instance = None
