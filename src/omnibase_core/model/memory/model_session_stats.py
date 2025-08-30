"""
Session statistics model for Universal Conversation Memory System.

Provides proper Pydantic model for session statistics and metadata,
replacing ugly Dict-based patterns with clean, type-safe ONEX-compliant
model architecture.
"""

from typing import Any, Dict

from pydantic import BaseModel, Field


class ModelSessionStats(BaseModel):
    """
    Session statistics model with proper type safety and validation.

    Replaces ugly Dict patterns with clean Pydantic model following
    ONEX architectural standards.

    Provides comprehensive session statistics and metadata with
    proper validation and type safety.
    """

    session_id: str = Field(..., description="Session identifier")
    description: str = Field(..., description="Session description")
    created_at: str = Field(..., description="ISO timestamp when session was created")
    last_used: str = Field(..., description="ISO timestamp when session was last used")
    conversation_count: int = Field(
        ..., description="Number of conversations in session"
    )
    is_current: bool = Field(
        ..., description="Whether this is the currently active session"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional session metadata"
    )

    # Additional statistics
    total_messages: int = Field(
        default=0, description="Total messages across all conversations"
    )
    avg_conversation_length: float = Field(
        default=0.0, description="Average conversation length"
    )
    session_duration_hours: float = Field(
        default=0.0, description="Hours between creation and last use"
    )

    class Config:
        """Pydantic configuration for ONEX compliance."""

        validate_assignment = True
        extra = "forbid"  # Strict validation - no extra fields allowed
