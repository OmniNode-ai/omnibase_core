"""
OpenAI API request model for LLM provider operations.

Provides strongly-typed OpenAI API request model to replace Dict[str, Any] usage
in provider request preparation methods with proper ONEX naming conventions.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.llm.model_llm_chat_message import ModelLLMChatMessage


class ModelLLMOpenAIRequest(BaseModel):
    """
    Strongly-typed OpenAI API request model.

    Replaces Dict[str, Any] usage in _prepare_openai_request
    with proper type safety and validation.
    """

    model: str = Field(min_length=1, description="OpenAI model name")

    messages: list[ModelLLMChatMessage] = Field(
        min_items=1,
        description="Chat messages for the conversation",
    )

    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Sampling temperature",
    )

    max_tokens: int | None = Field(
        default=None,
        ge=1,
        description="Maximum tokens to generate",
    )

    top_p: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter",
    )

    frequency_penalty: float | None = Field(
        default=None,
        ge=-2.0,
        le=2.0,
        description="Frequency penalty",
    )

    presence_penalty: float | None = Field(
        default=None,
        ge=-2.0,
        le=2.0,
        description="Presence penalty",
    )

    stream: bool | None = Field(
        default=None,
        description="Whether to stream responses",
    )

    model_config = ConfigDict(
        validate_assignment=True,
        extra="allow",  # Allow additional OpenAI parameters
    )
