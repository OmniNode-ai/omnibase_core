"""
Example metadata model.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ModelExampleMetadata(BaseModel):
    """Metadata for an example."""

    name: str = Field(..., description="Example name")
    description: Optional[str] = Field(None, description="Example description")
    category: Optional[str] = Field(None, description="Example category")
    tags: List[str] = Field(default_factory=list, description="Example tags")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    author: Optional[str] = Field(None, description="Example author")
