"""
Conversation filter model for Universal Conversation Memory System.

Provides proper Pydantic model for conversation filtering operations,
replacing the ugly Dict-based ConversationFilterType alias with clean,
type-safe ONEX-compliant model architecture.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, validator


class ModelTimestampRange(BaseModel):
    """Timestamp range for filtering conversations by time."""

    start: Optional[str] = Field(
        default=None, description="Start timestamp (ISO format)"
    )
    end: Optional[str] = Field(default=None, description="End timestamp (ISO format)")

    @validator("start", "end")
    def validate_timestamp_format(cls, v):
        """Validate timestamp format."""
        if v is not None:
            try:
                datetime.fromisoformat(v.replace("Z", "+00:00"))
            except ValueError:
                raise ValueError(f"Invalid timestamp format: {v}. Expected ISO format.")
        return v


class ModelConversationFilter(BaseModel):
    """
    Conversation filter model with proper type safety and validation.

    Replaces the ugly Dict[str, Union[...]] pattern with clean
    Pydantic model following ONEX architectural standards.

    Provides structured filtering capabilities for conversation search
    with proper validation and type safety.
    """

    session_id: Optional[str] = Field(
        default=None, description="Filter by specific session ID"
    )
    conversation_id: Optional[str] = Field(
        default=None, description="Filter by specific conversation ID"
    )
    tags: Optional[List[str]] = Field(
        default=None, description="Filter by conversation tags"
    )
    tools_used: Optional[List[str]] = Field(
        default=None, description="Filter by tools used in conversation"
    )
    timestamp_range: Optional[ModelTimestampRange] = Field(
        default=None, description="Filter by timestamp range"
    )

    # Semantic filtering options
    similarity_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score for search results",
    )
    content_type: Optional[str] = Field(
        default=None, description="Filter by content type"
    )
    language: Optional[str] = Field(
        default=None, description="Filter by detected language"
    )

    # Advanced filtering
    min_conversation_length: Optional[int] = Field(
        default=None, ge=1, description="Minimum conversation length in characters"
    )
    max_conversation_length: Optional[int] = Field(
        default=None, ge=1, description="Maximum conversation length in characters"
    )

    class Config:
        """Pydantic configuration for ONEX compliance."""

        validate_assignment = True
        extra = "forbid"  # Strict validation - no extra fields allowed

    @validator("max_conversation_length")
    def validate_length_range(cls, v, values):
        """Ensure max length is greater than min length."""
        min_length = values.get("min_conversation_length")
        if min_length is not None and v is not None and v < min_length:
            raise ValueError(
                "max_conversation_length must be greater than min_conversation_length"
            )
        return v

    @classmethod
    def create_empty(cls) -> "ModelConversationFilter":
        """Create an empty filter for use as default."""
        return cls()

    def to_dict(self) -> Dict:
        """Convert to dictionary format for backwards compatibility."""
        result = {}

        if self.session_id:
            result["session_id"] = self.session_id
        if self.conversation_id:
            result["conversation_id"] = self.conversation_id
        if self.tags:
            result["tags"] = self.tags
        if self.tools_used:
            result["tools"] = self.tools_used
        if self.timestamp_range:
            result["timestamp_range"] = self.timestamp_range.model_dump(
                exclude_none=True
            )

        return result
