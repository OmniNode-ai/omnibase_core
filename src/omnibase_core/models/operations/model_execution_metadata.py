"""
Strongly-typed execution metadata structure.

Replaces dict[str, Any] usage in execution metadata with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_environment import EnumEnvironment
from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import (
    ModelSemVer,
    default_model_version,
)

__all__ = ["ModelExecutionMetadata"]


class ModelExecutionMetadata(BaseModel):
    """
    Strongly-typed execution metadata.

    Replaces dict[str, Any] with structured metadata model.

    Implements Core protocols:
    - Executable: Execution management capabilities
    - Identifiable: UUID-based identification
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    execution_id: UUID = Field(
        default_factory=uuid4,
        description="Unique execution identifier (UUID format)",
    )
    start_time: datetime = Field(default=..., description="Execution start timestamp")
    end_time: datetime | None = Field(
        default=None, description="Execution end timestamp"
    )
    duration_ms: int = Field(
        default=0,
        ge=0,
        description="Execution duration in milliseconds",
    )
    status: EnumExecutionStatus = Field(
        default=EnumExecutionStatus.PENDING,
        description="Execution status",
    )
    correlation_id: UUID | None = Field(
        default=None,
        description="Request correlation ID (UUID format)",
    )

    # Environment information
    environment: EnumEnvironment = Field(
        default=EnumEnvironment.DEVELOPMENT,
        description="Execution environment",
    )
    version: ModelSemVer = Field(
        default_factory=default_model_version,
        description="System version in semantic version format",
    )
    node_id: UUID | None = Field(
        default=None,
        description="Executing node identifier (UUID format)",
    )

    # Resource usage
    memory_usage_mb: float = Field(default=0.0, description="Memory usage in MB")
    cpu_usage_percent: float = Field(default=0.0, description="CPU usage percentage")

    # Error information
    error_level_count: int = Field(
        default=0, ge=0, description="Number of errors encountered"
    )
    warning_count: int = Field(
        default=0, ge=0, description="Number of warnings encountered"
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Input validation for proper enum types
    @field_validator("status", mode="before")
    @classmethod
    def validate_status_type(cls, v: Any) -> EnumExecutionStatus:
        """Validate execution status is proper enum type."""
        if isinstance(v, EnumExecutionStatus):
            return v
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Status must be EnumExecutionStatus, got {type(v)}",
        )

    @field_validator("environment", mode="before")
    @classmethod
    def validate_environment_type(cls, v: Any) -> EnumEnvironment:
        """Validate environment is proper enum type."""
        if isinstance(v, EnumEnvironment):
            return v
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Environment must be EnumEnvironment, got {type(v)}",
        )

    # Protocol method implementations

    def get_id(self) -> str:
        """Get execution identifier (Identifiable protocol)."""
        return str(self.execution_id)

    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update execution status and metadata
            if "status" in kwargs:
                status_value = kwargs["status"]
                if isinstance(status_value, EnumExecutionStatus):
                    self.status = status_value
                else:
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        message=f"Status must be EnumExecutionStatus, got {type(status_value)}",
                    )
            if "end_time" in kwargs:
                end_time_value = kwargs["end_time"]
                if isinstance(end_time_value, datetime):
                    self.end_time = end_time_value
                    if self.start_time and self.end_time:
                        self.duration_ms = int(
                            (self.end_time - self.start_time).total_seconds() * 1000,
                        )
            # Update resource usage if provided
            if "memory_usage_mb" in kwargs:
                memory_value = kwargs["memory_usage_mb"]
                if isinstance(memory_value, (int, float)):
                    self.memory_usage_mb = float(memory_value)
            if "cpu_usage_percent" in kwargs:
                cpu_value = kwargs["cpu_usage_percent"]
                if isinstance(cpu_value, (int, float)):
                    self.cpu_usage_percent = float(cpu_value)
            return True
        except ModelOnexError:
            # Re-raise ModelOnexError as-is to preserve error context
            raise
        except PYDANTIC_MODEL_ERRORS as e:
            # fallback-ok: Converts specific exceptions to structured ModelOnexError.
            # PYDANTIC_MODEL_ERRORS covers AttributeError, TypeError, ValidationError, ValueError
            # which are raised by setattr with Pydantic validate_assignment=True.
            raise ModelOnexError(
                message=f"Failed to execute metadata update: {e}",
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
            ) from e

    def serialize(self) -> dict[str, object]:
        """Serialize execution metadata to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate execution metadata integrity (ProtocolValidatable protocol).

        Raises:
            OnexError: If validation fails with invalid field values
            Exception: If validation logic fails
        """
        # Validate required fields
        if not self.execution_id:
            raise ModelOnexError(
                message="execution_id is required",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        if not self.start_time:
            raise ModelOnexError(
                message="start_time is required",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        # Validate logical consistency
        if self.end_time and self.end_time < self.start_time:
            raise ModelOnexError(
                message="end_time cannot be before start_time",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        if self.duration_ms < 0:
            raise ModelOnexError(
                message="duration_ms cannot be negative",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        if self.memory_usage_mb < 0 or self.cpu_usage_percent < 0:
            raise ModelOnexError(
                message="Resource usage values cannot be negative",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        if self.error_level_count < 0 or self.warning_count < 0:
            raise ModelOnexError(
                message="Error and warning counts cannot be negative",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return True
