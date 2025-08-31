"""
LLM request model for universal LLM operations.

Defines the standardized request format for all LLM providers
with configurable generation parameters and provider preferences.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.llm.model_generation_params import ModelGenerationParams
from omnibase_core.model.llm.model_llm_context import ModelLlmContext
from omnibase_core.model.llm.model_llm_metadata import ModelLlmMetadata
from omnibase_core.model.llm.model_model_requirements import ModelModelRequirements


class ModelLLMRequest(BaseModel):
    """
    Universal LLM request model for all providers.

    Provides a standardized interface for LLM operations across
    different providers (Ollama, OpenAI, Anthropic) with configurable
    parameters and intelligent routing capabilities.
    """

    prompt: str = Field(
        description="Main text prompt for generation",
        min_length=1,
        max_length=100000,
    )

    system_prompt: str | None = Field(
        default=None,
        description="System prompt to set context and behavior",
        max_length=10000,
    )

    model_requirements: ModelModelRequirements | None = Field(
        default=None,
        description="Capability and constraint specifications for model selection",
    )

    generation_params: ModelGenerationParams = Field(
        default_factory=ModelGenerationParams,
        description="Temperature, max_tokens, and other generation parameters",
    )

    provider_preferences: list[str] = Field(
        default_factory=lambda: ["ollama", "openai", "anthropic"],
        description="Preferred provider order for intelligent routing",
    )

    stream: bool = Field(
        default=False,
        description="Enable streaming responses for real-time interaction",
    )

    conversation_id: str | None = Field(
        default=None,
        description="Conversation identifier for multi-turn interactions",
    )

    context: list[ModelLlmContext] | None = Field(
        default=None,
        description="Previous conversation context for multi-turn support",
    )

    metadata: ModelLlmMetadata = Field(
        default_factory=ModelLlmMetadata,
        description="Additional metadata for tracking and monitoring",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "prompt": "Explain the ONEX semantic discovery system architecture",
                "system_prompt": "You are a helpful assistant explaining technical concepts clearly",
                "model_requirements": {
                    "min_context_length": 4096,
                    "capabilities": ["text_generation", "technical_explanation"],
                    "max_cost_per_token": 0.001,
                },
                "generation_params": {
                    "temperature": 0.7,
                    "max_tokens": 1000,
                    "top_p": 0.9,
                },
                "provider_preferences": ["ollama", "openai"],
                "stream": False,
                "metadata": {"source": "cli_chat", "user_id": "developer_001"},
            },
        },
    )
