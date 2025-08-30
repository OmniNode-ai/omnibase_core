"""
Model for conversation session summary statistics.

Provides strongly typed session summary data for conversation metadata.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelConversationSessionSummary(BaseModel):
    """Model for conversation session summary statistics."""

    successful_interactions: int = Field(
        default=0, description="Number of successful interactions"
    )
    success_rate: float = Field(
        default=0.0, description="Success rate as percentage (0.0-1.0)"
    )
    unique_tools_used: List[str] = Field(
        default_factory=list, description="List of unique tools used in session"
    )
    session_duration_hours: float = Field(
        default=0.0, description="Session duration in hours"
    )
    conversation_topics: List[str] = Field(
        default_factory=list, description="List of conversation topics/contexts"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if summary generation failed"
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {float: lambda v: round(v, 4)}
