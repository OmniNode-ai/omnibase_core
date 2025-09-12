"""
MCP Tools List Result Model.

Model for MCP tools list result.
"""

from pydantic import BaseModel, Field

from .model_mcp_tool_schema import ModelMCPToolSchema


class ModelMCPToolsListResult(BaseModel):
    """
    MCP tools list result model.
    """

    tools: list["ModelMCPToolSchema"] = Field(
        default_factory=list,
        description="Available tools",
    )
