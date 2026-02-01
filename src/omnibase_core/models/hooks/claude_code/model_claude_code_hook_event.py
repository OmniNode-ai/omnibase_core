"""Claude Code hook event model.

Raw input schema for Claude Code hook events. This model represents the exact
structure of events received from Claude Code hooks without transformation.

This is the canonical input type - downstream services should parse events
into this model first, then transform/route as needed.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.hooks.claude_code.enum_claude_code_hook_event_type import (
    EnumClaudeCodeHookEventType,
)
from omnibase_core.models.hooks.claude_code.model_claude_code_hook_event_payload import (
    ModelClaudeCodeHookEventPayload,
)


class ModelClaudeCodeHookEvent(BaseModel):
    """Raw input schema for Claude Code hook events.

    This model captures the essential fields from Claude Code hook payloads
    without transformation. It serves as the contract between Claude Code
    and downstream processing in omniclaude/omniintelligence.

    The payload field accepts any BaseModel-derived payload. Downstream
    consumers should validate/parse payload based on event_type using
    specific payload models.

    Attributes:
        event_type: The type of hook event (from Claude Code lifecycle)
        session_id: Unique identifier for the Claude Code session (string per upstream API)
        correlation_id: Optional ID for distributed tracing across services
        timestamp_utc: When the event occurred (timezone-aware UTC)
        payload: Event-specific data as a ModelClaudeCodeHookEventPayload

    Example:
        >>> from datetime import UTC
        >>> event = ModelClaudeCodeHookEvent(
        ...     event_type=EnumClaudeCodeHookEventType.USER_PROMPT_SUBMIT,
        ...     session_id="abc123",
        ...     timestamp_utc=datetime.now(UTC),
        ...     payload=ModelClaudeCodeHookEventPayload(),
        ... )
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    event_type: EnumClaudeCodeHookEventType = Field(
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
        description="When the event occurred (must be timezone-aware, e.g., datetime.now(UTC))"
    )
    payload: ModelClaudeCodeHookEventPayload = Field(
        description="Event-specific data as a payload model"
    )

    @field_validator("timestamp_utc")
    @classmethod
    def validate_timezone_aware(cls, v: datetime) -> datetime:
        """Validate that timestamp_utc is timezone-aware."""
        if v.tzinfo is None:
            raise ValueError(
                "timestamp_utc must be timezone-aware (e.g., use datetime.now(UTC))"
            )
        return v

    def is_agentic_event(self) -> bool:
        """Check if this event is part of the agentic loop."""
        return EnumClaudeCodeHookEventType.is_agentic_loop_event(self.event_type)

    def is_session_event(self) -> bool:
        """Check if this event is a session lifecycle event."""
        return EnumClaudeCodeHookEventType.is_session_lifecycle_event(self.event_type)

    def __repr__(self) -> str:
        """Return concise representation for debugging.

        Shows event type, truncated session ID, and correlation indicator.

        Example:
            >>> repr(event)
            '<ClaudeCodeHookEvent SessionStart session=abc12345...>'
        """
        session_display = (
            self.session_id[:8] + "..." if len(self.session_id) > 8 else self.session_id
        )
        corr = " corr=..." if self.correlation_id else ""
        return f"<ClaudeCodeHookEvent {self.event_type.value} session={session_display}{corr}>"


__all__ = ["ModelClaudeCodeHookEvent"]
