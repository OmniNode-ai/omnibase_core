"""
GitHubIssue model.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from .model_git_hub_milestone import ModelGitHubMilestone
from .model_git_hub_user import ModelGitHubUser


class ModelGitHubIssue(BaseModel):
    """GitHub issue data."""

    id: int = Field(default=..., description="Issue ID")
    number: int = Field(default=..., description="Issue number")
    title: str = Field(default=..., description="Issue title")
    user: ModelGitHubUser = Field(default=..., description="Issue author")
    labels: list[str] = Field(default_factory=list, description="Issue labels")
    state: str = Field(default="open", description="Issue state")
    assignee: ModelGitHubUser | None = Field(default=None, description="Issue assignee")
    assignees: list[ModelGitHubUser] = Field(
        default_factory=list,
        description="All assignees",
    )
    milestone: ModelGitHubMilestone | None = Field(
        default=None,
        description="Issue milestone",
    )
    comments: int = Field(default=0, description="Number of comments")
    created_at: datetime = Field(default=..., description="Creation timestamp")
    updated_at: datetime | None = Field(
        default=None, description="Last update timestamp"
    )
    closed_at: datetime | None = Field(default=None, description="Close timestamp")
    body: str | None = Field(default=None, description="Issue description")
