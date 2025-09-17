"""
MCP Server Capabilities Model.

Model for MCP server capabilities.
"""

from pydantic import BaseModel, Field

from .model_mcp_tools_capability import ModelMCPToolsCapability


class ModelMCPCapabilities(BaseModel):
    """
    MCP server capabilities model.
    """

    tools: "ModelMCPToolsCapability" = Field(..., description="Tools capability")
