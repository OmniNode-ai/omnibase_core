"""
Typed execution context for compute pipelines.

This module provides the execution context model used to track and trace
compute pipeline executions. The context carries identifiers for operation
tracking, distributed tracing, and node identification.

Thread Safety:
    ModelComputeExecutionContext is immutable (frozen=True) and therefore
    thread-safe for read access after creation.

v1.0 Scope:
    This is a minimal context for deterministic execution. Future versions
    may add additional context fields for:
    - Execution configuration overrides
    - Resource limits and timeouts
    - User/tenant identification
    - Feature flags

Example:
    >>> from uuid import uuid4
    >>> from omnibase_core.models.compute import ModelComputeExecutionContext
    >>>
    >>> context = ModelComputeExecutionContext(
    ...     operation_id=uuid4(),
    ...     correlation_id=uuid4(),  # From upstream request
    ...     node_id="node-transform-001",
    ... )

See Also:
    - omnibase_core.utils.util_compute_executor: Uses this context during execution
    - omnibase_core.mixins.mixin_compute_execution: Creates context in async wrapper
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict

__all__ = [
    "ModelComputeExecutionContext",
]


class ModelComputeExecutionContext(BaseModel):
    """
    Typed execution context for compute pipelines.

    Provides tracing and identification information for a single pipeline
    execution. This context is passed through the execution pipeline and
    can be used for logging, metrics, and distributed tracing.

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it
        safe for concurrent read access from multiple threads or async tasks.

    v1.0 Scope:
        Minimal context for deterministic execution. Contains only the
        essential identifiers needed for basic operation tracking.

    Attributes:
        operation_id: Unique identifier for this specific operation execution.
            Generated fresh for each pipeline invocation. Used for:
            - Correlating log entries within a single execution
            - Identifying specific executions in metrics
            - Debugging failed operations
        correlation_id: Optional correlation ID for distributed tracing.
            Typically propagated from upstream services to enable end-to-end
            request tracing across service boundaries. If not provided,
            only the operation_id is available for tracking.
        node_id: Optional identifier for the node executing this operation.
            Useful for multi-node deployments to identify which instance
            processed the request. String format for flexibility (can be
            UUID, hostname, or custom identifier).

    Example:
        >>> from uuid import uuid4
        >>> context = ModelComputeExecutionContext(
        ...     operation_id=uuid4(),
        ...     correlation_id=uuid4(),
        ...     node_id="compute-node-east-1",
        ... )
        >>> # Use in pipeline execution
        >>> result = execute_compute_pipeline(contract, data, context)
        >>> # Access for logging
        >>> logger.info(
        ...     "Pipeline completed",
        ...     extra={"operation_id": str(context.operation_id)}
        ... )
    """

    operation_id: UUID
    correlation_id: UUID | None = None
    # error-ok: string_id - Intentionally str for flexibility (can be UUID, hostname, or custom identifier)
    node_id: str | None = None

    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)
