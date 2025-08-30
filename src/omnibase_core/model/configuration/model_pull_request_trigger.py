"""
Pull request trigger model.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelPullRequestTrigger(BaseModel):
    """Pull request trigger configuration."""

    branches: Optional[List[str]] = None
    types: Optional[List[str]] = None
    paths: Optional[List[str]] = None
    paths_ignore: Optional[List[str]] = Field(None, alias="paths-ignore")
