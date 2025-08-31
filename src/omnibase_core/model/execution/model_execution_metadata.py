"""Execution metadata model for tracking execution context information."""

from pydantic import BaseModel, Field


class ModelExecutionMetadata(BaseModel):
    """Model for execution metadata replacing Dict[str, Any]."""

    start_timestamp: float = Field(..., description="Execution start timestamp")
    user_id: str | None = Field(None, description="User who initiated execution")
    environment: str | None = Field(None, description="Execution environment")
    git_commit: str | None = Field(None, description="Git commit hash")
    additional_context: dict[str, str] = Field(
        default_factory=dict,
        description="Additional string context",
    )
