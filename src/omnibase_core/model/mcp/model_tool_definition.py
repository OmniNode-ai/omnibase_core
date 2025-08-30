"""Strongly typed model for MCP tool definitions."""

from collections.abc import Callable

from pydantic import BaseModel, Field


class ModelToolDefinition(BaseModel):
    """Strongly typed model for MCP tool definition."""

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    handler: Callable | None = Field(None, description="Tool handler function")
    parameters: dict = Field(default_factory=dict, description="Tool parameters")

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True  # Allow Callable type
