from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ModelAgentActivity(BaseModel):
    """Current agent activity information."""

    current_task_id: UUID | None = Field(
        default=None, description="ID of the currently executing task"
    )
    current_operation: str | None = Field(
        default=None, description="Description of current operation"
    )
    progress_percent: float = Field(
        default=0.0, description="Progress percentage of current task (0-100)"
    )
    estimated_completion: datetime | None = Field(
        default=None, description="Estimated completion time for current task"
    )
    last_activity: datetime = Field(
        default_factory=datetime.now, description="Timestamp of last activity"
    )
