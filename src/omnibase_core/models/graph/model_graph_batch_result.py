"""Graph Batch Result Model.

Type-safe model representing the result of a batch graph operation.

Thread Safety:
    ModelGraphBatchResult instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.graph.model_graph_query_result import ModelGraphQueryResult


class ModelGraphBatchResult(BaseModel):
    """Represents the result of a batch graph database operation.

    Contains individual results for each operation in the batch,
    overall success status, and transaction information.

    Thread Safety:
        This model is frozen (immutable) after creation, making it
        safe for concurrent read access across threads.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    results: list[ModelGraphQueryResult] = Field(
        default_factory=list,
        description="List of results for each operation in the batch",
    )
    success: bool = Field(
        default=False,
        description="Whether all operations in the batch succeeded",
    )
    transaction_id: UUID | None = Field(
        default=None,
        description="Transaction identifier if batch was executed in a transaction",
    )
    rollback_occurred: bool = Field(
        default=False,
        description="Whether a rollback occurred during batch execution",
    )


__all__ = ["ModelGraphBatchResult"]
