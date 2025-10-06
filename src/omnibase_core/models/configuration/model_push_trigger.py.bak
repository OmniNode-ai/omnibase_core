from pydantic import Field

"""
Push trigger model.
"""

from pydantic import BaseModel, Field


class ModelPushTrigger(BaseModel):
    """Push trigger configuration."""

    branches: list[str] | None = None
    tags: list[str] | None = None
    paths: list[str] | None = None
    paths_ignore: list[str] | None = Field(None, alias="paths-ignore")
