"""Claude Code hook enumerations.

Enums for Claude Code hook event types, lifecycle states, and tool names.
"""

from __future__ import annotations

from omnibase_core.enums.hooks.claude_code.enum_claude_code_hook_event_type import (
    EnumClaudeCodeHookEventType,
)
from omnibase_core.enums.hooks.claude_code.enum_claude_code_session_status import (
    EnumClaudeCodeSessionStatus,
)
from omnibase_core.enums.hooks.claude_code.enum_claude_code_tool_name import (
    EnumClaudeCodeToolName,
)

__all__ = [
    "EnumClaudeCodeHookEventType",
    "EnumClaudeCodeSessionStatus",
    "EnumClaudeCodeToolName",
]
