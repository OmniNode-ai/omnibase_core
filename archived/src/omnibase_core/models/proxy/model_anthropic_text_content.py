"""Strongly typed model for Anthropic text content blocks."""

from typing import Literal

from pydantic import BaseModel, Field


class ModelAnthropicTextContent(BaseModel):
    """Model for text content blocks in Anthropic responses."""

    type: Literal["text"] = Field("text", description="Content type identifier")
    text: str = Field(..., description="Text content", min_length=0)
