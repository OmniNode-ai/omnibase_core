"""
LLM response model for universal LLM operations.

Defines the standardized response format from all LLM providers
with usage metrics, metadata, and provider information.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.llm.model_llm_metadata import ModelLlmMetadata
from omnibase_core.model.llm.model_usage_metrics import ModelUsageMetrics


class ModelLLMResponse(BaseModel):
    """
    Universal LLM response model from all providers.

    Provides a standardized response format that captures
    generated content, usage metrics, and provider metadata
    for monitoring and optimization.
    """

    response: str = Field(description="Generated text response from the LLM")

    provider_used: str = Field(
        description="Which provider handled the request (ollama, openai, anthropic)"
    )

    model_used: str = Field(description="Specific model that generated the response")

    usage_metrics: ModelUsageMetrics = Field(
        description="Token usage, cost, and latency metrics"
    )

    conversation_id: Optional[str] = Field(
        default=None, description="Conversation identifier for multi-turn tracking"
    )

    finish_reason: Optional[str] = Field(
        default=None,
        description="Reason generation stopped (length, stop, error, etc.)",
    )

    confidence_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Model confidence in the response (if available)",
    )

    generated_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when response was generated",
    )

    metadata: ModelLlmMetadata = Field(
        default_factory=ModelLlmMetadata,
        description="Provider-specific metadata and additional information",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "response": "The ONEX semantic discovery system uses a multi-tier architecture...",
                "provider_used": "ollama",
                "model_used": "mistral:latest",
                "usage_metrics": {
                    "prompt_tokens": 45,
                    "completion_tokens": 234,
                    "total_tokens": 279,
                    "cost_usd": 0.0,
                    "latency_ms": 1250,
                },
                "conversation_id": "conv_12345",
                "finish_reason": "stop",
                "confidence_score": 0.92,
                "metadata": {
                    "model_version": "7B",
                    "context_used": 1024,
                    "temperature_used": 0.7,
                },
            }
        },
    )
