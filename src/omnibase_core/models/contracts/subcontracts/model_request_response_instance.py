"""
Request-Response Instance Model for Kafka RPC-style communication.

Defines a single request-response pattern instance configuration including
topic suffixes, correlation settings, timeout, and consumer group behavior.

Strict typing is enforced: No Any types allowed in implementation.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .model_correlation_config import ModelCorrelationConfig
from .model_reply_topics import ModelReplyTopics

__all__ = ["ModelRequestResponseInstance"]


class ModelRequestResponseInstance(BaseModel):
    """
    Configuration for a single request-response pattern instance.

    Defines the complete configuration for Kafka RPC-style request-response
    communication, including request/reply topics, correlation tracking,
    timeout behavior, and consumer group strategies.

    Strict typing is enforced: No Any types allowed in implementation.
    """

    name: str = Field(
        ...,
        description="Instance identifier for this request-response pattern",
    )

    request_topic: str = Field(
        ...,
        description="Topic suffix for request messages (ONEX naming convention required)",
    )

    reply_topics: ModelReplyTopics = Field(
        ...,
        description="Topic suffixes for completed and failed responses",
    )

    correlation: ModelCorrelationConfig | None = Field(
        default=None,
        description="Correlation ID configuration. If None, uses body.correlation_id",
    )

    timeout_seconds: int = Field(
        default=30,
        ge=1,
        description="Response timeout in seconds",
    )

    consumer_group_mode: Literal["per_instance", "shared"] = Field(
        default="per_instance",
        description="Consumer group strategy: per_instance creates unique groups, shared uses common group",
    )

    auto_offset_reset: Literal["earliest", "latest"] = Field(
        default="earliest",
        description="Kafka consumer offset reset policy when no committed offset exists",
    )

    @field_validator("request_topic", mode="after")
    @classmethod
    def validate_request_topic(cls, topic: str) -> str:
        """Validate request topic suffix against ONEX naming convention."""
        # Import here to avoid circular import at module load time
        from omnibase_core.validation import validate_topic_suffix

        result = validate_topic_suffix(topic)
        if not result.is_valid:
            raise ValueError(f"Invalid topic suffix '{topic}': {result.error}")
        return topic

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts for forward compatibility
        frozen=True,
        from_attributes=True,
    )
