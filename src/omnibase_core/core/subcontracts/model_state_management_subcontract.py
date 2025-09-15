#!/usr/bin/env python3
"""
State Management Subcontract Model - ONEX Standards Compliant.

Dedicated subcontract model for state management functionality providing:
- State persistence and recovery strategies
- State synchronization and consistency policies
- State validation and integrity checks
- State versioning and migration support
- State monitoring and metrics

This model is composed into node contracts that require state management,
providing clean separation between node logic and state handling behavior.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from pydantic import BaseModel, Field, ValidationInfo, field_validator


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

    storage_backend: str = Field(
        default="postgresql",
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


class ModelStateValidation(BaseModel):
    """
    State validation configuration.

    Defines validation rules, integrity checks,
    and consistency verification for state data.
    """

    validation_enabled: bool = Field(
        default=True,
        description="Enable state validation",
    )

    schema_validation: bool = Field(
        default=True,
        description="Enable schema validation for state",
    )

    integrity_checks: bool = Field(default=True, description="Enable integrity checks")

    consistency_checks: bool = Field(
        default=False,
        description="Enable consistency validation",
    )

    validation_rules: list[str] = Field(
        default_factory=list,
        description="Custom validation rules",
    )

    repair_enabled: bool = Field(
        default=False,
        description="Enable automatic state repair",
    )

    repair_strategies: list[str] = Field(
        default_factory=list,
        description="Available repair strategies",
    )


class ModelStateSynchronization(BaseModel):
    """
    State synchronization configuration.

    Defines synchronization policies for distributed
    state management and consistency guarantees.
    """

    synchronization_enabled: bool = Field(
        default=False,
        description="Enable state synchronization",
    )

    consistency_level: str = Field(
        default="eventual",
        description="Consistency level for distributed state",
    )

    sync_interval_ms: int = Field(
        default=30000,
        description="Synchronization interval",
        ge=1000,
    )

    conflict_resolution: str = Field(
        default="timestamp_based",
        description="Conflict resolution strategy",
    )

    replication_factor: int = Field(
        default=1,
        description="Number of state replicas",
        ge=1,
    )

    leader_election_enabled: bool = Field(
        default=False,
        description="Enable leader election for coordination",
    )

    distributed_locking: bool = Field(
        default=False,
        description="Enable distributed locking for state access",
    )


class ModelStateVersioning(BaseModel):
    """
    State versioning and migration configuration.

    Defines versioning policies, migration strategies,
    and state transition handling.
    """

    versioning_enabled: bool = Field(
        default=True,
        description="Enable state versioning",
    )

    version_scheme: str = Field(
        default="semantic",
        description="Versioning scheme for state",
    )

    migration_enabled: bool = Field(default=True, description="Enable state migration")

    migration_strategies: list[str] = Field(
        default_factory=list,
        description="Available migration strategies",
    )

    forward_compatibility: bool = Field(
        default=True,
        description="Maintain forward state compatibility",
    )

    version_retention: int = Field(
        default=5,
        description="Number of state versions to retain",
        ge=1,
    )

    rollback_enabled: bool = Field(
        default=True,
        description="Enable state rollback to previous versions",
    )


class ModelStateManagementSubcontract(BaseModel):
    """
    State Management subcontract model for state handling functionality.

    Comprehensive state management subcontract providing persistence,
    validation, synchronization, and versioning capabilities.
    Designed for composition into node contracts requiring state management.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    # Core state management configuration
    state_management_enabled: bool = Field(
        default=True,
        description="Enable state management functionality",
    )

    state_scope: str = Field(
        default="node_local",
        description="Scope of state management",
    )

    state_lifecycle: str = Field(
        default="persistent",
        description="State lifecycle management strategy",
    )

    # State persistence configuration
    persistence: ModelStatePersistence = Field(
        default_factory=ModelStatePersistence,
        description="State persistence configuration",
    )

    # State validation configuration
    validation: ModelStateValidation = Field(
        default_factory=ModelStateValidation,
        description="State validation configuration",
    )

    # State synchronization (for distributed scenarios)
    synchronization: ModelStateSynchronization | None = Field(
        default=None,
        description="State synchronization configuration",
    )

    # State versioning and migration
    versioning: ModelStateVersioning = Field(
        default_factory=ModelStateVersioning,
        description="State versioning configuration",
    )

    # State access and concurrency
    concurrent_access_enabled: bool = Field(
        default=True,
        description="Enable concurrent state access",
    )

    locking_strategy: str = Field(
        default="optimistic",
        description="Locking strategy for state access",
    )

    transaction_support: bool = Field(
        default=True,
        description="Enable transactional state operations",
    )

    isolation_level: str = Field(
        default="read_committed",
        description="Transaction isolation level",
    )

    # State caching and performance
    caching_enabled: bool = Field(default=True, description="Enable state caching")

    cache_size: int = Field(
        default=1000,
        description="Maximum cached state entries",
        ge=1,
    )

    cache_ttl_seconds: int = Field(default=300, description="Cache time-to-live", ge=1)

    lazy_loading: bool = Field(default=True, description="Enable lazy loading of state")

    # State monitoring and metrics
    monitoring_enabled: bool = Field(
        default=True,
        description="Enable state monitoring",
    )

    metrics_collection: bool = Field(
        default=True,
        description="Enable state metrics collection",
    )

    performance_tracking: bool = Field(
        default=False,
        description="Enable detailed performance tracking",
    )

    alert_on_corruption: bool = Field(
        default=True,
        description="Alert on state corruption detection",
    )

    # State security and encryption
    encryption_enabled: bool = Field(
        default=False,
        description="Enable state encryption at rest",
    )

    encryption_algorithm: str = Field(
        default="aes256",
        description="Encryption algorithm for state data",
    )

    key_rotation_enabled: bool = Field(
        default=False,
        description="Enable encryption key rotation",
    )

    access_control_enabled: bool = Field(
        default=False,
        description="Enable access control for state operations",
    )

    # State cleanup and maintenance
    cleanup_enabled: bool = Field(
        default=True,
        description="Enable automatic state cleanup",
    )

    cleanup_interval_ms: int = Field(
        default=3600000,
        description="Cleanup interval",
        ge=60000,
    )

    orphan_cleanup: bool = Field(
        default=True,
        description="Enable cleanup of orphaned state",
    )

    compaction_enabled: bool = Field(
        default=False,
        description="Enable state compaction",
    )

    @field_validator("cache_size")
    @classmethod
    def validate_cache_size(cls, v: int, info: ValidationInfo) -> int:
        """Validate cache size when caching is enabled."""
        if info.data and info.data.get("caching_enabled", True):
            if v < 10:
                msg = "cache_size must be at least 10 when caching is enabled"
                raise ValueError(
                    msg,
                )
        return v

    @field_validator("cleanup_interval_ms")
    @classmethod
    def validate_cleanup_interval(cls, v: int, info: ValidationInfo) -> int:
        """Validate cleanup interval when cleanup is enabled."""
        if info.data and info.data.get("cleanup_enabled", True):
            if v < 60000:  # 1 minute minimum
                msg = "cleanup_interval_ms must be at least 60000ms (1 minute)"
                raise ValueError(
                    msg,
                )
        return v

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        extra = "ignore"  # Allow extra fields from YAML contracts
        use_enum_values = False  # Keep enum objects, don't convert to strings
        validate_assignment = True
