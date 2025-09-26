"""
Strongly-typed execution metadata structure.

Replaces dict[str, Any] usage in execution metadata with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.core.decorators import allow_dict_str_any
from omnibase_core.models.metadata.model_semver import (
    ModelSemVer,
    parse_semver_from_string,
)


class ModelExecutionMetadata(BaseModel):
    """
    Strongly-typed execution metadata.

    Replaces dict[str, Any] with structured metadata model.
    """

    execution_id: UUID = Field(
        default_factory=uuid4, description="Unique execution identifier (UUID format)"
    )
    start_time: datetime = Field(..., description="Execution start timestamp")
    end_time: datetime | None = Field(None, description="Execution end timestamp")
    duration_ms: int = Field(
        default=0, description="Execution duration in milliseconds"
    )
    status: str = Field(default="pending", description="Execution status")
    correlation_id: UUID | None = Field(
        default=None, description="Request correlation ID (UUID format)"
    )

    # Environment information
    environment: str = Field(default="development", description="Execution environment")
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


# Export for use
__all__ = ["ModelExecutionMetadata"]
