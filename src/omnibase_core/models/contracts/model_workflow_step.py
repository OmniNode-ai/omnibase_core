"""
Workflow Step Model.

Strongly-typed workflow step model that replaces dict[str, str | int | bool] patterns
with proper Pydantic validation and type safety.

Strict typing is enforced: No Any types or dict[str, Any]patterns allowed.
"""

from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

__all__ = ["ModelWorkflowStep"]


class ModelWorkflowStep(BaseModel):
    """
    Strongly-typed workflow step definition.

    Replaces dict[str, str | int | bool] patterns with proper Pydantic model
    providing runtime validation and type safety for workflow execution.

    Strict typing is enforced: No Any types or dict[str, Any]patterns allowed.
    """

    model_config = {
        "extra": "forbid",
        "use_enum_values": False,
        "validate_assignment": True,
        "frozen": True,
    }

    # ONEX correlation tracking
    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="UUID for tracking workflow step across operations",
    )

    step_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this workflow step",
    )

    step_name: str = Field(
        default=...,
        description="Human-readable name for this step",
        min_length=1,
        max_length=200,
    )

    step_type: Literal[
        "compute",
        "effect",
        "reducer",
        "orchestrator",
        "conditional",
        "parallel",
        "custom",
    ] = Field(
        default=...,
        description="Type of workflow step execution",
    )

    # Execution configuration
    timeout_ms: int = Field(
        default=30000,
        description="Step execution timeout in milliseconds",
        ge=100,
        le=300000,  # Max 5 minutes
    )

    retry_count: int = Field(
        default=3,
        description="Number of retry attempts on failure",
        ge=0,
        le=10,
    )

    # Conditional execution
    enabled: bool = Field(
        default=True,
        description="Whether this step is enabled for execution",
    )

    skip_on_failure: bool = Field(
        default=False,
        description="Whether to skip this step if previous steps failed",
    )

    # Error handling
    continue_on_error: bool = Field(
        default=False,
        description="Whether to continue workflow if this step fails",
    )

    error_action: Literal["stop", "continue", "retry", "compensate"] = Field(
        default="stop",
        description="Action to take when step fails",
    )

    # Performance requirements
    max_memory_mb: int | None = Field(
        default=None,
        description="Maximum memory usage in megabytes",
        ge=1,
        le=32768,  # Max 32GB
    )

    max_cpu_percent: int | None = Field(
        default=None,
        description="Maximum CPU usage percentage",
        ge=1,
        le=100,
    )

    # Priority and ordering
    # NOTE: Priority uses standard heap/queue semantics where lower values execute first.
    # This matches Python's heapq and typical task queue implementations.
    priority: int = Field(
        default=100,
        description="Step execution priority (lower = higher priority, executes first)",
        ge=1,
        le=1000,
    )

    order_index: int = Field(
        default=0,
        description="Order index for step execution sequence",
        ge=0,
    )

    # Dependencies
    depends_on: list[UUID] = Field(
        default_factory=list,
        description="List of step IDs this step depends on",
    )

    # Parallel execution
    parallel_group: str | None = Field(
        default=None,
        description="Group identifier for parallel execution",
        max_length=100,
    )

    max_parallel_instances: int = Field(
        default=1,
        description="Maximum parallel instances of this step",
        ge=1,
        le=100,
    )

    # step_id validation is now handled by UUID type - no custom validation needed

    # depends_on validation is now handled by UUID type - no custom validation needed
