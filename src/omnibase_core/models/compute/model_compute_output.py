"""
Strongly typed output model for NodeCompute operations.

This module provides the ModelComputeOutput generic model that wraps computation
results with metadata including operation tracking, performance metrics, and
cache/parallelism information.

Thread Safety:
    ModelComputeOutput is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access from multiple threads or async tasks.

Key Features:
    - Generic type parameter T_Output for type-safe result data
    - Processing time measurement for performance analysis
    - Cache hit tracking for optimization insights
    - Parallel execution status for debugging

Example:
    >>> from omnibase_core.models import ModelComputeOutput
    >>> from uuid import uuid4
    >>>
    >>> # Create output after computation
    >>> output = ModelComputeOutput(
    ...     result={"transformed": "HELLO WORLD"},
    ...     operation_id=uuid4(),
    ...     computation_type="text_transform",
    ...     processing_time_ms=1.5,
    ...     cache_hit=False,
    ...     parallel_execution_used=False,
    ... )
    >>>
    >>> # Check performance
    >>> if output.processing_time_ms > 100:
    ...     print(f"Slow computation: {output.processing_time_ms}ms")
    >>> if output.cache_hit:
    ...     print("Result served from cache")

See Also:
    - omnibase_core.models.model_compute_input: Corresponding input model
    - omnibase_core.nodes.node_compute: NodeCompute.process() returns this model
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types.type_serializable_value import SerializedDict

__all__ = [
    "ModelComputeOutput",
]


class ModelComputeOutput[T_Output](BaseModel):
    """
    Output model for NodeCompute operations.

    Strongly typed output wrapper that includes computation metadata, performance
    metrics, and execution details. Created by NodeCompute.process() to return
    computation results with full observability information.

    Type Parameters:
        T_Output: The type of the computation result. Can be any type including
            primitives, dictionaries, lists, or Pydantic models.

    Attributes:
        result: The computation output data. Type is determined by the generic
            parameter T_Output and the computation function's return type.
        operation_id: UUID from the corresponding ModelComputeInput. Enables
            correlation between input and output for tracing and debugging.
        computation_type: String identifier of the computation that was executed.
            Matches the computation_type from the input.
        processing_time_ms: Actual execution time in milliseconds. Measured from
            computation start to completion, excluding cache lookup time.
            Value is 0.0 for cache hits (semantic: no computation work performed).
        cache_lookup_time_ms: Time spent on cache lookup operations in milliseconds.
            For cache hits, this represents the actual elapsed time for the cache
            retrieval (including key generation and dictionary access). For cache
            misses or when caching is disabled, this is 0.0. This field enables
            observability tooling to distinguish between "computation work done"
            (processing_time_ms) and "actual elapsed time" (cache_lookup_time_ms
            for cache hits).
        cache_hit: Whether this result was retrieved from cache rather than
            computed. True if the result was cached from a previous identical
            computation, False if freshly computed.
        parallel_execution_used: Whether parallel execution was utilized for
            this computation. True if the input data was processed using the
            thread pool, False for sequential execution.
        metadata: Additional context metadata from the computation. May include
            input size, cache status details, or computation-specific information.

    Example:
        >>> # Typical output inspection
        >>> output = node.process(input_data)
        >>> print(f"Result: {output.result}")
        >>> print(f"Time: {output.processing_time_ms:.2f}ms")
        >>> if output.cache_hit:
        ...     print("Served from cache")
        >>> if output.parallel_execution_used:
        ...     print("Used parallel processing")
    """

    result: T_Output
    operation_id: UUID
    computation_type: str
    processing_time_ms: float = Field(ge=0)
    cache_lookup_time_ms: float = Field(default=0.0, ge=0)
    cache_hit: bool = False
    parallel_execution_used: bool = False
    metadata: SerializedDict = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)
