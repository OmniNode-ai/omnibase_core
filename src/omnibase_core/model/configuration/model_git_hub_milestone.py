"""
GitHub Milestone Model

Type-safe GitHub milestone that replaces Dict[str, Any] usage.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from .model_git_hub_user import ModelGitHubUser


class ModelGitHubMilestone(BaseModel):
    """
    Type-safe GitHub milestone.

    Represents a GitHub milestone with structured fields.
    """

    id: int = Field(..., description="Milestone ID")
    node_id: str = Field(..., description="Milestone node ID")
    number: int = Field(..., description="Milestone number")
    title: str = Field(..., description="Milestone title")
    description: str | None = Field(None, description="Milestone description")
    creator: ModelGitHubUser = Field(..., description="Milestone creator")
    open_issues: int = Field(0, description="Number of open issues")
    closed_issues: int = Field(0, description="Number of closed issues")
    state: str = Field("open", description="Milestone state (open/closed)")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")
    due_on: datetime | None = Field(None, description="Due date")
    closed_at: datetime | None = Field(None, description="Close timestamp")
