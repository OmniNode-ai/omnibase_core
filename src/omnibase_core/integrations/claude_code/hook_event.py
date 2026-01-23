"""
Claude Code hook event model.

Raw input schema for Claude Code hook events. This model represents the exact
structure of events received from Claude Code hooks without transformation.

This is the canonical input type - downstream services should parse events
into this model first, then transform/route as needed.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.integrations.claude_code.hook_event_payload import (
    ClaudeHookEventPayload,
)
from omnibase_core.integrations.claude_code.hook_event_type import (
    ClaudeCodeHookEventType,
)


class ClaudeHookEvent(BaseModel):
    """
    Raw input schema for Claude Code hook events.

    This model captures the essential fields from Claude Code hook payloads
    without transformation. It serves as the integration surface between
    Claude Code and downstream processing.

    The payload field accepts any BaseModel-derived payload. Downstream
    consumers should validate/parse payload based on event_type using
    specific payload models.

    Attributes:
        event_type: The type of hook event (from Claude Code lifecycle)
        session_id: Unique identifier for the Claude Code session (string per upstream API)
        correlation_id: Optional ID for distributed tracing across services
        timestamp_utc: When the event occurred (timezone-aware UTC)
        payload: Event-specific data as a ClaudeHookEventPayload

    Example:
        >>> event = ClaudeHookEvent(
        ...     event_type=ClaudeCodeHookEventType.USER_PROMPT_SUBMIT,
        ...     session_id="abc123",
        ...     timestamp_utc=datetime.now(UTC),
        ...     payload=ClaudeHookEventPayload(prompt="Hello!"),
        ... )
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    event_type: ClaudeCodeHookEventType = Field(
        description="The type of Claude Code hook event"
    )
    # NOTE(OMN-1474): session_id is str (not UUID) per Claude Code's API contract.
    session_id: str = Field(
        description="Claude Code session identifier (string per upstream API)"
    )
    correlation_id: UUID | None = Field(
        default=None,
        description="Optional correlation ID for distributed tracing",
    )
    timestamp_utc: datetime = Field(
        description="When the event occurred (should be timezone-aware UTC)"
    )
    payload: ClaudeHookEventPayload = Field(
        description="Event-specific data as a payload model"
    )

    def is_agentic_event(self) -> bool:
        """
        Check if this event is part of the agentic loop.

        Returns:
            True if event_type is an agentic loop event, False otherwise
        """
        return ClaudeCodeHookEventType.is_agentic_loop_event(self.event_type)

    def is_session_event(self) -> bool:
        """
        Check if this event is a session lifecycle event.

        Returns:
            True if event_type is a session lifecycle event, False otherwise
        """
        return ClaudeCodeHookEventType.is_session_lifecycle_event(self.event_type)


__all__ = ["ClaudeHookEvent"]
