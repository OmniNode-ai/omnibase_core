"""
Claude Code integration types.

This module provides input-facing types for integrating with Claude Code hooks.
Types match the exact structure and naming from Claude Code's hook system.

Exported Types:
    ClaudeCodeHookEventType: The 12 lifecycle event types from Claude Code
    ClaudeHookEvent: Raw input schema for hook events
    ClaudeHookEventPayload: Base class for event payloads

Usage:
    >>> from omnibase_core.integrations.claude_code import (
    ...     ClaudeCodeHookEventType,
    ...     ClaudeHookEvent,
    ...     ClaudeHookEventPayload,
    ... )
    >>> event = ClaudeHookEvent(
    ...     event_type=ClaudeCodeHookEventType.USER_PROMPT_SUBMIT,
    ...     session_id="session-123",
    ...     timestamp_utc=datetime.now(UTC),
    ...     payload=ClaudeHookEventPayload(prompt="Help me with code"),
    ... )

See Also:
    - Claude Code Hooks documentation for event lifecycle
    - OMN-1474 for migration context
"""

from __future__ import annotations

from omnibase_core.integrations.claude_code.hook_event import ClaudeHookEvent
from omnibase_core.integrations.claude_code.hook_event_payload import (
    ClaudeHookEventPayload,
)
from omnibase_core.integrations.claude_code.hook_event_type import (
    ClaudeCodeHookEventType,
)

__all__ = [
    "ClaudeCodeHookEventType",
    "ClaudeHookEvent",
    "ClaudeHookEventPayload",
]
