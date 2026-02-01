"""
Backup Configuration Model.

Defines backup creation, storage, and rollback procedures
for safe side-effect operations with recovery capabilities.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelBackupConfig(BaseModel):
    """
    Backup and rollback strategies.

    Defines backup creation, storage, and rollback procedures
    for safe side-effect operations with recovery capabilities.
    """

    enabled: bool = Field(default=True, description="Enable backup creation")

    backup_location: str = Field(
        default="./backups",
        description="Backup storage location",
    )

    retention_days: int = Field(
        default=7,
        description="Backup retention period in days",
        ge=1,
    )

    compression_enabled: bool = Field(
        default=True,
        description="Enable backup compression",
    )

    verification_enabled: bool = Field(
        default=True,
        description="Enable backup verification after creation",
    )

    rollback_timeout_s: int = Field(
        default=120,
        description="Maximum rollback operation time in seconds",
        ge=1,
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )


__all__ = ["ModelBackupConfig"]
