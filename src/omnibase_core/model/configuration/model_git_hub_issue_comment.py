"""
GitHubIssueComment model.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .model_git_hub_user import ModelGitHubUser


class ModelGitHubIssueComment(BaseModel):
    """GitHub issue comment data."""

    id: int = Field(..., description="Comment ID")
    url: str = Field(..., description="Comment API URL")
    user: ModelGitHubUser = Field(..., description="Comment author")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    body: str = Field(..., description="Comment text")
