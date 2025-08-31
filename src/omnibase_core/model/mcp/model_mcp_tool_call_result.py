"""
MCP Tool Call Result Model.

Model for MCP tool call result.
"""

from pydantic import BaseModel, Field


class ModelMCPToolCallResult(BaseModel):
    """
    MCP tool call result model.
    """

    content: list["ModelMCPContentItem"] = Field(
        ...,
        description="Tool response content",
    )
