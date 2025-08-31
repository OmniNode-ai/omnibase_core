"""
MCP Tools List Result Model.

Model for MCP tools list result.
"""

from pydantic import BaseModel, Field


class ModelMCPToolsListResult(BaseModel):
    """
    MCP tools list result model.
    """

    tools: list["ModelMCPToolSchema"] = Field(
        default_factory=list,
        description="Available tools",
    )
