"""
MCP Tools List Result Model.

Model for MCP tools list result.
"""

from typing import List

from pydantic import BaseModel, Field


class ModelMCPToolsListResult(BaseModel):
    """
    MCP tools list result model.
    """

    tools: List["ModelMCPToolSchema"] = Field(
        default_factory=list, description="Available tools"
    )
