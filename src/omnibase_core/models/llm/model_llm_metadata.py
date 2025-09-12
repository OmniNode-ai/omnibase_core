"""
LLM metadata model for request/response metadata.

Provides strongly-typed metadata structure to replace Dict[str, Any] usage.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelLlmMetadata(BaseModel):
    """
    Metadata for LLM requests and responses.

    Replaces Dict[str, Any] usage in metadata fields.
    """

    request_id: str | None = Field(
        default=None,
        description="Unique identifier for this request",
    )

    correlation_id: str | None = Field(
        default=None,
        description="Correlation ID for request tracking",
    )

    provider: str | None = Field(default=None, description="LLM provider name")

    model_name: str | None = Field(
        default=None,
        description="Specific model name used",
    )

    timestamp: str | None = Field(
        default=None,
        description="Request/response timestamp (ISO format)",
    )

    processing_time_ms: int | None = Field(
        default=None,
        description="Processing time in milliseconds",
    )

    token_count_input: int | None = Field(
        default=None,
        description="Number of input tokens",
    )

    token_count_output: int | None = Field(
        default=None,
        description="Number of output tokens",
    )

    cost_estimate: float | None = Field(
        default=None,
        description="Estimated cost for this request",
    )

    rate_limit_remaining: int | None = Field(
        default=None,
        description="Remaining rate limit count",
    )

    retry_count: int | None = Field(
        default=None,
        description="Number of retries attempted",
    )

    error_code: str | None = Field(
        default=None,
        description="Error code if request failed",
    )

    user_agent: str | None = Field(default=None, description="User agent string")

    session_id: str | None = Field(default=None, description="Session identifier")

    tags: list[str] = Field(default_factory=list, description="Tags for categorization")

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",  # Allow extra fields for provider-specific metadata
    )
