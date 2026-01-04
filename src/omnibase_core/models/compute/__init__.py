"""
Compute pipeline models for contract-driven NodeCompute v1.0.

This module provides the core models for compute pipeline execution as defined
in the CONTRACT_DRIVEN_NODECOMPUTE_V1_0 specification. These models support
deterministic, traceable data transformation pipelines with abort-on-first-failure
semantics.

Key Components:
    ModelComputeExecutionContext:
        Typed execution context carrying operation IDs, correlation IDs, and
        node identification for distributed tracing and observability.

    ModelComputeStepMetadata:
        Execution metadata for individual steps including timing information
        and transformation type for performance analysis.

    ModelComputeStepResult:
        Complete result of a single pipeline step including output data,
        success status, metadata, and error details.

    ModelComputePipelineResult:
        Aggregated result of entire pipeline execution with overall status,
        final output, timing, and per-step results.

Thread Safety:
    All models in this module are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.

Example:
    >>> from uuid import uuid4
    >>> from omnibase_core.models.compute import (
    ...     ModelComputeExecutionContext,
    ...     ModelComputePipelineResult,
    ... )
    >>> from omnibase_core.utils.util_compute_executor import execute_compute_pipeline
    >>>
    >>> # Create execution context
    >>> context = ModelComputeExecutionContext(
    ...     operation_id=uuid4(),
    ...     correlation_id=request_correlation_id,
    ... )
    >>>
    >>> # Execute pipeline and get result
    >>> result: ModelComputePipelineResult = execute_compute_pipeline(
    ...     contract, input_data, context
    ... )
    >>> if result.success:
    ...     print(f"Output: {result.output}")
    ... else:
    ...     print(f"Error at '{result.error_step}': {result.error_message}")

See Also:
    - omnibase_core.utils.util_compute_executor: Pipeline execution logic
    - omnibase_core.utils.util_compute_transformations: Transformation functions
    - omnibase_core.models.contracts.subcontracts: Contract definitions
    - docs/guides/node-building/03_COMPUTE_NODE_TUTORIAL.md: Compute node tutorial
"""

from omnibase_core.models.compute.model_compute_context import ModelComputeContext
from omnibase_core.models.compute.model_compute_execution_context import (
    ModelComputeExecutionContext,
)
from omnibase_core.models.compute.model_compute_input import ModelComputeInput
from omnibase_core.models.compute.model_compute_output import ModelComputeOutput
from omnibase_core.models.compute.model_compute_pipeline_result import (
    ModelComputePipelineResult,
)
from omnibase_core.models.compute.model_compute_step_metadata import (
    ModelComputeStepMetadata,
)
from omnibase_core.models.compute.model_compute_step_result import (
    ModelComputeStepResult,
)

__all__ = [
    "ModelComputeContext",
    "ModelComputeExecutionContext",
    "ModelComputeInput",
    "ModelComputeOutput",
    "ModelComputeStepMetadata",
    "ModelComputeStepResult",
    "ModelComputePipelineResult",
]
