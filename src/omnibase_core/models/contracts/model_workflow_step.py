"""
Workflow Step Model.

Strongly-typed workflow step model that replaces dict[str, str | int | bool] patterns
with proper Pydantic validation and type safety.

Strict typing is enforced: No Any types or dict[str, Any]patterns allowed.

v1.0.4 Compliance (Fix 41): step_type MUST be one of: compute, effect, reducer,
orchestrator, custom, parallel. Any other value raises ModelOnexError at validation.
"""

from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.validation.workflow_constants import VALID_STEP_TYPES

__all__ = ["ModelWorkflowStep", "VALID_STEP_TYPES"]


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

    # v1.0.4 Normative (Fix 41): step_type MUST be one of the valid types.
    # "conditional" is reserved for v1.1+ and MUST NOT be accepted.
    step_type: Literal[
        "compute",
        "effect",
        "reducer",
        "orchestrator",
        "parallel",
        "custom",
    ] = Field(
        default=...,
        description="Type of workflow step execution (Fix 41: conditional is NOT valid)",
    )

    @field_validator("step_type", mode="after")
    @classmethod
    def validate_step_type(cls, v: str) -> str:
        """
        Validate step_type against v1.0.4 normative rules.

        Fix 41: step_type MUST be one of: compute, effect, reducer, orchestrator,
        custom, parallel. Any other value MUST raise ModelOnexError.

        Note: Pydantic's Literal type already enforces this at the type level,
        but this validator provides explicit error messaging for v1.0.4 compliance.
        """
        if v not in VALID_STEP_TYPES:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.ORCHESTRATOR_STRUCT_INVALID_STEP_TYPE,
                message=(
                    f"Invalid step_type '{v}'. v1.0.4 requires one of: "
                    f"{', '.join(sorted(VALID_STEP_TYPES))}. "
                    "'conditional' is reserved for v1.1+."
                ),
                step_type=v,
                valid_types=sorted(VALID_STEP_TYPES),
            )
        return v

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
    # v1.0.4 Fix 43: error_action controls behavior exclusively. continue_on_error
    # is advisory in v1.0 and MUST NOT override error_action.
    continue_on_error: bool = Field(
        default=False,
        description=(
            "Advisory flag for workflow continuation on failure. "
            "v1.0.4 (Fix 43): This is advisory ONLY - error_action controls "
            "execution behavior exclusively."
        ),
    )

    error_action: Literal["stop", "continue", "retry", "compensate"] = Field(
        default="stop",
        description=(
            "Action to take when step fails. v1.0.4 (Fix 43): This field controls "
            "error handling exclusively. continue_on_error is advisory only."
        ),
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
        description=(
            "Used to derive action priority on the queue; does not affect DAG "
            "topological order. Lower values = higher priority. Declaration order "
            "is the tiebreaker for steps at the same dependency level."
        ),
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
    # v1.0.4 Fix 42: parallel_group is a pure opaque label. No prefix, suffix,
    # numeric pattern, or hierarchy interpretation is allowed. Only strict
    # string equality may be used for comparison.
    parallel_group: str | None = Field(
        default=None,
        description=(
            "Group identifier for parallel execution. v1.0.4 (Fix 42): This is an "
            "opaque label - no pattern interpretation is performed. Only strict "
            "string equality is used for comparison."
        ),
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
