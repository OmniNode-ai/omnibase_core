"""Claude Code hook models.

Models for Claude Code hook events and payloads.
"""

from __future__ import annotations

from omnibase_core.models.hooks.claude_code.model_claude_code_hook_event import (
    ModelClaudeCodeHookEvent,
)
from omnibase_core.models.hooks.claude_code.model_claude_code_hook_event_payload import (
    ModelClaudeCodeHookEventPayload,
)

__all__ = [
    "ModelClaudeCodeHookEvent",
    "ModelClaudeCodeHookEventPayload",
]
