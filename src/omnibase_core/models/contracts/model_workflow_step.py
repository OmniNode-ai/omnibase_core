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

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.constants import TIMEOUT_DEFAULT_MS, TIMEOUT_LONG_MS
from omnibase_core.constants.constants_field_limits import (
    MAX_IDENTIFIER_LENGTH,
    MAX_NAME_LENGTH,
)
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.validation.validator_workflow_constants import (
    MIN_TIMEOUT_MS,
    VALID_STEP_TYPES,
)

__all__ = ["ModelWorkflowStep", "VALID_STEP_TYPES"]


class ModelWorkflowStep(BaseModel):
    """
    Strongly-typed workflow step definition.

    Replaces dict[str, str | int | bool] patterns with proper Pydantic model
    providing runtime validation and type safety for workflow execution.

    Strict typing is enforced: No Any types or dict[str, Any] patterns allowed.

    Thread Safety:
        This model is frozen (frozen=True), making it fully immutable and safe
        to share across threads without synchronization. All fields are read-only
        after construction. To "modify" a step, create a new instance using
        `model_copy(update={...})`.

    v1.0.4 Compliance:
        step_type MUST be one of: compute, effect, reducer, orchestrator, custom,
        parallel. The "conditional" type is reserved for v1.1+ and MUST NOT be
        accepted in v1.0.x. See: validator_workflow_constants.VALID_STEP_TYPES
    """

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        frozen=True,
        use_enum_values=False,
    )

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
        max_length=MAX_NAME_LENGTH,
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

        INTENTIONAL REDUNDANCY NOTE (v1.0.4 Compliance):
        While Pydantic's Literal type already enforces valid values at the type level,
        this validator is intentionally retained to provide:
        1. Explicit ONEX-specific error codes (ORCHESTRATOR_STRUCT_INVALID_STEP_TYPE)
        2. User-friendly error messages referencing v1.0.4 normative spec
        3. Clear guidance that 'conditional' is reserved for v1.1+
        This redundancy is by design for improved developer experience.
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
    # DESIGN DECISION: Workflow step timeout is capped at TIMEOUT_LONG_MS (5 minutes)
    # rather than MAX_TIMEOUT_MS (24 hours). Rationale:
    # 1. Individual workflow steps should complete within bounded time
    # 2. Long-running operations (>5 min) should be async or broken into smaller steps
    # 3. This prevents single steps from blocking entire workflow pipelines
    # 4. MAX_TIMEOUT_MS (24 hours) is for aggregate workflow duration, not per-step
    #
    # TIMEOUT HIERARCHY (cross-reference):
    # - Step timeout: Capped at TIMEOUT_LONG_MS (5 min) - this field
    #   See: omnibase_core/constants/constants_timeouts.py
    # - Event timeout: Capped at MAX_TIMEOUT_MS (24 hours) - for longer operations
    #   See: omnibase_core/models/core/model_event_input_state.py
    # - Workflow global timeout: Configured in ModelWorkflowMetadata.timeout_ms
    #   See: omnibase_core/validation/validator_workflow_constants.py
    timeout_ms: int = Field(
        default=TIMEOUT_DEFAULT_MS,
        description=(
            "Step execution timeout in milliseconds. "
            "Min: 100ms (prevents unrealistic timeouts), Max: 5 minutes "
            "(TIMEOUT_LONG_MS - individual steps should complete quickly; "
            "longer operations should use async patterns)."
        ),
        ge=MIN_TIMEOUT_MS,  # Min 100ms per v1.0.3 normative constraint
        le=TIMEOUT_LONG_MS,  # Max 5 minutes (per-step limit, NOT 24-hour aggregate limit)
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
    # IMPORTANT: In v1.0, priority is INFORMATIONAL ONLY and does NOT affect execution
    # order. Steps execute in declaration order. Priority-based scheduling is planned
    # for v1.1+. This field exists for forward compatibility and documentation.
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
        max_length=MAX_IDENTIFIER_LENGTH,
    )

    max_parallel_instances: int = Field(
        default=1,
        description="Maximum parallel instances of this step",
        ge=1,
        le=100,
    )

    # step_id validation is now handled by UUID type - no custom validation needed

    # depends_on validation is now handled by UUID type - no custom validation needed
