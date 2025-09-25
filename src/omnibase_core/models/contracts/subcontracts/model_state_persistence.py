#!/usr/bin/env python3
"""
State Persistence Model - ONEX Standards Compliant.

Individual model for state persistence configuration.
Part of the State Management Subcontract Model family.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_state_management import EnumStorageBackend


class ModelStatePersistence(BaseModel):
    """
    State persistence configuration.

    Defines state storage, backup, and recovery
    strategies for durable state management.
    """

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
        default=300000,
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
