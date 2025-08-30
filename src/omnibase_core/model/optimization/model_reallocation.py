"""
Model for quota reallocation.

Quota reallocation between windows.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelReallocation(BaseModel):
    """Quota reallocation between windows."""

    from_window: str = Field(..., description="Source window ID")
    to_window: str = Field(..., description="Target window ID")
    amount: int = Field(..., gt=0, description="Tokens reallocated")
    reason: str = Field(..., description="Reason for reallocation")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When reallocation occurred"
    )
