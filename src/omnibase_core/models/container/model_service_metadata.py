"""Service metadata model - implements ProtocolServiceRegistrationMetadata."""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelServiceMetadata(BaseModel):
    """
    Service registration metadata.

    Implements ProtocolServiceRegistrationMetadata.
    Provides comprehensive metadata for registered services including
    versioning, tagging, and configuration.

    Attributes:
        service_id: Unique identifier for the service
        service_name: Human-readable service name
        service_interface: Interface type name (e.g., "ProtocolLogger")
        service_implementation: Implementation class name
        version: Semantic version of the service
        description: Optional service description
        tags: List of tags for categorization
        configuration: Additional configuration key-value pairs
        created_at: Timestamp when service was registered
        last_modified_at: Timestamp when service was last modified

    Example:
        ```python
        from uuid import UUID
        metadata = ModelServiceMetadata(
            service_id=UUID("12345678-1234-5678-1234-567812345678"),
            service_name="enhanced_logger",
            service_interface="ProtocolLogger",
            service_implementation="EnhancedLogger",
            version=ModelSemVer(major=1, minor=0, patch=0),
            tags=["logging", "core"],
        )
        ```
    """

    # from_attributes=True allows Pydantic to accept objects with matching
    # attributes even when class identity differs (e.g., in pytest-xdist
    # parallel execution where model classes are imported in separate workers).
    # See CLAUDE.md section "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    service_id: UUID = Field(description="Unique service identifier")
    service_name: str = Field(description="Human-readable service name")
    service_interface: str = Field(description="Interface type name")
    service_implementation: str = Field(description="Implementation class name")
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Semantic version",
    )
    description: str | None = Field(
        default=None,
        description="Optional service description",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Service tags for categorization",
    )
    configuration: SerializedDict = Field(
        default_factory=dict,
        description="Additional configuration",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Registration timestamp",
    )
    last_modified_at: datetime | None = Field(
        default=None,
        description="Last modification timestamp",
    )
