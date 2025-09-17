"""
MCP Tool Call Result Model.

Model for MCP tool call result.
"""

from pydantic import BaseModel, Field

from .model_mcp_content_item import ModelMCPContentItem


class ModelMCPToolCallResult(BaseModel):
    """
    MCP tool call result model.
    """

    content: list["ModelMCPContentItem"] = Field(
        ...,
        description="Tool response content",
    )
