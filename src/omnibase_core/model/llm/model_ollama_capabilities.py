"""
Ollama model capabilities model for local LLM management.

Provides strongly-typed model capability definitions and specialization
information for Ollama local models.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_query_type import EnumQueryType
from omnibase_core.model.core.model_onex_base_state import ModelOnexInputState


class ModelOllamaSpecialization(BaseModel):
    """Model representing specialization information for an Ollama model."""

    use_cases: List[EnumQueryType] = Field(
        default_factory=list, description="Query types this model specializes in"
    )
    description: str = Field(..., description="Description of model specialization")
    performance_tier: str = Field(
        default="standard", description="Performance tier (fast, standard, high)"
    )
    context_window: int = Field(..., gt=0, description="Model context window size")
    parameter_count: str = Field(
        ..., description="Model parameter count (e.g., '7B', '13B')"
    )


class ModelOllamaCapabilities(ModelOnexInputState):
    """
    Ollama model capabilities model for local LLM management.

    Provides comprehensive model capability definitions including specializations,
    performance characteristics, and usage recommendations.
    """

    model_name: str = Field(..., description="Ollama model name")
    display_name: str = Field(..., description="Human-readable model name")
    specialization: ModelOllamaSpecialization = Field(
        ..., description="Model specialization information"
    )
    is_available: bool = Field(
        default=False, description="Whether model is currently available"
    )
    last_health_check: Optional[str] = Field(
        default=None, description="Last health check timestamp"
    )
    average_latency_ms: Optional[float] = Field(
        default=None, ge=0.0, description="Average response latency in milliseconds"
    )
    success_rate: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Success rate for requests"
    )
    recommended_use_cases: List[str] = Field(
        default_factory=list, description="Recommended use cases for this model"
    )
