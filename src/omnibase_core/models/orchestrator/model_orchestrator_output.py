"""
Orchestrator Output Model

Type-safe orchestrator output that replaces Dict[str, Any] usage
in orchestrator results.

Option A Semantic Model (OMN-941):
    ORCHESTRATOR nodes emit domain decision events and intents for desired effects.
    The runtime translates intents to internal directives.

    Allowed emissions:
        - events[]: Domain decision events (facts about what happened)
        - intents[]: Desired effects (what should happen next)

    Forbidden emissions:
        - projections[]: Orchestrators do not emit projections (that's for reducers)
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.reducer.model_intent import ModelIntent
from omnibase_core.models.services.model_custom_fields import ModelCustomFields
from omnibase_core.utils.util_decorators import allow_dict_str_any


@allow_dict_str_any(
    "Orchestrator output requires flexible step_outputs, output_variables, and metrics "
    "for arbitrary workflow results and execution data."
)
class ModelOrchestratorOutput(BaseModel):
    """
    Type-safe orchestrator output with Option A semantics.

    Provides structured output storage for orchestrator execution
    results with type safety and validation.

    Option A Semantic Model:
        Orchestrators are domain decision coordinators. They:
        1. Emit domain decision events (via events[]) recording facts
        2. Emit intents (via intents[]) expressing desired effects
        3. Do NOT emit projections (that's the reducer's responsibility)

        The runtime translates intents to internal directives that drive
        effect execution. This separation maintains clean boundaries between
        domain logic (orchestrator) and side-effect execution (effects).

    This model is immutable (frozen=True) and thread-safe. Once created,
    instances cannot be modified. This ensures safe sharing across threads
    and prevents accidental mutation of execution results.

    Important:
        The start_time and end_time fields currently both represent the workflow
        completion timestamp (when the result was created), not an actual execution
        time range. For the actual execution duration, use execution_time_ms instead.

    Example:
        >>> # Create output result with events and intents
        >>> result = ModelOrchestratorOutput(
        ...     execution_status="completed",
        ...     execution_time_ms=1500,
        ...     start_time="2025-01-01T00:00:00Z",
        ...     end_time="2025-01-01T00:00:01Z",
        ...     events=(workflow_completed_event,),
        ...     intents=(notify_user_intent,),
        ... )
        >>>
        >>> # To "update" a frozen model, use model_copy
        >>> updated = result.model_copy(update={"metrics": {"step_count": 5}})
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    # Execution summary
    execution_status: str = Field(default=..., description="Overall execution status")
    execution_time_ms: int = Field(
        default=...,
        description="Total execution time in milliseconds (use this for duration)",
    )
    start_time: str = Field(
        default=...,
        description="Execution timestamp (ISO format). Note: Currently set to completion "
        "time, not actual start. See execution_time_ms for duration.",
    )
    end_time: str = Field(
        default=...,
        description="Execution timestamp (ISO format). Note: Currently same as start_time "
        "(completion time). See execution_time_ms for duration.",
    )

    # Step results
    completed_steps: list[str] = Field(
        default_factory=list,
        description="List of completed step IDs",
    )
    failed_steps: list[str] = Field(
        default_factory=list,
        description="List of failed step IDs",
    )
    skipped_steps: list[str] = Field(
        default_factory=list,
        description="List of skipped step IDs",
    )

    # Step outputs (step_id -> output data)
    step_outputs: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Outputs from each step",
    )

    # Final outputs
    final_result: Any | None = Field(
        default=None, description="Final orchestration result"
    )
    output_variables: dict[str, Any] = Field(
        default_factory=dict,
        description="Output variables from the orchestration",
    )

    # Error information
    errors: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of errors (each with 'step_id', 'error_type', 'message')",
    )

    # Metrics
    metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Performance metrics",
    )

    # Parallel execution tracking
    parallel_executions: int = Field(
        default=0,
        description="Number of parallel execution batches completed",
    )

    # Option A semantic outputs (OMN-941)
    events: tuple[ModelEventEnvelope[Any], ...] = Field(
        default=(),
        description="Domain decision events emitted by orchestrator (facts about what happened)",
    )
    intents: tuple[ModelIntent, ...] = Field(
        default=(),
        description="Desired effects (what should happen), translated to runtime directives",
    )

    # Actions tracking (DEPRECATED)
    actions_emitted: list[Any] = Field(
        default_factory=list,
        description="DEPRECATED: Use events[] and intents[] instead. Will be removed in v0.5.0",
        deprecated=True,
    )

    # Custom outputs for extensibility
    custom_outputs: ModelCustomFields | None = Field(
        default=None,
        description="Custom output fields for orchestrator-specific data",
    )
