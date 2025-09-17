"""
Orchestrator Output Model

Type-safe orchestrator output that replaces Dict[str, Any] usage
in orchestrator results.
"""

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_custom_fields import ModelCustomFields


class ModelOrchestratorOutput(BaseModel):
    """
    Type-safe orchestrator output.

    Provides structured output storage for orchestrator execution
    results with type safety and validation.
    """

    # Execution summary
    execution_status: str = Field(..., description="Overall execution status")
    execution_time_ms: int = Field(
        ...,
        description="Total execution time in milliseconds",
    )
    start_time: str = Field(..., description="Execution start time (ISO format)")
    end_time: str = Field(..., description="Execution end time (ISO format)")

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
    final_result: Any | None = Field(None, description="Final orchestration result")
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

    # Custom outputs for extensibility
    custom_outputs: ModelCustomFields | None = Field(
        None,
        description="Custom output fields for orchestrator-specific data",
    )
