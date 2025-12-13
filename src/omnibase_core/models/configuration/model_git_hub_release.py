"""
GitHubRelease model.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from .model_git_hub_user import ModelGitHubUser


class ModelGitHubRelease(BaseModel):
    """GitHub release event data."""

    url: str = Field(default=..., description="Release API URL")
    id: int = Field(default=..., description="Release ID")
    tag_name: str = Field(default=..., description="Release tag")
    target_commitish: str = Field(default=..., description="Target branch or commit")
    name: str | None = Field(default=None, description="Release name")
    draft: bool = Field(default=False, description="Whether release is a draft")
    prerelease: bool = Field(
        default=False, description="Whether release is a prerelease"
    )
    created_at: datetime = Field(default=..., description="Creation timestamp")
    published_at: datetime | None = Field(
        default=None, description="Publication timestamp"
    )
    author: ModelGitHubUser = Field(default=..., description="Release author")
    body: str | None = Field(default=None, description="Release description")
