"""Service metadata model - implements ProtocolServiceRegistrationMetadata.

Provides comprehensive metadata for registered services in the ONEX
dependency injection container.

Thread Safety:
    This model uses `from_attributes=True` for ORM/dataclass compatibility.
    While the model itself is mutable, the `from_attributes` config is safe
    when source objects are either:
    1. Immutable (frozen Pydantic models, NamedTuples)
    2. Not shared across threads during model creation

    For thread-safe service registration, ensure single-writer semantics
    when creating metadata from mutable source objects.

See Also:
    docs/conventions/PYDANTIC_BEST_PRACTICES.md: Guidelines for from_attributes usage.
    docs/architecture/CONTAINER_TYPES.md: Container and DI architecture.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types.type_serializable_value import SerializedDict
from omnibase_core.utils.util_decorators import allow_dict_str_any


@allow_dict_str_any(
    "Service metadata configuration requires flexible dict for service-specific "
    "settings that vary across implementations (e.g., connection pooling, timeouts)."
)
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
        tags: List of tags for categorization (see docs/conventions/NAMING_CONVENTIONS.md
            for tag format: `<category>:<value>`)
        configuration: Additional configuration key-value pairs
        created_at: Timestamp when service was registered
        last_modified_at: Timestamp when service was last modified

    Thread Safety:
        This model uses `from_attributes=True` for ORM compatibility. When
        creating from mutable source objects, ensure the source is not being
        modified concurrently. The created Pydantic model is independent of
        the source after creation.

    Example:
        ```python
        from uuid import UUID
        metadata = ModelServiceMetadata(
            service_id=UUID("12345678-1234-5678-1234-567812345678"),
            service_name="enhanced_logger",
            service_interface="ProtocolLogger",
            service_implementation="EnhancedLogger",
            version=ModelSemVer(major=1, minor=0, patch=0),
            tags=["env:production", "tier:core"],  # Use category:value format
        )
        ```
    """

    model_config = ConfigDict(
        from_attributes=True,  # ORM compatibility - see module docstring for safety notes
    )

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
        default_factory=datetime.now,
        description="Registration timestamp",
    )
    last_modified_at: datetime | None = Field(
        default=None,
        description="Last modification timestamp",
    )
