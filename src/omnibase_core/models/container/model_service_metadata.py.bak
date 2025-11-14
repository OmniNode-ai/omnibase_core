"""Service metadata model - implements ProtocolDIServiceMetadata."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelServiceMetadata(BaseModel):
    """
    Service registration metadata.

    Implements ProtocolDIServiceMetadata from omnibase_spi.
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
        metadata = ModelServiceMetadata(
            service_id="logger-123",
            service_name="enhanced_logger",
            service_interface="ProtocolLogger",
            service_implementation="EnhancedLogger",
            version=ModelSemVer(major=1, minor=0, patch=0),
            tags=["logging", "core"],
        )
        ```
    """

    service_id: UUID = Field(description="Unique service identifier")
    service_name: str = Field(description="Human-readable service name")
    service_interface: str = Field(description="Interface type name")
    service_implementation: str = Field(description="Implementation class name")
    version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
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
    configuration: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional configuration",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Registration timestamp",
    )
    last_modified_at: datetime | None = Field(
        default=None,
        description="Last modification timestamp",
    )
