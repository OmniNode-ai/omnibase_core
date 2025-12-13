"""
GitHubUser model.
"""

from pydantic import BaseModel, Field


class ModelGitHubUser(BaseModel):
    """GitHub user information."""

    login: str = Field(default=..., description="Username")
    id: int = Field(default=..., description="User ID")
    avatar_url: str | None = Field(default=None, description="Avatar URL")
    url: str | None = Field(default=None, description="User API URL")
    type: str = Field(default="User", description="User type")
