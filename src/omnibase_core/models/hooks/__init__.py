# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

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
from omnibase_core.models.hooks.claude_code.model_claude_code_session_outcome import (
    ModelClaudeCodeSessionOutcome,
)
from omnibase_core.models.hooks.claude_code.model_user_prompt_submit_payload import (
    ModelUserPromptSubmitPayload,
)
from omnibase_core.models.hooks.cursor.model_cursor_hook_event import (
    ModelCursorHookEvent,
)
from omnibase_core.models.hooks.cursor.model_cursor_hook_event_payload import (
    ModelCursorHookEventPayload,
)
from omnibase_core.utils.util_parse_hook_payload import (
    get_payload_type,
    parse_hook_payload,
)

__all__ = [
    "ModelClaudeCodeHookEvent",
    "ModelClaudeCodeHookEventPayload",
    "ModelClaudeCodeSessionOutcome",
    "ModelCursorHookEvent",
    "ModelCursorHookEventPayload",
    "ModelUserPromptSubmitPayload",
    "get_payload_type",
    "parse_hook_payload",
]
