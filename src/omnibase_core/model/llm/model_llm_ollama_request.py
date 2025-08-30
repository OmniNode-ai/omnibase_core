"""
Ollama API request model for LLM provider operations.

Provides strongly-typed Ollama API request model to replace Dict[str, Any] usage
in provider request preparation methods with proper ONEX naming conventions.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelLLMOllamaRequest(BaseModel):
    """
    Strongly-typed Ollama API request model.

    Replaces Dict[str, Any] usage in _prepare_ollama_request
    with proper type safety and validation.
    """

    model: str = Field(min_length=1, description="Ollama model name")

    prompt: str = Field(min_length=1, description="Text prompt for generation")

    system: str | None = Field(default=None, description="System prompt")

    context: str | None = Field(default=None, description="Conversation context")

    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Sampling temperature",
    )

    num_predict: int | None = Field(
        default=None,
        ge=1,
        description="Number of tokens to predict",
    )

    top_p: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter",
    )

    top_k: int | None = Field(
        default=None,
        ge=1,
        description="Top-k sampling parameter",
    )

    stream: bool | None = Field(
        default=None,
        description="Whether to stream responses",
    )

    model_config = ConfigDict(
        validate_assignment=True,
        extra="allow",  # Allow additional Ollama parameters
    )
