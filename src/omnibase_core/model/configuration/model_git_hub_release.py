"""
GitHubRelease model.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .model_git_hub_user import ModelGitHubUser


class ModelGitHubRelease(BaseModel):
    """GitHub release event data."""

    url: str = Field(..., description="Release API URL")
    id: int = Field(..., description="Release ID")
    tag_name: str = Field(..., description="Release tag")
    target_commitish: str = Field(..., description="Target branch or commit")
    name: Optional[str] = Field(None, description="Release name")
    draft: bool = Field(False, description="Whether release is a draft")
    prerelease: bool = Field(False, description="Whether release is a prerelease")
    created_at: datetime = Field(..., description="Creation timestamp")
    published_at: Optional[datetime] = Field(None, description="Publication timestamp")
    author: ModelGitHubUser = Field(..., description="Release author")
    body: Optional[str] = Field(None, description="Release description")
