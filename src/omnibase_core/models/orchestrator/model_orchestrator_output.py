"""
Orchestrator Output Model

Type-safe orchestrator output that replaces Dict[str, Any] usage
in orchestrator results.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.errors.exception_groups import VALIDATION_ERRORS
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.orchestrator.model_action import ModelAction
from omnibase_core.models.services.model_custom_fields import ModelCustomFields


class ModelOrchestratorOutput(BaseModel):
    """
    Type-safe orchestrator output.

    Provides structured output storage for orchestrator execution
    results with type safety and validation.

    This model is immutable (frozen=True) and thread-safe. Once created,
    instances cannot be modified. This ensures safe sharing across threads
    and prevents accidental mutation of execution results.

    Important:
        The start_time and end_time fields currently both represent the workflow
        completion timestamp (when the result was created), not an actual execution
        time range. For the actual execution duration, use execution_time_ms instead.

    Example:
        >>> # Create output result
        >>> result = ModelOrchestratorOutput(
        ...     execution_status="completed",
        ...     execution_time_ms=1500,
        ...     start_time="2025-01-01T00:00:00Z",
        ...     end_time="2025-01-01T00:00:01Z",
        ... )
        >>>
        >>> # To "update" a frozen model, use model_copy
        >>> updated = result.model_copy(update={"metrics": {"step_count": 5}})
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
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
    step_outputs: dict[str, dict[str, ModelSchemaValue]] = Field(
        default_factory=dict,
        description="Outputs from each step (type-safe)",
    )

    # Final outputs
    final_result: ModelSchemaValue | None = Field(
        default=None, description="Final orchestration result (type-safe)"
    )
    output_variables: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Output variables from the orchestration (type-safe)",
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

    # Actions tracking
    actions_emitted: list[ModelAction] = Field(
        default_factory=list,
        description="List of actions emitted during workflow execution (type-safe)",
    )

    @field_validator("step_outputs", mode="before")
    @classmethod
    def convert_step_outputs(
        cls, v: dict[str, dict[str, object] | object]
    ) -> dict[str, dict[str, ModelSchemaValue]]:
        """Convert step outputs to ModelSchemaValue for type safety.

        Handles both properly structured step outputs (dict[str, dict[str, Any]])
        and malformed inputs where step data is not a dict.
        """
        if not v:
            return {}
        result: dict[str, dict[str, ModelSchemaValue]] = {}
        for step_id, step_data in v.items():
            if isinstance(step_data, dict):
                result[step_id] = {
                    key: cls._convert_to_schema_value(value)
                    for key, value in step_data.items()
                }
            else:
                result[step_id] = {"value": ModelSchemaValue.from_value(step_data)}
        return result

    @classmethod
    def _convert_to_schema_value(cls, value: object) -> ModelSchemaValue:
        """Convert a value to ModelSchemaValue, handling serialized dicts."""
        if isinstance(value, ModelSchemaValue):
            return value
        # Check if this is a serialized ModelSchemaValue dict
        if isinstance(value, dict) and "value_type" in value:
            try:
                return ModelSchemaValue.model_validate(value)
            except VALIDATION_ERRORS:
                # fallback-ok: If validation fails, treat as raw value.
                # VALIDATION_ERRORS covers TypeError, ValidationError, ValueError
                # which are raised by Pydantic model_validate.
                pass
        return ModelSchemaValue.from_value(value)

    @field_validator("output_variables", mode="before")
    @classmethod
    def convert_output_variables(
        cls, v: dict[str, object] | dict[str, ModelSchemaValue]
    ) -> dict[str, ModelSchemaValue]:
        """Convert output variables to ModelSchemaValue for type safety."""
        if not v:
            return {}
        return {key: cls._convert_to_schema_value(value) for key, value in v.items()}

    @field_validator("final_result", mode="before")
    @classmethod
    def convert_final_result(
        cls, v: object | ModelSchemaValue | None
    ) -> ModelSchemaValue | None:
        """Convert final result to ModelSchemaValue for type safety."""
        if v is None:
            return None
        return cls._convert_to_schema_value(v)

    @field_validator("actions_emitted", mode="before")
    @classmethod
    def convert_actions_emitted(
        cls, v: list[object] | list[ModelAction]
    ) -> list[ModelAction]:
        """Convert actions to ModelAction for type safety.

        Accepts:
        - list[ModelAction]: Returned as-is
        - list[dict]: Each dict is validated as ModelAction
        - Empty list: Returned as-is
        """
        if not v:
            return []
        # Note: len(v) > 0 check removed - guaranteed non-empty after early return
        if isinstance(v[0], ModelAction):
            return v  # type: ignore[return-value]  # Already list[ModelAction]
        # Let Pydantic validate dicts as ModelAction
        return v  # type: ignore[return-value]  # Passthrough for dicts; Pydantic validates as ModelAction

    # Custom outputs for extensibility
    custom_outputs: ModelCustomFields | None = Field(
        default=None,
        description="Custom output fields for orchestrator-specific data",
    )


__all__ = ["ModelOrchestratorOutput"]
