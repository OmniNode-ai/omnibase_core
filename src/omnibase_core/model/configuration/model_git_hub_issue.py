"""
GitHubIssue model.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from .model_git_hub_milestone import ModelGitHubMilestone
from .model_git_hub_user import ModelGitHubUser


class ModelGitHubIssue(BaseModel):
    """GitHub issue data."""

    id: int = Field(..., description="Issue ID")
    number: int = Field(..., description="Issue number")
    title: str = Field(..., description="Issue title")
    user: ModelGitHubUser = Field(..., description="Issue author")
    labels: List[str] = Field(default_factory=list, description="Issue labels")
    state: str = Field("open", description="Issue state")
    assignee: Optional[ModelGitHubUser] = Field(None, description="Issue assignee")
    assignees: List[ModelGitHubUser] = Field(
        default_factory=list, description="All assignees"
    )
    milestone: Optional[ModelGitHubMilestone] = Field(
        None, description="Issue milestone"
    )
    comments: int = Field(0, description="Number of comments")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    closed_at: Optional[datetime] = Field(None, description="Close timestamp")
    body: Optional[str] = Field(None, description="Issue description")
