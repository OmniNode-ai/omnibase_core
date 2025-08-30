"""
MCP Content Item Model.

Model for MCP content item.
"""

from pydantic import BaseModel, Field


class ModelMCPContentItem(BaseModel):
    """
    MCP content item model.
    """

    type: str = Field(..., description="Content type")
    text: str = Field(..., description="Content text")
