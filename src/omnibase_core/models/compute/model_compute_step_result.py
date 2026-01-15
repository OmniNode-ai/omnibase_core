"""
Result of a single pipeline step.

This module provides the ModelComputeStepResult model that captures the complete
outcome of executing a single step in a compute pipeline, including the output
data, success status, timing information, and error details if applicable.

Thread Safety:
    ModelComputeStepResult is immutable (frozen=True) and therefore thread-safe
    for read access after creation.

The step result provides:
    - Output data from the step transformation
    - Success/failure status
    - Execution metadata (timing, transformation type)
    - Error details if the step failed

Example:
    >>> from omnibase_core.models.compute import ModelComputeStepResult, ModelComputeStepMetadata
    >>>
    >>> # Successful step result
    >>> result = ModelComputeStepResult(
    ...     step_name="normalize",
    ...     output="HELLO WORLD",
    ...     success=True,
    ...     metadata=ModelComputeStepMetadata(
    ...         duration_ms=1.5,
    ...         transformation_type="CASE_CONVERSION",
    ...     ),
    ... )
    >>>
    >>> # Failed step result
    >>> failed_result = ModelComputeStepResult(
    ...     step_name="validate",
    ...     output=None,
    ...     success=False,
    ...     metadata=ModelComputeStepMetadata(duration_ms=0.3),
    ...     error_type="validation_error",
    ...     error_message="Required field 'name' is missing",
    ... )

See Also:
    - omnibase_core.models.compute.model_compute_pipeline_result: Aggregated pipeline results
    - omnibase_core.models.compute.model_compute_step_metadata: Step execution metadata
    - omnibase_core.utils.util_compute_executor: Creates step results during execution
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from omnibase_core.models.compute.model_compute_step_metadata import (
        ModelComputeStepMetadata,
    )

__all__ = [
    "ModelComputeStepResult",
]


class ModelComputeStepResult(BaseModel):
    """
    Result of a single pipeline step.

    Captures the complete outcome of executing one step in a compute pipeline.
    This includes the transformation output, execution status, timing metadata,
    and detailed error information when a step fails.

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it safe
        for concurrent read access from multiple threads or async tasks.

    Success Case:
        When success=True, the output field contains the step's transformation
        result and error_type/error_message are None.

    Failure Case:
        When success=False:
        - output is typically None (but may contain partial results)
        - error_type identifies the error category
        - error_message provides a human-readable description

    Attributes:
        step_name: Unique name identifying this step within the pipeline.
            Used for logging, debugging, and referencing in mapping paths
            (e.g., "$.steps.step_name.output").
        output: The output data from this step's transformation. Type depends
            on the transformation configuration. On success, contains the
            transformed data. On failure, typically None but may contain
            partial results depending on the error point.
        success: Whether the step completed successfully. True if the
            transformation executed without errors, False otherwise.
        metadata: Execution metadata including timing (duration_ms) and
            transformation type. Always populated regardless of success/failure.
        error_type: Error classification string if step failed, None otherwise.
            v1.0 uses simple strings (e.g., "validation_error", "operation_failed").
            Future versions may use a structured enum for better error handling.
        error_message: Human-readable error description if step failed,
            None otherwise. Suitable for logging and user-facing error messages.

    Example:
        >>> # Accessing step result in pipeline result
        >>> pipeline_result = execute_compute_pipeline(contract, data, context)
        >>> for step_name in pipeline_result.steps_executed:
        ...     step = pipeline_result.step_results[step_name]
        ...     if step.success:
        ...         print(f"{step_name}: completed in {step.metadata.duration_ms:.2f}ms")
        ...     else:
        ...         print(f"{step_name}: FAILED - {step.error_message}")
    """

    step_name: str
    output: Any
    success: bool = True
    metadata: ModelComputeStepMetadata
    error_type: str | None = None  # v1.0: Simple string, not enum
    error_message: str | None = None

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)


# Import at runtime for forward ref resolution
from omnibase_core.models.compute.model_compute_step_metadata import (
    ModelComputeStepMetadata,
)

ModelComputeStepResult.model_rebuild()
