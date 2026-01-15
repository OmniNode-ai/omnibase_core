"""
Result of compute pipeline execution.

This module provides the result model for compute pipeline executions,
aggregating all step results and providing overall success/failure status
with detailed error information when failures occur.

Thread Safety:
    ModelComputePipelineResult is immutable (frozen=True) and therefore
    thread-safe for read access after creation.

The result provides:
    - Overall success/failure status
    - Final output from the last successful step
    - Timing metrics for performance analysis
    - Individual step results for debugging
    - Detailed error context on failure

Example:
    >>> from omnibase_core.utils.util_compute_executor import execute_compute_pipeline
    >>>
    >>> result = execute_compute_pipeline(contract, data, context)
    >>> if result.success:
    ...     print(f"Output: {result.output}")
    ...     print(f"Time: {result.processing_time_ms:.2f}ms")
    ...     for step_name in result.steps_executed:
    ...         step = result.step_results[step_name]
    ...         print(f"  {step_name}: {step.metadata.duration_ms:.2f}ms")
    ... else:
    ...     print(f"Failed at '{result.error_step}': {result.error_message}")

See Also:
    - omnibase_core.utils.util_compute_executor: Creates this result
    - omnibase_core.models.compute.model_compute_step_result: Individual step results
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

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

    Aggregates the results of all executed steps and provides overall
    success/failure status with detailed error information. This model
    is returned by execute_compute_pipeline and contains everything
    needed to understand what happened during execution.

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it
        safe for concurrent read access from multiple threads or async tasks.

    Success Case:
        When success=True, the output field contains the final result from
        the last step, and all step_results will have success=True.

    Failure Case:
        When success=False, the error_* fields identify what went wrong:
        - error_step: Name of the step that failed
        - error_type: Error classification (e.g., "validation_error")
        - error_message: Human-readable description
        - output: Will be None
        - step_results: Contains results up to and including the failed step

    Attributes:
        success: Whether the entire pipeline completed successfully. True only
            if all enabled steps executed without errors.
        output: Final output from the pipeline. On success, this is the output
            from the last executed step. On failure, this is None.
            Type is Any because it depends on the pipeline's transformation
            configuration.
        processing_time_ms: Total pipeline execution time in milliseconds,
            measured from start to finish (including failed step if applicable).
        steps_executed: List of step names that were executed, in order.
            Includes all steps up to and including any failed step.
        step_results: Dictionary mapping step names to their individual results.
            Contains detailed timing and error information for each step.
        error_type: Error classification string if pipeline failed, None otherwise.
            v1.0 uses simple strings (e.g., "validation_error", "operation_failed").
            Future versions may use an enum for more structured error handling.
        error_message: Human-readable error description if pipeline failed,
            None otherwise. Suitable for logging and error reporting.
        error_step: Name of the step where the error occurred if pipeline failed,
            None otherwise. Useful for debugging and error recovery.

    Example:
        >>> # Successful execution
        >>> result = execute_compute_pipeline(contract, {"text": "hello"}, context)
        >>> assert result.success
        >>> print(result.output)  # "HELLO" (if uppercase transform)
        >>> print(f"Took {result.processing_time_ms:.2f}ms")
        >>>
        >>> # Failed execution
        >>> result = execute_compute_pipeline(bad_contract, data, context)
        >>> assert not result.success
        >>> print(f"Failed at step '{result.error_step}'")
        >>> print(f"Error: {result.error_message}")
    """

    success: bool
    output: Any  # Any: output type depends on pipeline configuration
    processing_time_ms: float = Field(ge=0)
    steps_executed: list[str]
    step_results: dict[str, ModelComputeStepResult]
    error_type: str | None = None  # v1.0: Simple string
    error_message: str | None = None
    error_step: str | None = None

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)


# Import at runtime for forward ref resolution
from omnibase_core.models.compute.model_compute_step_result import (
    ModelComputeStepResult,
)

ModelComputePipelineResult.model_rebuild()
