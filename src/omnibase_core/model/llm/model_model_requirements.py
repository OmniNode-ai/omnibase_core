"""
Model requirements for intelligent LLM provider selection.

Defines capability requirements and constraints for automatic
model selection and provider routing.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ModelCapability(str, Enum):
    """Available model capabilities for routing decisions."""

    TEXT_GENERATION = "text_generation"
    CODE_GENERATION = "code_generation"
    CODE_ANALYSIS = "code_analysis"
    TECHNICAL_EXPLANATION = "technical_explanation"
    CONVERSATION = "conversation"
    FUNCTION_CALLING = "function_calling"
    JSON_OUTPUT = "json_output"
    LONG_CONTEXT = "long_context"
    MULTILINGUAL = "multilingual"
    REASONING = "reasoning"
    MATH = "math"
    CREATIVE_WRITING = "creative_writing"


class ModelModelRequirements(BaseModel):
    """
    Requirements and constraints for model selection.

    Defines the capabilities, performance, and cost constraints
    that guide intelligent provider and model selection for
    optimal user experience and resource utilization.
    """

    required_capabilities: list[ModelCapability] = Field(
        default_factory=list,
        description="Capabilities that the model must support",
    )

    preferred_capabilities: list[ModelCapability] = Field(
        default_factory=list,
        description="Capabilities that are preferred but not required",
    )

    min_context_length: int | None = Field(
        default=None,
        ge=1,
        le=1000000,
        description="Minimum context window size required",
    )

    max_latency_ms: int | None = Field(
        default=None,
        ge=100,
        le=60000,
        description="Maximum acceptable response latency in milliseconds",
    )

    max_cost_per_token: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Maximum acceptable cost per token in USD",
    )

    min_throughput_tokens_per_second: float | None = Field(
        default=None,
        ge=0.1,
        le=1000.0,
        description="Minimum required generation throughput",
    )

    quality_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum quality score for responses (0.0-1.0)",
    )

    privacy_level: str = Field(
        default="standard",
        description="Privacy level requirement (local_only, standard, external_ok)",
    )

    exclude_providers: list[str] = Field(
        default_factory=list,
        description="Providers to exclude from consideration",
    )

    require_streaming: bool = Field(
        default=False,
        description="Whether streaming response capability is required",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "required_capabilities": ["text_generation", "technical_explanation"],
                "preferred_capabilities": ["code_analysis", "long_context"],
                "min_context_length": 4096,
                "max_latency_ms": 5000,
                "max_cost_per_token": 0.001,
                "min_throughput_tokens_per_second": 10.0,
                "quality_threshold": 0.8,
                "privacy_level": "local_only",
                "exclude_providers": ["anthropic"],
                "require_streaming": False,
            },
        },
    )

    def matches_capability(self, available_capabilities: list[str]) -> bool:
        """Check if available capabilities meet requirements."""
        available_set = set(available_capabilities)
        required_set = {cap.value for cap in self.required_capabilities}
        return required_set.issubset(available_set)

    def calculate_preference_score(self, available_capabilities: list[str]) -> float:
        """Calculate preference score based on available capabilities."""
        if not self.preferred_capabilities:
            return 1.0

        available_set = set(available_capabilities)
        preferred_set = {cap.value for cap in self.preferred_capabilities}

        matching_preferred = preferred_set.intersection(available_set)
        return len(matching_preferred) / len(preferred_set)

    def is_privacy_compatible(self, provider_type: str) -> bool:
        """Check if provider type meets privacy requirements."""
        if self.privacy_level == "local_only":
            return provider_type == "local"
        if self.privacy_level == "standard":
            return provider_type in ["local", "external_trusted"]
        return self.privacy_level == "external_ok"
