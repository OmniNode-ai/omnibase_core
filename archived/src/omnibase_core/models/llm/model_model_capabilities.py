"""
Model capabilities for LLM provider and model selection.

Defines the capabilities and characteristics of different LLM models
for intelligent routing and provider selection decisions.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.llm.model_model_requirements import (
    ModelCapability,
    ModelModelRequirements,
)


class ModelModelCapabilities(BaseModel):
    """
    Capabilities and characteristics of an LLM model.

    Defines what a specific model can do and its performance
    characteristics for intelligent routing decisions and
    capability-based model selection.
    """

    model_name: str = Field(
        description="Name of the model (e.g., 'mistral:latest', 'gpt-4')",
    )

    provider: str = Field(description="Provider name (ollama, openai, anthropic)")

    capabilities: list[ModelCapability] = Field(
        description="List of capabilities this model supports",
    )

    context_length: int = Field(
        ge=1,
        le=1000000,
        description="Maximum context window size in tokens",
    )

    max_output_tokens: int = Field(
        ge=1,
        le=100000,
        description="Maximum output tokens the model can generate",
    )

    cost_per_input_token: float = Field(
        default=0.0,
        ge=0.0,
        description="Cost per input token in USD (0.0 for local models)",
    )

    cost_per_output_token: float = Field(
        default=0.0,
        ge=0.0,
        description="Cost per output token in USD (0.0 for local models)",
    )

    typical_latency_ms: int | None = Field(
        default=None,
        ge=1,
        description="Typical response latency in milliseconds",
    )

    typical_throughput_tokens_per_second: float | None = Field(
        default=None,
        ge=0.1,
        description="Typical generation throughput in tokens per second",
    )

    supports_streaming: bool = Field(
        default=True,
        description="Whether the model supports streaming responses",
    )

    supports_function_calling: bool = Field(
        default=False,
        description="Whether the model supports function/tool calling",
    )

    supports_json_mode: bool = Field(
        default=False,
        description="Whether the model supports structured JSON output",
    )

    quality_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Quality assessment score (0.0-1.0)",
    )

    parameter_count: str | None = Field(
        default=None,
        description="Model parameter count (e.g., '7B', '13B', '70B')",
    )

    model_version: str | None = Field(
        default=None,
        description="Model version or variant information",
    )

    specializations: list[str] = Field(
        default_factory=list,
        description="Areas of specialization (e.g., 'code', 'conversation', 'technical')",
    )

    languages_supported: list[str] = Field(
        default_factory=lambda: ["en"],
        description="Languages supported by the model",
    )

    last_updated: str | None = Field(
        default=None,
        description="When capability information was last updated",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "model_name": "mistral:latest",
                "provider": "ollama",
                "capabilities": [
                    "text_generation",
                    "conversation",
                    "technical_explanation",
                    "code_analysis",
                ],
                "context_length": 4096,
                "max_output_tokens": 2048,
                "cost_per_input_token": 0.0,
                "cost_per_output_token": 0.0,
                "typical_latency_ms": 1200,
                "typical_throughput_tokens_per_second": 18.5,
                "supports_streaming": True,
                "supports_function_calling": False,
                "supports_json_mode": False,
                "quality_score": 0.85,
                "parameter_count": "7B",
                "model_version": "v0.2",
                "specializations": ["conversation", "technical_writing"],
                "languages_supported": ["en", "fr", "de", "es"],
                "last_updated": "2025-01-11T00:00:00Z",
            },
        },
    )

    def matches_requirements(self, requirements: "ModelModelRequirements") -> bool:
        """Check if this model meets the given requirements."""
        # Check required capabilities
        if not requirements.matches_capability(
            [cap.value for cap in self.capabilities],
        ):
            return False

        # Check context length
        if (
            requirements.min_context_length
            and self.context_length < requirements.min_context_length
        ):
            return False

        # Check cost constraints
        if requirements.max_cost_per_token:
            max_cost = max(self.cost_per_input_token, self.cost_per_output_token)
            if max_cost > requirements.max_cost_per_token:
                return False

        # Check latency constraints
        if requirements.max_latency_ms and self.typical_latency_ms:
            if self.typical_latency_ms > requirements.max_latency_ms:
                return False

        # Check throughput constraints
        if (
            requirements.min_throughput_tokens_per_second
            and self.typical_throughput_tokens_per_second
        ) and (
            self.typical_throughput_tokens_per_second
            < requirements.min_throughput_tokens_per_second
        ):
            return False

        # Check streaming requirement
        return not (requirements.require_streaming and not self.supports_streaming)

    def calculate_score(self, requirements: "ModelModelRequirements") -> float:
        """Calculate a score for how well this model matches requirements."""
        if not self.matches_requirements(requirements):
            return 0.0

        score = 1.0

        # Add preference bonus
        preference_score = requirements.calculate_preference_score(
            [cap.value for cap in self.capabilities],
        )
        score += preference_score * 0.2

        # Add quality bonus
        if self.quality_score:
            score += self.quality_score * 0.1

        # Prefer local models for privacy
        if (
            self.cost_per_input_token == 0.0
            and requirements.privacy_level == "local_only"
        ):
            score += 0.1

        return min(score, 2.0)  # Cap at 2.0

    def estimate_cost(self, prompt_tokens: int, max_output_tokens: int) -> float:
        """Estimate cost for a request with this model."""
        input_cost = prompt_tokens * self.cost_per_input_token
        output_cost = max_output_tokens * self.cost_per_output_token
        return input_cost + output_cost
