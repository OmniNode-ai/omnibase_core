"""Graph delete result model.

Type-safe model representing the result of a graph node/relationship deletion.

Thread Safety:
    ModelGraphDeleteResult instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelGraphDeleteResult(BaseModel):
    """
    Represents the result of a graph database deletion operation.

    Contains information about the deletion including success status,
    the deleted entity's ID, and cascade deletion statistics.

    Thread Safety:
        This model is frozen (immutable) after creation, making it
        safe for concurrent read access across threads.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    success: bool = Field(
        default=False,
        description="Whether the deletion operation succeeded",
    )
    node_id: str | None = Field(
        default=None,
        description="Element ID of the deleted node (if node deletion)",
    )
    relationships_deleted: int = Field(
        default=0,
        description="Number of relationships deleted (cascade or direct)",
        ge=0,
    )
    execution_time_ms: float = Field(
        default=0.0,
        description="Time taken to execute the deletion in milliseconds",
        ge=0.0,
    )


__all__ = ["ModelGraphDeleteResult"]
