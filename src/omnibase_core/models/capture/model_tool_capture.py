"""
Tool capture model for utility_tool_capture_storage.py
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ModelToolCapture(BaseModel):
    """Basic tool capture model for storage utilities."""

    id: str = Field(..., description="Unique capture ID")
    tool_name: str = Field(..., description="Name of the captured tool")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Capture timestamp"
    )
    data: dict[str, Any] = Field(default_factory=dict, description="Captured tool data")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}
