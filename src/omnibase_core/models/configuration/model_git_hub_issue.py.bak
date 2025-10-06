from typing import Any

from pydantic import Field

"""
GitHubIssue model.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from .model_git_hub_milestone import ModelGitHubMilestone
from .model_git_hub_user import ModelGitHubUser


class ModelGitHubIssue(BaseModel):
    """GitHub issue data."""

    id: int = Field(..., description="Issue ID")
    number: int = Field(..., description="Issue number")
    title: str = Field(..., description="Issue title")
    user: ModelGitHubUser = Field(..., description="Issue author")
    labels: list[str] = Field(default_factory=list, description="Issue labels")
    state: str = Field("open", description="Issue state")
    assignee: ModelGitHubUser | None = Field(None, description="Issue assignee")
    assignees: list[ModelGitHubUser] = Field(
        default_factory=list,
        description="All assignees",
    )
    milestone: ModelGitHubMilestone | None = Field(
        None,
        description="Issue milestone",
    )
    comments: int = Field(0, description="Number of comments")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")
    closed_at: datetime | None = Field(None, description="Close timestamp")
    body: str | None = Field(None, description="Issue description")
