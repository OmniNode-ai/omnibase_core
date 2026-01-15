"""
Metadata for a single pipeline step execution.

This module provides the ModelComputeStepMetadata model that captures execution
metrics and observability information for individual pipeline steps. This data
is essential for performance monitoring, debugging, and optimization.

Thread Safety:
    ModelComputeStepMetadata is immutable (frozen=True) and therefore thread-safe
    for read access after creation.

The metadata captures:
    - Execution timing (duration_ms) for performance analysis
    - Transformation type for debugging and logging

Example:
    >>> from omnibase_core.models.compute import ModelComputeStepMetadata
    >>>
    >>> metadata = ModelComputeStepMetadata(
    ...     duration_ms=2.45,
    ...     transformation_type="CASE_CONVERSION",
    ... )
    >>> print(f"Step took {metadata.duration_ms:.2f}ms")

See Also:
    - omnibase_core.models.compute.model_compute_step_result: Uses metadata for step results
    - omnibase_core.utils.util_compute_executor: Creates metadata during step execution
"""

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ModelComputeStepMetadata",
]


class ModelComputeStepMetadata(BaseModel):
    """
    Metadata for a single pipeline step execution.

    Captures timing and observability information for an individual step in the
    compute pipeline. This metadata is essential for performance monitoring,
    debugging slow pipelines, and understanding transformation behavior.

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it safe
        for concurrent read access from multiple threads or async tasks.

    Performance Analysis:
        The duration_ms field enables identification of slow steps in pipelines.
        Aggregate step durations may be less than total pipeline time due to
        overhead in result collection and context management.

    Attributes:
        duration_ms: Execution time for this step in milliseconds. Measured
            from step start to completion (or failure). Must be >= 0.
            Typical values range from <1ms for simple transformations to
            >100ms for complex operations.
        transformation_type: Type of transformation applied if this is a
            TRANSFORMATION step. Contains the string value of the
            EnumTransformationType (e.g., "CASE_CONVERSION", "REGEX").
            None for MAPPING and VALIDATION steps.

    Example:
        >>> # Analyzing step performance
        >>> for step_name, result in pipeline_result.step_results.items():
        ...     meta = result.metadata
        ...     if meta.duration_ms > 10.0:
        ...         print(f"Slow step: {step_name} took {meta.duration_ms:.2f}ms")
        ...         if meta.transformation_type:
        ...             print(f"  Transform type: {meta.transformation_type}")
    """

    duration_ms: float = Field(ge=0)
    transformation_type: str | None = None

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)
