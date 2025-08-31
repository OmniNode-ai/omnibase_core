"""Strongly typed model for Anthropic API usage statistics."""

from pydantic import BaseModel, Field


class ModelAnthropicUsage(BaseModel):
    """Model for API usage statistics from Anthropic."""

    input_tokens: int = Field(..., description="Number of input tokens", ge=0)
    output_tokens: int = Field(..., description="Number of output tokens", ge=0)
