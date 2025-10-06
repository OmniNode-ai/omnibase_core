from typing import Any

from pydantic import Field

"""
Example metadata model.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelExampleMetadata(BaseModel):
    """Metadata for an example."""

    name: str = Field(..., description="Example name")
    description: str | None = Field(default=None, description="Example description")
    category: str | None = Field(default=None, description="Example category")
    tags: list[str] = Field(default_factory=list, description="Example tags")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    author: str | None = Field(default=None, description="Example author")
