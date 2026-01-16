"""
Node initialization metadata model for startup tracking.

This module provides ModelNodeInitMetadata, a typed model for node
initialization metadata that replaces untyped dict[str, str] fields. It
captures initialization source, timing, configuration, and feature flags.

Thread Safety:
    ModelNodeInitMetadata is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access from multiple threads or async tasks.

See Also:
    - omnibase_core.models.context.model_checkpoint_metadata: Checkpoint metadata
    - omnibase_core.nodes: Node base classes
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ["ModelNodeInitMetadata"]


class ModelNodeInitMetadata(BaseModel):
    """Node initialization metadata.

    Provides typed metadata for node initialization tracking. Supports
    debugging node startup issues, configuration drift detection, and
    feature flag management.

    Attributes:
        init_source: Source that triggered node initialization
            (e.g., "container", "test_fixture", "hot_reload", "manual").
        init_timestamp: ISO 8601 timestamp of initialization completion.
            Used for startup timing analysis and performance monitoring.
        config_hash: Hash of the configuration used for initialization.
            Enables configuration drift detection between restarts.
        dependency_versions: Serialized dependency version information
            (e.g., JSON object with package versions).
        feature_flags: Comma-separated list of enabled feature flags
            at initialization time.

    Thread Safety:
        This model is frozen and immutable after creation.
        Safe for concurrent read access across threads.

    Example:
        >>> from omnibase_core.models.context import ModelNodeInitMetadata
        >>>
        >>> init_meta = ModelNodeInitMetadata(
        ...     init_source="container",
        ...     init_timestamp="2025-01-15T10:30:00Z",
        ...     config_hash="sha256:abc123def456",
        ...     dependency_versions='{"pydantic": "2.11.0", "fastapi": "0.120.0"}',
        ...     feature_flags="experimental_caching,async_processing",
        ... )
        >>> init_meta.init_source
        'container'
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    init_source: str | None = Field(
        default=None,
        description="Initialization source",
    )
    init_timestamp: str | None = Field(
        default=None,
        description="Initialization timestamp",
    )
    config_hash: str | None = Field(
        default=None,
        description="Configuration hash",
    )
    dependency_versions: str | None = Field(
        default=None,
        description="Dependency versions",
    )
    feature_flags: str | None = Field(
        default=None,
        description="Enabled feature flags",
    )

    @field_validator("init_timestamp", mode="before")
    @classmethod
    def validate_init_timestamp_iso8601(cls, value: str | None) -> str | None:
        """Validate init_timestamp is in ISO 8601 format.

        Args:
            value: The init_timestamp string or None.

        Returns:
            The validated timestamp string unchanged, or None.

        Raises:
            ValueError: If the value is not a string or not valid ISO 8601 format.
        """
        if value is None:
            return None
        if not isinstance(value, str):
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(
                f"init_timestamp must be a string, got {type(value).__name__}"
            )
        try:
            # Python 3.11+ fromisoformat handles 'Z' suffix
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as e:
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(
                f"Invalid ISO 8601 timestamp for init_timestamp: {value}"
            ) from e
        return value
