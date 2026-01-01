"""Injection Context Model.

Implements ProtocolInjectionContext for dependency injection tracking.

This model provides context information for dependency injection operations,
including:
- Resolution status and error tracking
- Dependency path tracking for circular detection
- Scope and timing information

Used by the service registry to track injection operations and
diagnose resolution failures.
"""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.protocols import (
    LiteralInjectionScope,
    LiteralServiceResolutionStatus,
)
from omnibase_core.types.type_serializable_value import SerializableValue


class ModelInjectionContext(BaseModel):
    """
    Context for dependency injection operations.

    Implements ProtocolInjectionContext.
    Tracks the state of an injection operation including resolution
    status, resolved dependencies, and error information.

    Attributes:
        context_id: Unique identifier for this injection context
        target_service_id: ID of the service being resolved
        scope: Injection scope (global, request, session, etc.)
        resolved_dependencies: Map of resolved dependency values
        injection_time: When the injection was initiated
        resolution_status: Current status of resolution
        error_details: Error message if resolution failed
        resolution_path: Path of service IDs for circular detection
        metadata: Additional context metadata

    Example:
        ```python
        context = ModelInjectionContext(
            context_id=uuid4(),
            target_service_id=UUID("12345678-..."),
            scope="global",
            resolution_status="resolved",
        )
        ```
    """

    model_config = ConfigDict(
        extra="ignore",
        frozen=False,
        validate_assignment=True,
    )

    context_id: UUID = Field(description="Unique identifier for this injection context")
    target_service_id: UUID = Field(description="ID of the service being resolved")
    scope: LiteralInjectionScope = Field(
        default="global",
        description="Injection scope",
    )
    resolved_dependencies: dict[str, SerializableValue] = Field(
        default_factory=dict,
        description="Map of resolved dependency values",
    )
    injection_time: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the injection was initiated",
    )
    resolution_status: LiteralServiceResolutionStatus = Field(
        description="Current status of resolution",
    )
    error_details: str | None = Field(
        default=None,
        description="Error message if resolution failed",
    )
    resolution_path: list[UUID] = Field(
        default_factory=list,
        description="Path of service IDs for circular detection",
    )
    metadata: dict[str, SerializableValue] = Field(
        default_factory=dict,
        description="Additional context metadata",
    )

    @property
    def is_resolved(self) -> bool:
        """Check if the service was successfully resolved."""
        return self.resolution_status == "resolved"

    @property
    def has_error(self) -> bool:
        """Check if resolution encountered an error."""
        return self.resolution_status == "failed" or self.error_details is not None

    @property
    def has_circular_dependency(self) -> bool:
        """Check if resolution failed due to circular dependency."""
        return self.resolution_status == "circular_dependency"

    @property
    def has_missing_dependency(self) -> bool:
        """Check if resolution failed due to missing dependency."""
        return self.resolution_status == "missing_dependency"

    def mark_resolved(self) -> None:
        """Mark the injection as successfully resolved."""
        self.resolution_status = "resolved"
        self.error_details = None

    def mark_failed(self, error_message: str) -> None:
        """Mark the injection as failed with an error."""
        self.resolution_status = "failed"
        self.error_details = error_message

    def mark_circular_dependency(self, error_message: str) -> None:
        """Mark the injection as failed due to circular dependency."""
        self.resolution_status = "circular_dependency"
        self.error_details = error_message

    def mark_missing_dependency(self, error_message: str) -> None:
        """Mark the injection as failed due to missing dependency."""
        self.resolution_status = "missing_dependency"
        self.error_details = error_message

    def mark_type_mismatch(self, error_message: str) -> None:
        """Mark the injection as failed due to type mismatch."""
        self.resolution_status = "type_mismatch"
        self.error_details = error_message

    def add_to_path(self, service_id: UUID) -> bool:
        """
        Add a service to the resolution path.

        Returns:
            True if added successfully, False if already in path (circular)
        """
        if service_id in self.resolution_path:
            return False
        self.resolution_path.append(service_id)
        return True

    def add_resolved_dependency(self, name: str, value: SerializableValue) -> None:
        """Add a resolved dependency value."""
        self.resolved_dependencies[name] = value


__all__ = ["ModelInjectionContext"]
