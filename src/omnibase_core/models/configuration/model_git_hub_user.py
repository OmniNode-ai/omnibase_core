from pydantic import Field

"""
GitHubUser model.
"""

from pydantic import BaseModel, Field


class ModelGitHubUser(BaseModel):
    """GitHub user information."""

    login: str = Field(..., description="Username")
    id: int = Field(..., description="User ID")
    avatar_url: str | None = Field(None, description="Avatar URL")
    url: str | None = Field(None, description="User API URL")
    type: str = Field("User", description="User type")
