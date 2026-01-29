"""Intent query operation result model.

Represents the result of querying stored intents.
Part of the intent storage subsystem (OMN-1645).
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.intelligence.model_intent_record import ModelIntentRecord

__all__ = ["ModelIntentQueryResult"]


class ModelIntentQueryResult(BaseModel):
    """Result of querying stored intents.

    Returned by query operations with matching intent records
    and pagination metadata.

    Attributes:
        success: Whether the query operation succeeded.
        intents: List of matching intent records.
        total_count: Total number of matching records (for pagination).
        error_message: Error description if operation failed.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        from_attributes=True,
    )

    success: bool = Field(
        description="Whether the query operation succeeded",
    )
    intents: list[ModelIntentRecord] = Field(
        default_factory=list,
        description="List of matching intent records",
    )
    total_count: int = Field(
        default=0,
        ge=0,
        description="Total number of matching records (for pagination)",
    )
    error_message: str | None = Field(
        default=None,
        description="Error description if operation failed",
    )
