"""
ONEX Model: Conversation State Model

Strongly typed model for conversation state management.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.model.conversation.model_conversation_context import (
    ModelConversationInteraction,
)


class ModelConversationState(BaseModel):
    """Strongly typed model for conversation state management."""

    current_session: list[ModelConversationInteraction] = Field(
        default_factory=list,
        description="Current session interactions",
    )
    session_id: str | None = Field(None, description="Current session ID")
    session_start: datetime | None = Field(None, description="Session start time")
    buffer: list[ModelConversationInteraction] = Field(
        default_factory=list,
        description="Buffered interactions waiting to be persisted",
    )
    buffer_size: int = Field(
        default=5,
        description="Number of interactions to buffer before persisting",
    )

    def clear_session(self) -> None:
        """Clear the current session."""
        self.current_session = []
        self.session_id = None
        self.session_start = None
        self.buffer = []

    def start_new_session(self, session_id: str) -> None:
        """Start a new session with the given ID."""
        self.clear_session()
        self.session_id = session_id
        self.session_start = datetime.now()

    def add_interaction(self, interaction: ModelConversationInteraction) -> None:
        """Add an interaction to the current session and buffer."""
        self.current_session.append(interaction)
        self.buffer.append(interaction)

    def should_flush_buffer(self) -> bool:
        """Check if buffer should be flushed."""
        return len(self.buffer) >= self.buffer_size

    def clear_buffer(self) -> None:
        """Clear the buffer after flushing."""
        self.buffer = []
