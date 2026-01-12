"""
Cache Distribution Model.

Model for distributed caching configuration in the ONEX caching system.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.constants import TIMEOUT_DEFAULT_MS
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelCacheDistribution(BaseModel):
    """
    Distributed caching configuration.

    Defines distributed cache behavior,
    synchronization, and consistency policies.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    distributed_enabled: bool = Field(
        default=False,
        description="Enable distributed caching",
    )

    consistency_level: str = Field(
        default="eventual",
        description="Consistency level for distributed cache",
    )

    replication_factor: int = Field(
        default=2,
        description="Number of cache replicas",
        ge=1,
    )

    partition_strategy: str = Field(
        default="consistent_hash",
        description="Partitioning strategy for distribution",
    )

    sync_interval_ms: int = Field(
        default=TIMEOUT_DEFAULT_MS,
        description="Synchronization interval",
        ge=1000,
    )

    conflict_resolution: str = Field(
        default="last_writer_wins",
        description="Conflict resolution strategy",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
