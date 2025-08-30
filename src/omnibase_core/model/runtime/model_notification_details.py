"""Notification details model."""

from typing import Dict, Optional

from pydantic import BaseModel, Field


class ModelNotificationDetails(BaseModel):
    """Additional notification details."""

    execution_id: Optional[str] = Field(default=None, description="Execution ID")
    node_id: Optional[str] = Field(default=None, description="Node ID")
    error_message: Optional[str] = Field(default=None, description="Error message")
    duration_seconds: Optional[float] = Field(
        default=None, description="Execution duration"
    )
    retry_count: Optional[int] = Field(default=None, description="Retry count")
    metadata: Optional[Dict[str, str]] = Field(
        default=None, description="Additional metadata"
    )
