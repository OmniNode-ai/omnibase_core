"""
Session data model for Universal Conversation Memory System.

Provides proper Pydantic model for session information storage,
replacing the ugly Dict-based SessionDataType alias with clean,
type-safe ONEX-compliant model architecture.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ModelSessionData(BaseModel):
    """
    Session data model with proper type safety and validation.

    Replaces the ugly Dict[str, Union[...]] pattern with clean
    Pydantic model following ONEX architectural standards.

    All session information is properly typed and validated,
    providing better IDE support and runtime safety.
    """

    id: str = Field(..., description="Unique session identifier")
    description: str = Field(..., description="Human-readable session description")
    created_at: str = Field(..., description="ISO timestamp when session was created")
    last_used: str = Field(..., description="ISO timestamp when session was last used")
    conversation_count: int = Field(
        default=0,
        description="Number of conversations in this session",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional session metadata",
    )

    # Optional fields for enhanced session management
    tags: list[str] | None = Field(
        default=None,
        description="Tags for categorizing the session",
    )
    project_name: str | None = Field(
        default=None,
        description="Associated project name",
    )
    priority: int | None = Field(default=None, description="Session priority level")
    archived: bool = Field(default=False, description="Whether session is archived")

    class Config:
        """Pydantic configuration for ONEX compliance."""

        json_encoders = {datetime: lambda v: v.isoformat()}
        validate_assignment = True
        extra = "forbid"  # Strict validation - no extra fields allowed
