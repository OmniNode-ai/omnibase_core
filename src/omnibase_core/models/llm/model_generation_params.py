"""
Generation parameters model for LLM operations.

Defines configurable parameters for text generation across
all LLM providers with validation and sensible defaults.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModelGenerationParams(BaseModel):
    """
    Configurable parameters for LLM text generation.

    Provides standardized generation parameters that work
    across different LLM providers with appropriate validation
    and provider-specific parameter mapping.
    """

    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Randomness in generation (0.0 = deterministic, 2.0 = very random)",
    )

    max_tokens: int = Field(
        default=1000,
        ge=1,
        le=32000,
        description="Maximum number of tokens to generate",
    )

    top_p: float | None = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter (cumulative probability)",
    )

    top_k: int | None = Field(
        default=None,
        ge=1,
        le=100,
        description="Top-k sampling parameter (number of tokens to consider)",
    )

    frequency_penalty: float | None = Field(
        default=0.0,
        ge=-2.0,
        le=2.0,
        description="Penalty for token frequency (reduce repetition)",
    )

    presence_penalty: float | None = Field(
        default=0.0,
        ge=-2.0,
        le=2.0,
        description="Penalty for token presence (encourage new topics)",
    )

    stop_sequences: list[str] | None = Field(
        default=None,
        description="Sequences that stop generation when encountered",
    )

    seed: int | None = Field(
        default=None,
        description="Random seed for reproducible generation",
    )

    repeat_penalty: float | None = Field(
        default=1.1,
        ge=0.1,
        le=2.0,
        description="Penalty for repeating tokens (Ollama-specific)",
    )

    mirostat: int | None = Field(
        default=None,
        ge=0,
        le=2,
        description="Mirostat sampling algorithm version (Ollama-specific)",
    )

    mirostat_eta: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Mirostat learning rate (Ollama-specific)",
    )

    mirostat_tau: float | None = Field(
        default=None,
        ge=0.0,
        le=10.0,
        description="Mirostat target entropy (Ollama-specific)",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "temperature": 0.7,
                "max_tokens": 1000,
                "top_p": 0.9,
                "top_k": 40,
                "frequency_penalty": 0.0,
                "presence_penalty": 0.0,
                "stop_sequences": ["\n\n", "END"],
                "seed": 42,
                "repeat_penalty": 1.1,
            },
        },
    )

    def get_ollama_params(self) -> dict[str, Any]:
        """Get parameters formatted for Ollama API."""
        params: dict[str, Any] = {
            "temperature": self.temperature,
            "num_predict": self.max_tokens,
            "top_p": self.top_p,
            "repeat_penalty": self.repeat_penalty,
        }

        if self.top_k is not None:
            params["top_k"] = self.top_k
        if self.stop_sequences:
            params["stop"] = self.stop_sequences
        if self.seed is not None:
            params["seed"] = self.seed
        if self.mirostat is not None:
            params["mirostat"] = self.mirostat
        if self.mirostat_eta is not None:
            params["mirostat_eta"] = self.mirostat_eta
        if self.mirostat_tau is not None:
            params["mirostat_tau"] = self.mirostat_tau

        # Remove None values
        return {k: v for k, v in params.items() if v is not None}

    def get_openai_params(self) -> dict[str, Any]:
        """Get parameters formatted for OpenAI API."""
        params: dict[str, Any] = {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
        }

        if self.stop_sequences:
            params["stop"] = self.stop_sequences
        if self.seed is not None:
            params["seed"] = self.seed

        # Remove None values
        return {k: v for k, v in params.items() if v is not None}

    def get_anthropic_params(self) -> dict[str, Any]:
        """Get parameters formatted for Anthropic API."""
        params: dict[str, Any] = {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
        }

        if self.stop_sequences:
            params["stop_sequences"] = self.stop_sequences

        # Remove None values
        return {k: v for k, v in params.items() if v is not None}
