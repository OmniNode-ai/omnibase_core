# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Hook-related enumerations.

Contains enums for external hook systems that integrate with OmniNode.
"""

from __future__ import annotations

from omnibase_core.enums.hooks.claude_code.enum_claude_code_hook_event_type import (
    EnumClaudeCodeHookEventType,
)
from omnibase_core.enums.hooks.claude_code.enum_claude_code_session_outcome import (
    EnumClaudeCodeSessionOutcome,
)
from omnibase_core.enums.hooks.claude_code.enum_claude_code_session_status import (
    EnumClaudeCodeSessionStatus,
)
from omnibase_core.enums.hooks.cursor.enum_cursor_hook_event_type import (
    EnumCursorHookEventType,
)
from omnibase_core.enums.hooks.enum_agent_source import EnumAgentSource

__all__ = [
    "EnumAgentSource",
    "EnumClaudeCodeHookEventType",
    "EnumClaudeCodeSessionOutcome",
    "EnumClaudeCodeSessionStatus",
    "EnumCursorHookEventType",
]
