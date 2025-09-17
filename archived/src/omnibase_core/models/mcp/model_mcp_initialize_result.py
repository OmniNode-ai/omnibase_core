"""
MCP Initialize Method Result Model.

Result model for MCP initialize method.
"""

from pydantic import BaseModel, Field

from .model_mcp_capabilities import ModelMCPCapabilities
from .model_mcp_server_info import ModelMCPServerInfo


class ModelMCPInitializeResult(BaseModel):
    """
    MCP initialize method result model.
    """

    protocolVersion: str = Field(
        default="2024-11-05",
        description="MCP protocol version",
    )
    capabilities: "ModelMCPCapabilities" = Field(..., description="Server capabilities")
    serverInfo: "ModelMCPServerInfo" = Field(..., description="Server information")
