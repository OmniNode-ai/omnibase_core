"""
Reply Topics Model for request-response patterns.

Defines the topic suffixes for completed and failed responses in
request-response communication patterns within the ONEX event bus.

Strict typing is enforced: No Any types allowed in implementation.
"""

from __future__ import annotations

__all__ = ["ModelReplyTopics"]

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelReplyTopics(BaseModel):
    """
    Reply topic configuration for request-response patterns.

    Defines the topic suffixes used for publishing responses back to
    requestors. Both completed and failed topic suffixes are required
    and must comply with ONEX topic naming conventions.

    Strict typing is enforced: No Any types allowed in implementation.
    """

    completed: str = Field(
        ...,
        description="Topic suffix for successful responses (ONEX naming convention required)",
    )

    failed: str = Field(
        ...,
        description="Topic suffix for failure responses (ONEX naming convention required)",
    )

    @field_validator("completed", "failed", mode="after")
    @classmethod
    def validate_topic_suffixes(cls, topic: str) -> str:
        """Validate topic suffix against ONEX naming convention."""
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
