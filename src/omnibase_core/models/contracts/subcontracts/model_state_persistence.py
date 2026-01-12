"""
State Persistence Model.

Individual model for state persistence configuration.
Part of the State Management Subcontract Model family.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.constants import TIMEOUT_LONG_MS
from omnibase_core.enums.enum_state_management import EnumStorageBackend
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelStatePersistence(BaseModel):
    """
    State persistence configuration.

    Defines state storage, backup, and recovery
    strategies for durable state management.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    persistence_enabled: bool = Field(
        default=True,
        description="Enable state persistence",
    )

    storage_backend: EnumStorageBackend = Field(
        default=EnumStorageBackend.POSTGRESQL,
        description="Backend storage system for state",
    )

    backup_enabled: bool = Field(
        default=True,
        description="Enable automatic state backups",
    )

    backup_interval_ms: int = Field(
        default=TIMEOUT_LONG_MS,
        description="Backup interval",
        ge=1000,
    )

    backup_retention_days: int = Field(
        default=7,
        description="Backup retention period",
        ge=1,
    )

    checkpoint_enabled: bool = Field(
        default=True,
        description="Enable state checkpointing",
    )

    checkpoint_interval_ms: int = Field(
        default=60000,
        description="Checkpoint interval",
        ge=1000,
    )

    recovery_enabled: bool = Field(
        default=True,
        description="Enable automatic state recovery",
    )

    compression_enabled: bool = Field(
        default=False,
        description="Enable state compression",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
