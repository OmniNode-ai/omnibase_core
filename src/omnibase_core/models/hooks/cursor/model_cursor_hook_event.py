# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Cursor IDE hook event model.

Raw input schema for Cursor hook events. This model represents the structure of
events received from the OmniCursor plugin's hooks. It mirrors
ModelClaudeCodeHookEvent so the two platforms are interchangeable dispatchers
into the OmniNode stack, while remaining a distinct, first-class Cursor type.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.hooks.cursor.enum_cursor_hook_event_type import (
    EnumCursorHookEventType,
)
from omnibase_core.models.hooks.cursor.model_cursor_hook_event_payload import (
    ModelCursorHookEventPayload,
)


class ModelCursorHookEvent(BaseModel):
    """Raw input schema for Cursor IDE hook events.

    This model captures the essential fields from Cursor hook payloads. It is
    the contract between the OmniCursor plugin and downstream processing in
    omniintelligence. The shape intentionally matches ModelClaudeCodeHookEvent
    (session_id, correlation_id, timestamp_utc, payload) so the shared
    intelligence pipeline can be reused via event-type translation.

    Attributes:
        event_type: The type of Cursor hook event.
        session_id: Cursor session/conversation identifier (string).
        correlation_id: Optional ID for distributed tracing across services.
        timestamp_utc: When the event occurred (timezone-aware UTC).
        payload: Event-specific data as a ModelCursorHookEventPayload.

    Example:
        >>> from datetime import UTC, datetime
        >>> event = ModelCursorHookEvent(
        ...     event_type=EnumCursorHookEventType.USER_PROMPT_SUBMIT,
        ...     session_id="abc123",
        ...     timestamp_utc=datetime.now(UTC),
        ...     payload=ModelCursorHookEventPayload(),
        ... )
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    event_type: EnumCursorHookEventType = Field(
        description="The type of Cursor IDE hook event"
    )
    session_id: str = Field(
        description="Cursor session identifier (string per Cursor plugin API)"
    )
    correlation_id: UUID | None = Field(
        default=None,
        description="Optional correlation ID for distributed tracing",
    )
    timestamp_utc: datetime = Field(
        description="When the event occurred (must be timezone-aware, e.g., datetime.now(UTC))"
    )
    payload: ModelCursorHookEventPayload = Field(
        description="Event-specific data as a payload model"
    )
    agent_source: str = Field(
        default="cursor",
        description=(
            "Originating dispatcher frontend; always 'cursor' for this model. "
            "Propagated as provenance onto downstream events so Cursor and Claude "
            "intents remain distinguishable on shared topics."
        ),
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

    def __repr__(self) -> str:
        """Return concise representation for debugging."""
        session_display = (
            self.session_id[:8] + "..." if len(self.session_id) > 8 else self.session_id
        )
        corr = " corr=..." if self.correlation_id else ""
        return (
            f"<CursorHookEvent {self.event_type.value} session={session_display}{corr}>"
        )


__all__ = ["ModelCursorHookEvent"]
