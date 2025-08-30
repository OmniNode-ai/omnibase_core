"""
LLM metadata model for request/response metadata.

Provides strongly-typed metadata structure to replace Dict[str, Any] usage.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ModelLlmMetadata(BaseModel):
    """
    Metadata for LLM requests and responses.

    Replaces Dict[str, Any] usage in metadata fields.
    """

    request_id: Optional[str] = Field(
        default=None, description="Unique identifier for this request"
    )

    correlation_id: Optional[str] = Field(
        default=None, description="Correlation ID for request tracking"
    )

    provider: Optional[str] = Field(default=None, description="LLM provider name")

    model_name: Optional[str] = Field(
        default=None, description="Specific model name used"
    )

    timestamp: Optional[str] = Field(
        default=None, description="Request/response timestamp (ISO format)"
    )

    processing_time_ms: Optional[int] = Field(
        default=None, description="Processing time in milliseconds"
    )

    token_count_input: Optional[int] = Field(
        default=None, description="Number of input tokens"
    )

    token_count_output: Optional[int] = Field(
        default=None, description="Number of output tokens"
    )

    cost_estimate: Optional[float] = Field(
        default=None, description="Estimated cost for this request"
    )

    rate_limit_remaining: Optional[int] = Field(
        default=None, description="Remaining rate limit count"
    )

    retry_count: Optional[int] = Field(
        default=None, description="Number of retries attempted"
    )

    error_code: Optional[str] = Field(
        default=None, description="Error code if request failed"
    )

    user_agent: Optional[str] = Field(default=None, description="User agent string")

    session_id: Optional[str] = Field(default=None, description="Session identifier")

    tags: List[str] = Field(default_factory=list, description="Tags for categorization")

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",  # Allow extra fields for provider-specific metadata
    )
