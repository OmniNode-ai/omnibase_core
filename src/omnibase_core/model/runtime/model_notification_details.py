"""Notification details model."""

from pydantic import BaseModel, Field


class ModelNotificationDetails(BaseModel):
    """Additional notification details."""

    execution_id: str | None = Field(default=None, description="Execution ID")
    node_id: str | None = Field(default=None, description="Node ID")
    error_message: str | None = Field(default=None, description="Error message")
    duration_seconds: float | None = Field(
        default=None,
        description="Execution duration",
    )
    retry_count: int | None = Field(default=None, description="Retry count")
    metadata: dict[str, str] | None = Field(
        default=None,
        description="Additional metadata",
    )
