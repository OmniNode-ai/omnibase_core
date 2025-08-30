"""Execution metadata model for tracking execution context information."""

from typing import Dict, Optional

from pydantic import BaseModel, Field


class ModelExecutionMetadata(BaseModel):
    """Model for execution metadata replacing Dict[str, Any]."""

    start_timestamp: float = Field(..., description="Execution start timestamp")
    user_id: Optional[str] = Field(None, description="User who initiated execution")
    environment: Optional[str] = Field(None, description="Execution environment")
    git_commit: Optional[str] = Field(None, description="Git commit hash")
    additional_context: Dict[str, str] = Field(
        default_factory=dict, description="Additional string context"
    )
