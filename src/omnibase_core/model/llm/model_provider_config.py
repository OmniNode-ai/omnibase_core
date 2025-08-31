"""
Provider configuration models for LLM providers.

Defines configuration options for different LLM providers
including connection details, authentication, and provider-specific settings.
"""

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from omnibase_core.model.llm.model_gemini_types import ModelGeminiGenerationConfig
from omnibase_core.model.llm.model_provider_metadata import ModelProviderMetadata


class ModelProviderConfig(BaseModel):
    """
    Base configuration for LLM providers.

    Provides common configuration options that can be extended
    by specific provider implementations for their unique
    connection and authentication requirements.
    """

    provider_name: str = Field(
        description="Name of the LLM provider (ollama, openai, anthropic)",
    )

    enabled: bool = Field(default=True, description="Whether this provider is enabled")

    priority: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Provider priority for routing (1=highest, 100=lowest)",
    )

    timeout_seconds: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Request timeout in seconds",
    )

    retry_attempts: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Number of retry attempts on failure",
    )

    retry_delay_seconds: int = Field(
        default=1,
        ge=0,
        le=60,
        description="Delay between retry attempts",
    )

    health_check_interval_seconds: int = Field(
        default=60,
        ge=10,
        le=3600,
        description="Interval between health checks",
    )

    max_concurrent_requests: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Maximum concurrent requests to this provider",
    )

    rate_limit_requests_per_minute: int | None = Field(
        default=None,
        ge=1,
        description="Rate limit in requests per minute",
    )

    custom_headers: dict[str, str] = Field(
        default_factory=dict,
        description="Custom HTTP headers for requests",
    )

    additional_config: ModelProviderMetadata | None = Field(
        default=None,
        description="Provider-specific additional configuration",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )


class ModelOllamaConfig(ModelProviderConfig):
    """Configuration for Ollama local LLM provider."""

    provider_name: str = Field(default="ollama")

    host: str = Field(default="localhost", description="Ollama server host")

    port: int = Field(default=11434, ge=1, le=65535, description="Ollama server port")

    protocol: str = Field(default="http", description="Protocol (http or https)")

    verify_ssl: bool = Field(
        default=True,
        description="Verify SSL certificates for HTTPS",
    )

    model_pull_timeout_seconds: int = Field(
        default=300,
        ge=30,
        le=3600,
        description="Timeout for model download/pull operations",
    )

    default_model: str = Field(
        default="mistral:latest",
        description="Default model to use if none specified",
    )

    auto_pull_models: bool = Field(
        default=True,
        description="Automatically pull models if not available",
    )

    @property
    def base_url(self) -> str:
        """Get the base URL for Ollama API."""
        return f"{self.protocol}://{self.host}:{self.port}"


class ModelOpenAIConfig(ModelProviderConfig):
    """Configuration for OpenAI API provider."""

    provider_name: str = Field(default="openai")

    api_key: SecretStr = Field(description="OpenAI API key")

    organization_id: str | None = Field(
        default=None,
        description="OpenAI organization ID",
    )

    base_url: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI API base URL",
    )

    default_model: str = Field(
        default="gpt-3.5-turbo",
        description="Default OpenAI model to use",
    )

    max_cost_per_request: float | None = Field(
        default=None,
        ge=0.0,
        description="Maximum cost per request in USD",
    )

    daily_cost_limit: float | None = Field(
        default=None,
        ge=0.0,
        description="Daily cost limit in USD",
    )


class ModelAnthropicConfig(ModelProviderConfig):
    """Configuration for Anthropic Claude API provider."""

    provider_name: str = Field(default="anthropic")

    api_key: SecretStr = Field(description="Anthropic API key")

    base_url: str = Field(
        default="https://api.anthropic.com",
        description="Anthropic API base URL",
    )

    default_model: str = Field(
        default="claude-3-sonnet-20240229",
        description="Default Anthropic model to use",
    )

    max_cost_per_request: float | None = Field(
        default=None,
        ge=0.0,
        description="Maximum cost per request in USD",
    )

    daily_cost_limit: float | None = Field(
        default=None,
        ge=0.0,
        description="Daily cost limit in USD",
    )

    anthropic_version: str = Field(
        default="2023-06-01",
        description="Anthropic API version",
    )


class ModelGeminiConfig(ModelProviderConfig):
    """Configuration for Google Gemini LLM provider."""

    provider_name: str = Field(default="gemini")

    api_key: SecretStr = Field(description="Google API key for Gemini")

    base_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta",
        description="Gemini API base URL",
    )

    default_model: str = Field(
        default="gemini-1.5-flash",
        description="Default model to use if none specified",
    )

    model_aliases: dict[str, str] = Field(
        default_factory=lambda: {
            "flash": "gemini-1.5-flash",
            "pro": "gemini-1.5-pro",
            "pro-exp": "gemini-1.5-pro-experimental-0827",
        },
        description="Model name aliases for convenience",
    )

    max_cost_per_request: float | None = Field(
        default=None,
        ge=0.0,
        description="Maximum cost per request in USD",
    )

    daily_cost_limit: float | None = Field(
        default=None,
        ge=0.0,
        description="Daily cost limit in USD",
    )

    safety_settings: dict[str, str] | None = Field(
        default=None,
        description="Safety settings for content filtering",
    )

    generation_config: ModelGeminiGenerationConfig | None = Field(
        default=None,
        description="Default generation configuration",
    )
