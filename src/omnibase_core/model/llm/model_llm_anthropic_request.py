"""
Anthropic API request model for LLM provider operations.

Provides strongly-typed Anthropic API request model to replace Dict[str, Any] usage
in provider request preparation methods with proper ONEX naming conventions.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.llm.model_llm_chat_message import ModelLLMChatMessage


class ModelLLMAnthropicRequest(BaseModel):
    """
    Strongly-typed Anthropic API request model.

    Replaces Dict[str, Any] usage in _prepare_anthropic_request
    with proper type safety and validation.
    """

    model: str = Field(min_length=1, description="Anthropic model name")

    messages: List[ModelLLMChatMessage] = Field(
        min_items=1, description="Chat messages for the conversation"
    )

    max_tokens: int = Field(ge=1, description="Maximum tokens to generate")

    system: Optional[str] = Field(default=None, description="System prompt")

    temperature: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Sampling temperature"
    )

    top_p: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Nucleus sampling parameter"
    )

    top_k: Optional[int] = Field(
        default=None, ge=1, description="Top-k sampling parameter"
    )

    stream: Optional[bool] = Field(
        default=None, description="Whether to stream responses"
    )

    model_config = ConfigDict(
        validate_assignment=True, extra="allow"  # Allow additional Anthropic parameters
    )
