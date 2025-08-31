"""
MCP Tools Capability Model.

Model for MCP tools capability.
"""

from pydantic import BaseModel, Field


class ModelMCPToolsCapability(BaseModel):
    """
    MCP tools capability model.
    """

    listChanged: bool = Field(
        default=False,
        description="Whether tools list can change",
    )
    call: bool = Field(default=True, description="Whether tools can be called")
