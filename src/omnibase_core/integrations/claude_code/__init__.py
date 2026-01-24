"""Claude Code integration types.

Provides the public API for Claude Code hook event types and models.
This module re-exports internal types with user-friendly names.

Example:
    >>> from omnibase_core.integrations.claude_code import (
    ...     ClaudeCodeHookEventType,
    ...     ClaudeHookEvent,
    ...     ClaudeHookEventPayload,
    ... )
"""

from __future__ import annotations

from omnibase_core.enums.hooks.claude_code.enum_claude_code_hook_event_type import (
    EnumClaudeCodeHookEventType as ClaudeCodeHookEventType,
)
from omnibase_core.models.hooks.claude_code.model_claude_code_hook_event import (
    ModelClaudeCodeHookEvent as ClaudeHookEvent,
)
from omnibase_core.models.hooks.claude_code.model_claude_code_hook_event_payload import (
    ModelClaudeCodeHookEventPayload as ClaudeHookEventPayload,
)

__all__ = [
    "ClaudeCodeHookEventType",
    "ClaudeHookEvent",
    "ClaudeHookEventPayload",
]
