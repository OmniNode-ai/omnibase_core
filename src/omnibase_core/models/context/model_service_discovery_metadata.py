"""
Service discovery metadata model for service discovery and composition.

This module provides ModelServiceDiscoveryMetadata, a typed model for service-related
metadata that replaces untyped dict[str, ModelSchemaValue] fields. It captures
service identification, capabilities, and discovery information.

Note:
    This model is distinct from ModelServiceMetadata in models/container/, which
    is used for service registration in the DI container. This model focuses on
    service discovery and composition in distributed systems.

Thread Safety:
    ModelServiceDiscoveryMetadata is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access from multiple threads or async tasks.

    CAVEAT: The list fields (capabilities, dependencies, tags) can still have their
    contents mutated even on a frozen model (Pydantic's frozen only prevents field
    reassignment, not mutation of mutable container contents). Treat these lists as
    immutable by convention for thread safety.

See Also:
    - omnibase_core.models.context.model_session_context: Session context metadata
    - omnibase_core.models.context.model_http_request_metadata: HTTP request metadata
"""

from typing import Literal, cast
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = ["ModelServiceDiscoveryMetadata"]

# Type alias for service protocols
ServiceProtocol = Literal["grpc", "http", "https", "ws", "wss"]

# Valid protocol values for service communication (for validation error messages)
VALID_PROTOCOLS = frozenset({"grpc", "http", "https", "ws", "wss"})


class ModelServiceDiscoveryMetadata(BaseModel):
    """Service discovery metadata for service discovery and composition.

    Provides typed service identification, capabilities, and discovery
    information. Used for service registration, health checking, and
    dynamic service composition in distributed systems.

    Note:
        This model is distinct from ModelServiceMetadata in models/container/,
        which is used for service registration in the DI container.

    Attributes:
        service_name: Unique service name for discovery. Required field
            that identifies the service in the registry.
        service_version: Semantic version of the service using ModelSemVer.
            Used for version-aware routing and compatibility checks.
        service_instance_id: UUID identifier for this service instance.
            Distinguishes between multiple instances of the same service.
        health_check_url: URL endpoint for health checks. Must be a valid
            HTTP(S) URL when provided (e.g., "https://service:8080/health").
        capabilities: List of service capabilities for feature discovery.
            Services can advertise what operations they support. WARNING:
            While model is frozen, list contents can be mutated. Treat as
            immutable by convention for thread safety.
        dependencies: List of service names this service depends on.
            Used for dependency tracking and startup ordering. WARNING:
            While model is frozen, list contents can be mutated. Treat as
            immutable by convention for thread safety.
        tags: Discovery tags for service categorization and filtering.
            Enables tag-based service lookup (e.g., ["production", "us-west"]).
            WARNING: While model is frozen, list contents can be mutated.
            Treat as immutable by convention for thread safety.
        protocol: Communication protocol for the service. Valid values are
            "grpc", "http", "https", "ws", "wss". Defaults to "grpc".

    Thread Safety:
        This model is frozen (field reassignment prevented) and safe for
        concurrent read access across threads. CAVEAT: The list fields
        (capabilities, dependencies, tags) CAN have their contents mutated
        even on a frozen model. For true thread safety, never modify list
        contents after model creation.

    Example:
        >>> from uuid import UUID
        >>> from omnibase_core.models.context import ModelServiceDiscoveryMetadata
        >>> from omnibase_core.models.primitives.model_semver import ModelSemVer
        >>>
        >>> metadata = ModelServiceDiscoveryMetadata(
        ...     service_name="user-service",
        ...     service_version=ModelSemVer(major=2, minor=1, patch=0),
        ...     service_instance_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        ...     health_check_url="https://user-service:8080/health",
        ...     capabilities=["create_user", "delete_user", "list_users"],
        ...     dependencies=["auth-service", "database-service"],
        ...     tags=["production", "us-west-2"],
        ...     protocol="grpc",
        ... )
        >>> metadata.service_name
        'user-service'
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    service_name: str = Field(
        ...,
        min_length=1,
        description="Unique service name for discovery (required identifier in the registry)",
    )
    service_version: ModelSemVer | None = Field(
        default=None,
        description="Semantic version of the service using ModelSemVer type",
    )
    service_instance_id: UUID | None = Field(
        default=None,
        description="UUID identifier for this service instance",
    )
    health_check_url: str | None = Field(
        default=None,
        description="Health check endpoint URL (e.g., 'https://service:8080/health')",
    )
    # IMPORTANT - Mutable List Limitation:
    # While this model has frozen=True (Pydantic ConfigDict), list contents can still
    # be mutated after model creation. Pydantic's frozen setting only prevents reassigning
    # the field itself (e.g., `model.capabilities = new_list` raises an error), but does
    # NOT prevent mutating the list contents (e.g., `model.capabilities.append("value")`
    # will succeed). For thread safety, treat these lists as immutable by convention:
    # - Never modify list contents after model creation
    # - Create a new model instance if you need different list values
    # - In multi-threaded contexts, create separate model instances per thread
    capabilities: list[str] = Field(
        default_factory=list,
        description=(
            "List of service capabilities for feature discovery. "
            "WARNING: While model is frozen, list contents can be mutated. "
            "Treat as immutable by convention for thread safety."
        ),
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description=(
            "List of service names this service depends on. "
            "WARNING: While model is frozen, list contents can be mutated. "
            "Treat as immutable by convention for thread safety."
        ),
    )
    tags: list[str] = Field(
        default_factory=list,
        description=(
            "Discovery tags for service categorization and filtering. "
            "WARNING: While model is frozen, list contents can be mutated. "
            "Treat as immutable by convention for thread safety."
        ),
    )
    protocol: ServiceProtocol = Field(
        default="grpc",
        description="Service protocol: 'grpc', 'http', 'https', 'ws', or 'wss'",
    )

    @field_validator("protocol", mode="before")
    @classmethod
    def validate_protocol(cls, v: str) -> ServiceProtocol:
        """Validate that protocol is a supported service communication protocol.

        Args:
            v: The protocol string to validate.

        Returns:
            The validated protocol as a Literal type (lowercase).

        Raises:
            ValueError: If the value is not a string or not a valid protocol.
        """
        if not isinstance(v, str):
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(f"Protocol must be a string, got {type(v).__name__}")
        normalized = v.lower().strip()
        if normalized not in VALID_PROTOCOLS:
            valid_list = ", ".join(sorted(VALID_PROTOCOLS))
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(f"Invalid protocol '{v}': must be one of {valid_list}")
        # Validated via set membership check above
        return cast(ServiceProtocol, normalized)

    @field_validator("health_check_url", mode="before")
    @classmethod
    def validate_health_check_url(cls, v: str | None) -> str | None:
        """Validate that health_check_url is a valid HTTP(S) URL.

        Args:
            v: The URL string to validate, or None.

        Returns:
            The validated URL string, or None if input is None.

        Raises:
            ValueError: If the value is not a string or not a valid HTTP(S) URL.
        """
        if v is None:
            return None
        if not isinstance(v, str):
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(
                f"Health check URL must be a string, got {type(v).__name__}"
            )

        v = v.strip()
        if not v:
            return None

        parsed = urlparse(v)
        # Validate scheme
        if parsed.scheme not in ("http", "https"):
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(
                f"Invalid health check URL '{v}': scheme must be 'http' or 'https', "
                f"got '{parsed.scheme or '(empty)'}'"
            )
        # Validate netloc (host[:port])
        if not parsed.netloc:
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(f"Invalid health check URL '{v}': missing host")
        return v

    @field_validator("service_instance_id", mode="before")
    @classmethod
    def coerce_service_instance_id(cls, v: UUID | str | None) -> UUID | None:
        """Coerce string UUID values to UUID type.

        Accepts UUID objects directly or valid UUID string representations.

        Args:
            v: The service instance ID value, either as UUID, string, or None.

        Returns:
            The UUID value, or None if input is None.

        Raises:
            ValueError: If the string value is not a valid UUID format.
        """
        if v is None:
            return None
        if isinstance(v, UUID):
            return v
        if isinstance(v, str):
            try:
                return UUID(v)
            except ValueError:
                # error-ok: Pydantic field_validator requires ValueError
                raise ValueError(
                    f"Invalid UUID string for service_instance_id: '{v}'. "
                    f"Must be a valid UUID format (e.g., '550e8400-e29b-41d4-a716-446655440000')"
                ) from None
        # error-ok: Pydantic field_validator requires ValueError
        raise ValueError(
            f"service_instance_id must be UUID or str, got {type(v).__name__}"
        )

    @field_validator("service_version", mode="before")
    @classmethod
    def coerce_service_version(
        cls, v: ModelSemVer | str | dict[str, object] | None
    ) -> ModelSemVer | None:
        """Coerce string or dict values to ModelSemVer.

        Provides flexible input handling for service_version field:
        - String format "X.Y.Z" is parsed to ModelSemVer
        - Dict format {"major": X, "minor": Y, "patch": Z} is converted
        - ModelSemVer instances are passed through unchanged
        - None values are passed through unchanged

        Args:
            v: The service version value as ModelSemVer, string, dict, or None.

        Returns:
            The coerced ModelSemVer value, or None if input is None.

        Raises:
            ValueError: If string format is invalid, dict is malformed, or value
                is not ModelSemVer, str, dict, or None.

        Example:
            >>> metadata = ModelServiceDiscoveryMetadata(
            ...     service_name="test",
            ...     service_version="2.1.0"
            ... )
            >>> metadata.service_version
            ModelSemVer(major=2, minor=1, patch=0)
        """
        if v is None:
            return None
        if isinstance(v, ModelSemVer):
            return v
        if isinstance(v, str):
            # Use ModelSemVer.parse() for string parsing
            return ModelSemVer.parse(v)
        if isinstance(v, dict):
            # Allow dict format like {"major": 1, "minor": 2, "patch": 3}
            try:
                # Extract and validate required fields explicitly
                major = v.get("major")
                minor = v.get("minor")
                patch = v.get("patch")
                if (
                    not isinstance(major, int)
                    or not isinstance(minor, int)
                    or not isinstance(patch, int)
                ):
                    # error-ok: Pydantic field_validator requires ValueError
                    raise ValueError(
                        "Invalid service_version dict: major, minor, patch must be integers"
                    )
                return ModelSemVer(major=major, minor=minor, patch=patch)
            except (KeyError, TypeError, ValueError) as e:
                # error-ok: Pydantic field_validator requires ValueError
                raise ValueError(
                    f"Invalid service_version dict format: expected {{'major': int, "
                    f"'minor': int, 'patch': int}}, got {v}"
                ) from e
        # error-ok: Pydantic field_validator requires ValueError
        raise ValueError(f"Expected ModelSemVer, str, or dict, got {type(v).__name__}")
