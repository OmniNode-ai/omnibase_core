"""
Model for usage snapshot.

Point-in-time usage snapshot for tracking.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from omnibase_core.model.optimization.model_snapshot_metadata import \
    ModelSnapshotMetadata


class ModelUsageSnapshot(BaseModel):
    """Point-in-time usage snapshot."""

    timestamp: datetime = Field(..., description="Snapshot timestamp")
    window_id: str = Field(..., description="Active window ID")
    agent_id: str = Field(..., description="Agent that consumed tokens")
    tokens_consumed: int = Field(..., gt=0, description="Tokens consumed")
    task_type: str = Field(..., description="Type of task performed")
    success: bool = Field(..., description="Whether task succeeded")

    cost: Optional[float] = Field(None, description="Cost in USD")
    duration_seconds: Optional[int] = Field(None, description="Task duration")

    metadata: Optional[ModelSnapshotMetadata] = Field(
        default_factory=ModelSnapshotMetadata, description="Additional snapshot data"
    )
