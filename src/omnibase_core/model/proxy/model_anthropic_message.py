"""Strongly typed model for complete Anthropic message response."""

from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field

from omnibase_core.model.proxy.model_anthropic_text_content import \
    ModelAnthropicTextContent
from omnibase_core.model.proxy.model_anthropic_tool_use_content import \
    ModelAnthropicToolUseContent
from omnibase_core.model.proxy.model_anthropic_usage import ModelAnthropicUsage


class ModelAnthropicMessage(BaseModel):
    """Model for complete Anthropic message response."""

    id: str = Field(..., description="Message ID", min_length=1)
    type: Literal["message"] = Field("message", description="Response type")
    role: Literal["assistant"] = Field("assistant", description="Message role")
    content: List[Union[ModelAnthropicTextContent, ModelAnthropicToolUseContent]] = (
        Field(..., description="Message content blocks", min_items=0)
    )
    model: str = Field(..., description="Model used", min_length=1)
    stop_reason: Optional[Literal["end_turn", "max_tokens", "stop_sequence"]] = Field(
        None, description="Reason for stopping generation"
    )
    stop_sequence: Optional[str] = Field(
        None, description="Stop sequence that triggered stop"
    )
    usage: ModelAnthropicUsage = Field(..., description="Token usage statistics")
