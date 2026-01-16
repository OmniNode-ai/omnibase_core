"""Graph Query Result Model.

Type-safe model representing the result of a graph database query.

Thread Safety:
    ModelGraphQueryResult instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.graph.model_graph_query_counters import (
    ModelGraphQueryCounters,
)
from omnibase_core.models.graph.model_graph_query_summary import ModelGraphQuerySummary
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelGraphQueryResult(BaseModel):
    """Represents the result of a graph database query.

    Contains query records, execution summary, operation counters,
    and timing information.

    Thread Safety:
        This model is frozen (immutable) after creation, making it
        safe for concurrent read access across threads.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    records: list[SerializedDict] = Field(
        default_factory=list,
        description="List of result records from the query",
    )
    summary: ModelGraphQuerySummary = Field(
        default_factory=ModelGraphQuerySummary,
        description="Query execution summary",
    )
    counters: ModelGraphQueryCounters = Field(
        default_factory=ModelGraphQueryCounters,
        description="Statistics counters for the query execution",
    )
    execution_time_ms: float = Field(
        default=0.0,
        description="Time taken to execute the query in milliseconds",
        ge=0.0,
    )


__all__ = ["ModelGraphQueryResult"]
