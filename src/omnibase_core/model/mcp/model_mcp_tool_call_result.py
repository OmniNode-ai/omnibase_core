"""
MCP Tool Call Result Model.

Model for MCP tool call result.
"""

from typing import List

from pydantic import BaseModel, Field


class ModelMCPToolCallResult(BaseModel):
    """
    MCP tool call result model.
    """

    content: List["ModelMCPContentItem"] = Field(
        ..., description="Tool response content"
    )
