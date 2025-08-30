"""
Push trigger model.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelPushTrigger(BaseModel):
    """Push trigger configuration."""

    branches: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    paths: Optional[List[str]] = None
    paths_ignore: Optional[List[str]] = Field(None, alias="paths-ignore")
