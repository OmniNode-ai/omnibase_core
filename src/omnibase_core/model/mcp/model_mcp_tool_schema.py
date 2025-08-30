"""
MCP Tool Schema Model.

Model for MCP tool schema for JSON-RPC protocol.
"""

from pydantic import BaseModel, Field


class ModelMCPToolSchema(BaseModel):
    """
    MCP tool schema model for JSON-RPC protocol.
    """

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    inputSchema: "ModelMCPToolInputSchema" = Field(..., description="Tool input schema")
