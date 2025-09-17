"""Strongly typed model for Anthropic tool use content blocks."""

from typing import Literal

from pydantic import BaseModel, Field


class ModelAnthropicToolUseContent(BaseModel):
    """Model for tool use content blocks in Anthropic responses."""

    type: Literal["tool_use"] = Field("tool_use", description="Content type identifier")
    id: str = Field(..., description="Unique tool use identifier", min_length=1)
    name: str = Field(..., description="Tool name", min_length=1)
    input: dict = Field(..., description="Tool input parameters as dynamic JSON")

    class Config:
        """Pydantic config."""

        extra = "forbid"  # Strict validation for tool use blocks
