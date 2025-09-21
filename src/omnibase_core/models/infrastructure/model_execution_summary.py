"""
Execution summary model.

Typed execution summary model with result metadata.
Follows ONEX one-model-per-file naming conventions.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class ModelExecutionSummary(BaseModel):
    """Execution summary model with typed fields."""

    execution_id: UUID = Field(description="Execution identifier")
    success: bool = Field(description="Whether execution was successful")
    duration_ms: int | None = Field(description="Duration in milliseconds")
    warning_count: int = Field(description="Number of warnings")
    has_metadata: bool = Field(description="Whether metadata exists")
    completed: bool = Field(description="Whether execution is completed")


# Export for use
__all__ = ["ModelExecutionSummary"]
