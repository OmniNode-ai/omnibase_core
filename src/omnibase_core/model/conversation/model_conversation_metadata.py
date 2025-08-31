"""
Model for conversation metadata.

Provides strongly typed metadata structures for conversation capture and storage.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.model.conversation.model_conversation_session_summary import (
    ModelConversationSessionSummary,
)


class ModelConversationMetadata(BaseModel):
    """Model for conversation metadata."""

    session_id: str = Field(description="Unique session identifier")
    session_start: datetime = Field(description="When the session started")
    interaction_count: int = Field(description="Number of interactions in session")
    task_type: str | None = Field(default=None, description="Type of task")
    domain: str | None = Field(default=None, description="Domain of the task")
    complexity: str | None = Field(default=None, description="Task complexity level")
    tools_count: int = Field(default=0, description="Total number of tools used")
    interaction_duration_ms: float = Field(
        default=0.0,
        description="Duration of the interaction in milliseconds",
    )
    session_summary: ModelConversationSessionSummary | None = Field(
        default=None,
        description="Session summary statistics",
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}
