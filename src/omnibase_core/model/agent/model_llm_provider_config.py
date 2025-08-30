"""
Model for LLM provider configuration.

Provides provider-specific configuration for LLM agents with proper ONEX compliance.
"""

from typing import Optional

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_llm_provider import EnumLLMProvider
from omnibase_core.model.agent.model_llm_endpoint import ModelLLMEndpoint


class ModelLLMProviderConfig(BaseModel):
    """Provider-specific configuration for LLM agents."""

    provider: EnumLLMProvider = Field(..., description="LLM provider type")
    model_id: str = Field(
        ..., description="Model identifier (e.g., mistral:7b-instruct)"
    )
    endpoint: Optional[ModelLLMEndpoint] = Field(
        None, description="Endpoint for local models"
    )
    api_key: Optional[str] = Field(None, description="API key for cloud providers")
    timeout_seconds: int = Field(300, description="Request timeout in seconds")
    max_retries: int = Field(3, description="Maximum retry attempts")

    # Model-specific parameters
    context_length: int = Field(4096, description="Maximum context window")
    temperature: float = Field(0.7, description="Generation temperature")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens to generate")
