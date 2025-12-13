"""
Pull request trigger model.
"""

from pydantic import BaseModel, Field


class ModelPullRequestTrigger(BaseModel):
    """Pull request trigger configuration."""

    branches: list[str] | None = None
    types: list[str] | None = None
    paths: list[str] | None = None
    paths_ignore: list[str] | None = Field(default=None, alias="paths-ignore")
