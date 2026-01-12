"""
Cache Invalidation Model.

Model for cache invalidation policies in the ONEX caching system.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelCacheInvalidation(BaseModel):
    """
    Cache invalidation policy.

    Defines cache invalidation strategies,
    triggers, and cleanup policies.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    invalidation_strategy: str = Field(
        default=...,
        description="Strategy for cache invalidation",
        min_length=1,
    )

    ttl_seconds: int = Field(
        default=300,
        description="Time-to-live for cache entries",
        ge=1,
    )

    max_idle_seconds: int = Field(
        default=600,
        description="Maximum idle time before invalidation",
        ge=1,
    )

    invalidation_triggers: list[str] = Field(
        default_factory=list,
        description="Events that trigger cache invalidation",
    )

    batch_invalidation: bool = Field(
        default=False,
        description="Enable batch invalidation for efficiency",
    )

    lazy_expiration: bool = Field(
        default=True,
        description="Use lazy expiration to reduce overhead",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
