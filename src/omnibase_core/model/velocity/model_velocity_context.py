"""
Velocity Context Model for tracking task execution context.

This model captures contextual information about where and how
a velocity-tracked task was executed using strong typing.
"""

from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.core.model_environment import ModelEnvironment
from omnibase_core.model.memory.model_session_data import ModelSessionData


class ModelVelocityContext(BaseModel):
    """Context information for velocity tracking with strong typing."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    work_session: ModelSessionData = Field(description="Work session information")
    branch_name: str = Field(description="Git branch name", min_length=1)
    commit_hash: str = Field(description="Git commit hash", min_length=7, max_length=40)
    parent_task_id: UUID = Field(description="Parent task UUID if this is a subtask")
    correlation_id: UUID = Field(description="Correlation UUID for related operations")

    # Additional strongly-typed context fields
    environment: ModelEnvironment = Field(description="Environment context")
    working_directory: Path = Field(description="Working directory path")
    user_context: str = Field(description="User or system context", min_length=1)
