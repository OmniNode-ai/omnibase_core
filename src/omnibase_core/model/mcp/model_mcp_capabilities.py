"""
MCP Server Capabilities Model.

Model for MCP server capabilities.
"""

from pydantic import BaseModel, Field


class ModelMCPCapabilities(BaseModel):
    """
    MCP server capabilities model.
    """

    tools: "ModelMCPToolsCapability" = Field(..., description="Tools capability")
