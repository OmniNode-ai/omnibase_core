"""
Strongly-typed execution metadata structure.

Replaces dict[str, Any] usage in execution metadata with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from omnibase_core.core.decorators import allow_dict_str_any
from omnibase_core.core.type_constraints import (
    Executable,
    Identifiable,
    Serializable,
    Validatable,
)
from omnibase_core.enums.enum_environment import EnumEnvironment
from omnibase_core.enums.enum_execution_status_v2 import EnumExecutionStatusV2
from omnibase_core.models.metadata.model_semver import (
    ModelSemVer,
    parse_semver_from_string,
)


class ModelExecutionMetadata(BaseModel):
    """
    Strongly-typed execution metadata.

    Replaces dict[str, Any] with structured metadata model.

    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Identifiable: UUID-based identification
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    execution_id: UUID = Field(
        default_factory=uuid4, description="Unique execution identifier (UUID format)"
    )
    start_time: datetime = Field(..., description="Execution start timestamp")
    end_time: datetime | None = Field(None, description="Execution end timestamp")
    duration_ms: int = Field(
        default=0, description="Execution duration in milliseconds"
    )
    status: EnumExecutionStatusV2 = Field(
        default=EnumExecutionStatusV2.PENDING, description="Execution status"
    )
    correlation_id: UUID | None = Field(
        default=None, description="Request correlation ID (UUID format)"
    )

    # Environment information
    environment: EnumEnvironment = Field(
        default=EnumEnvironment.DEVELOPMENT, description="Execution environment"
    )
    version: ModelSemVer = Field(
        default=ModelSemVer(major=1, minor=0, patch=0),
        description="System version in semantic version format",
    )
    node_id: UUID | None = Field(
        default=None, description="Executing node identifier (UUID format)"
    )

    # Resource usage
    memory_usage_mb: float = Field(default=0.0, description="Memory usage in MB")
    cpu_usage_percent: float = Field(default=0.0, description="CPU usage percentage")

    # Error information
    error_count: int = Field(default=0, description="Number of errors encountered")
    warning_count: int = Field(default=0, description="Number of warnings encountered")

    # Input validation for proper enum types
    @field_validator("status", mode="before")
    @classmethod
    def validate_status_type(cls, v: Any) -> EnumExecutionStatusV2:
        """Validate execution status is proper enum type."""
        if isinstance(v, EnumExecutionStatusV2):
            return v
        raise ValueError(f"Status must be EnumExecutionStatusV2, got {type(v)}")

    @field_validator("environment", mode="before")
    @classmethod
    def validate_environment_type(cls, v: Any) -> EnumEnvironment:
        """Validate environment is proper enum type."""
        if isinstance(v, EnumEnvironment):
            return v
        raise ValueError(f"Environment must be EnumEnvironment, got {type(v)}")

    # Protocol method implementations

    def get_id(self) -> str:
        """Get execution identifier (Identifiable protocol)."""
        return str(self.execution_id)

    def execute(self, **kwargs: Any) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update execution status and metadata
            if "status" in kwargs:
                status_value = kwargs["status"]
                if isinstance(status_value, EnumExecutionStatusV2):
                    self.status = status_value
                else:
                    raise ValueError(
                        f"Status must be EnumExecutionStatusV2, got {type(status_value)}"
                    )
            if "end_time" in kwargs:
                self.end_time = kwargs["end_time"]
                if self.start_time and self.end_time:
                    self.duration_ms = int(
                        (self.end_time - self.start_time).total_seconds() * 1000
                    )
            # Update resource usage if provided
            if "memory_usage_mb" in kwargs:
                self.memory_usage_mb = kwargs["memory_usage_mb"]
            if "cpu_usage_percent" in kwargs:
                self.cpu_usage_percent = kwargs["cpu_usage_percent"]
            return True
        except Exception:
            return False

    def serialize(self) -> dict[str, Any]:
        """Serialize execution metadata to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate execution metadata integrity (Validatable protocol)."""
        try:
            # Validate required fields
            if not self.execution_id:
                return False
            if not self.start_time:
                return False
            # Validate logical consistency
            if self.end_time and self.end_time < self.start_time:
                return False
            if self.duration_ms < 0:
                return False
            if self.memory_usage_mb < 0 or self.cpu_usage_percent < 0:
                return False
            if self.error_count < 0 or self.warning_count < 0:
                return False
            return True
        except Exception:
            return False


# Export for use
__all__ = ["ModelExecutionMetadata"]
