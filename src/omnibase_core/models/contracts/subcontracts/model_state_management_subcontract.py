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

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_state_management import (
    EnumEncryptionAlgorithm,
    EnumIsolationLevel,
    EnumLockingStrategy,
    EnumStateLifecycle,
    EnumStateScope,
)
from omnibase_core.exceptions.onex_error import OnexError
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

from .model_state_persistence import ModelStatePersistence
from .model_state_synchronization import ModelStateSynchronization
from .model_state_validation import ModelStateValidation
from .model_state_versioning import ModelStateVersioning


class ModelStateManagementSubcontract(BaseModel):
    """
    State Management subcontract model for state handling functionality.

    Comprehensive state management subcontract providing persistence,
    validation, synchronization, and versioning capabilities.
    Designed for composition into node contracts requiring state management.

    ZERO TOLERANCE: No Any types allowed in implementation.
    """

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,
    )

    # Correlation and tracing
    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="Unique correlation ID for state management operations",
    )

    # Core state management configuration
    state_management_enabled: bool = Field(
        default=True,
        description="Enable state management functionality",
    )

    state_scope: EnumStateScope = Field(
        default=EnumStateScope.NODE_LOCAL,
        description="Scope of state management",
    )

    state_lifecycle: EnumStateLifecycle = Field(
        default=EnumStateLifecycle.PERSISTENT,
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

    locking_strategy: EnumLockingStrategy = Field(
        default=EnumLockingStrategy.OPTIMISTIC,
        description="Locking strategy for state access",
    )

    transaction_support: bool = Field(
        default=True,
        description="Enable transactional state operations",
    )

    isolation_level: EnumIsolationLevel = Field(
        default=EnumIsolationLevel.READ_COMMITTED,
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

    encryption_algorithm: EnumEncryptionAlgorithm = Field(
        default=EnumEncryptionAlgorithm.AES256,
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
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("valueerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "model_validation",
                            ),
                        },
                    ),
                )
        return v

    @field_validator("cleanup_interval_ms")
    @classmethod
    def validate_cleanup_interval(cls, v: int, info: ValidationInfo) -> int:
        """Validate cleanup interval when cleanup is enabled."""
        if info.data and info.data.get("cleanup_enabled", True):
            if v < 60000:  # 1 minute minimum
                msg = "cleanup_interval_ms must be at least 60000ms (1 minute)"
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("valueerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "model_validation",
                            ),
                        },
                    ),
                )
        return v
