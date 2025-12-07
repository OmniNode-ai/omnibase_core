"""
Typed execution context for compute pipelines.

v1.0: Minimal context for deterministic execution.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict

__all__ = [
    "ModelComputeExecutionContext",
]


class ModelComputeExecutionContext(BaseModel):
    """
    Typed execution context for compute pipelines.

    v1.0: Minimal context for deterministic execution.

    Attributes:
        operation_id: Unique identifier for this operation execution.
        correlation_id: Optional correlation ID for distributed tracing.
        node_id: Optional identifier for the node executing this operation.
    """

    operation_id: UUID
    correlation_id: UUID | None = None
    node_id: str | None = None

    model_config = ConfigDict(frozen=True)
