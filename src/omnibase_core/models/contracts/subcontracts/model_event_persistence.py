"""
Event Persistence Model.

Model for event persistence configuration in the ONEX event-driven architecture system.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.constants import TIMEOUT_LONG_MS
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelEventPersistence(BaseModel):
    """
    Event persistence configuration.

    Defines event storage, replay capabilities,
    and historical event management policies.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    persistence_enabled: bool = Field(
        default=True,
        description="Whether events should be persisted",
    )

    storage_backend: str = Field(
        default="memory",
        description="Backend storage system for events",
    )

    retention_policy: str = Field(
        default="time_based",
        description="Retention policy for stored events",
    )

    retention_days: int = Field(
        default=30,
        description="Number of days to retain events",
        ge=1,
    )

    replay_enabled: bool = Field(
        default=True,
        description="Whether event replay is supported",
    )

    snapshot_interval_ms: int = Field(
        default=TIMEOUT_LONG_MS,
        description="Interval for event snapshots",
        ge=1000,
    )

    compression_enabled: bool = Field(
        default=True,
        description="Enable compression for stored events",
    )

    encryption_enabled: bool = Field(
        default=False,
        description="Enable encryption for stored events",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
        from_attributes=True,
    )
