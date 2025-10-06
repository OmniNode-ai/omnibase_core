from pydantic import Field

"""
GitHubRepository model.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from .model_git_hub_user import ModelGitHubUser


class ModelGitHubRepository(BaseModel):
    """GitHub repository information."""

    id: int = Field(..., description="Repository ID")
    name: str = Field(..., description="Repository name")
    full_name: str = Field(..., description="Full repository name (owner/repo)")
    private: bool = Field(default=False, description="Whether repository is private")
    owner: ModelGitHubUser = Field(..., description="Repository owner")
    description: str | None = Field(default=None, description="Repository description")
    fork: bool = Field(default=False, description="Whether repository is a fork")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(
        default=None, description="Last update timestamp"
    )
    pushed_at: datetime | None = Field(default=None, description="Last push timestamp")
    default_branch: str = Field("main", description="Default branch")
