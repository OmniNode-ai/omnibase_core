"""
GitHub Milestone Model

Type-safe GitHub milestone that replaces Dict[str, Any] usage.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from .model_git_hub_user import ModelGitHubUser


class ModelGitHubMilestone(BaseModel):
    """
    Type-safe GitHub milestone.

    Represents a GitHub milestone with structured fields.
    """

    id: int = Field(default=..., description="Milestone ID")
    node_id: UUID = Field(default=..., description="Milestone node ID")
    number: int = Field(default=..., description="Milestone number")
    title: str = Field(default=..., description="Milestone title")
    description: str | None = Field(default=None, description="Milestone description")
    creator: ModelGitHubUser = Field(default=..., description="Milestone creator")
    open_issues: int = Field(default=0, description="Number of open issues")
    closed_issues: int = Field(default=0, description="Number of closed issues")
    state: str = Field(default="open", description="Milestone state (open/closed)")
    created_at: datetime = Field(default=..., description="Creation timestamp")
    updated_at: datetime | None = Field(
        default=None, description="Last update timestamp"
    )
    due_on: datetime | None = Field(default=None, description="Due date")
    closed_at: datetime | None = Field(default=None, description="Close timestamp")
