"""
Result of compute pipeline execution.

Aggregates all step results and provides overall success/failure status.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from omnibase_core.models.compute.model_compute_step_result import (
        ModelComputeStepResult,
    )

__all__ = [
    "ModelComputePipelineResult",
]


class ModelComputePipelineResult(BaseModel):
    """
    Result of compute pipeline execution.

    Attributes:
        success: Whether the entire pipeline completed successfully.
        output: Final output from the pipeline (from last step).
        processing_time_ms: Total pipeline execution time in milliseconds.
        steps_executed: List of step names that were executed (in order).
        step_results: Dictionary mapping step names to their results.
        error_type: v1.0 uses simple string for error type (not enum).
        error_message: Human-readable error message if pipeline failed.
        error_step: Name of the step where the error occurred.
    """

    success: bool
    output: Any
    processing_time_ms: float
    steps_executed: list[str]
    step_results: dict[str, "ModelComputeStepResult"]
    error_type: str | None = None  # v1.0: Simple string
    error_message: str | None = None
    error_step: str | None = None

    model_config = ConfigDict(frozen=True)


# Import at runtime for forward ref resolution
from omnibase_core.models.compute.model_compute_step_result import (  # noqa: E402
    ModelComputeStepResult,
)

ModelComputePipelineResult.model_rebuild()
