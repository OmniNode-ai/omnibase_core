"""
MCP Server Information Model.

Model for MCP server information.
"""

from pydantic import BaseModel, Field


class ModelMCPServerInfo(BaseModel):
    """
    MCP server information model.
    """

    name: str = Field(..., description="Server name")
    version: str = Field(..., description="Server version")
