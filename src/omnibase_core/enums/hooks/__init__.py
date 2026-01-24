"""Hook-related enumerations.

Contains enums for external hook systems that integrate with OmniNode.
"""

from __future__ import annotations

from omnibase_core.enums.hooks.claude_code.enum_claude_code_hook_event_type import (
    EnumClaudeCodeHookEventType,
)
from omnibase_core.enums.hooks.claude_code.enum_claude_code_session_status import (
    EnumClaudeCodeSessionStatus,
)

__all__ = ["EnumClaudeCodeHookEventType", "EnumClaudeCodeSessionStatus"]
