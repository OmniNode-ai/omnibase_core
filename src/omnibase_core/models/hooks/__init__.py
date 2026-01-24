"""Hook-related models.

Contains models for external hook systems that integrate with OmniNode.
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
