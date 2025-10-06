from pydantic import Field

"""
GitHubRelease model.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from .model_git_hub_user import ModelGitHubUser


class ModelGitHubRelease(BaseModel):
    """GitHub release event data."""

    url: str = Field(..., description="Release API URL")
    id: int = Field(..., description="Release ID")
    tag_name: str = Field(..., description="Release tag")
    target_commitish: str = Field(..., description="Target branch or commit")
    name: str | None = Field(default=None, description="Release name")
    draft: bool = Field(default=False, description="Whether release is a draft")
    prerelease: bool = Field(
        default=False, description="Whether release is a prerelease"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    published_at: datetime | None = Field(
        default=None, description="Publication timestamp"
    )
    author: ModelGitHubUser = Field(..., description="Release author")
    body: str | None = Field(default=None, description="Release description")
