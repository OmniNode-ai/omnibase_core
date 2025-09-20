"""
Example metadata model.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelExampleMetadata(BaseModel):
    """Metadata for an example."""

    name: str = Field(..., description="Example name")
    description: str | None = Field(None, description="Example description")
    category: str | None = Field(None, description="Example category")
    tags: list[str] = Field(default_factory=list, description="Example tags")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    author: str | None = Field(None, description="Example author")