"""Claude Code hook event type enumeration.

Defines the 12 lifecycle events in Claude Code's hook system, matching the
exact event names used by Claude Code. This is the canonical input type for
integration with Claude Code hooks.

Reference: Claude Code Hook Lifecycle
    SessionStart -> UserPromptSubmit -> [Agentic Loop] -> Stop -> PreCompact -> SessionEnd

Agentic Loop:
    PreToolUse -> PermissionRequest -> [execution] -> PostToolUse/PostToolUseFailure
    -> SubagentStart/SubagentStop -> (repeat)

Async: Notification (can occur at any point)
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumClaudeCodeHookEventType(StrValueHelper, str, Enum):
    """Event types from Claude Code hook lifecycle.

    These values match exactly what Claude Code sends, enabling direct deserialization
    without transformation. Values use PascalCase to match Claude Code's convention.

    Lifecycle Flow:
        1. SESSION_START - Session initialization
        2. USER_PROMPT_SUBMIT - User submits a prompt
        3. [Agentic Loop begins]
           - PRE_TOOL_USE - Before tool execution
           - PERMISSION_REQUEST - Permission requested for tool
           - POST_TOOL_USE - After successful tool execution
           - POST_TOOL_USE_FAILURE - After failed tool execution
           - SUBAGENT_START - Subagent spawned
           - SUBAGENT_STOP - Subagent completed
        4. NOTIFICATION - Async notification (can occur anytime)
        5. STOP - Session stopping
        6. PRE_COMPACT - Before context compaction
        7. SESSION_END - Session terminated

    Event Categories (helper methods):
        - is_agentic_loop_event(): PRE_TOOL_USE, PERMISSION_REQUEST, POST_TOOL_USE,
          POST_TOOL_USE_FAILURE, SUBAGENT_START, SUBAGENT_STOP
        - is_session_lifecycle_event(): SESSION_START, SESSION_END, STOP, PRE_COMPACT
        - is_prompt_event(): USER_PROMPT_SUBMIT
        - is_async_event(): NOTIFICATION
    """

    # Session lifecycle
    SESSION_START = "SessionStart"
    """Session initialization event. First event in lifecycle."""

    SESSION_END = "SessionEnd"
    """Session termination event. Final event in lifecycle."""

    # Prompt lifecycle
    USER_PROMPT_SUBMIT = "UserPromptSubmit"
    """User prompt submission event. Triggers agentic processing."""

    # Tool execution lifecycle (agentic loop)
    PRE_TOOL_USE = "PreToolUse"
    """Before tool execution. Allows inspection/modification of tool call."""

    PERMISSION_REQUEST = "PermissionRequest"
    """Permission requested for tool execution. User approval may be required."""

    POST_TOOL_USE = "PostToolUse"
    """After successful tool execution. Contains tool result."""

    POST_TOOL_USE_FAILURE = "PostToolUseFailure"
    """After failed tool execution. Contains error information."""

    # Subagent lifecycle
    SUBAGENT_START = "SubagentStart"
    """Subagent spawned for delegated task."""

    SUBAGENT_STOP = "SubagentStop"
    """Subagent completed delegated task."""

    # Async events
    NOTIFICATION = "Notification"
    """Async notification event. Can occur at any point in lifecycle."""

    # Session control
    STOP = "Stop"
    """Session stop event. Precedes PreCompact and SessionEnd."""

    PRE_COMPACT = "PreCompact"
    """Before context compaction. Allows cleanup before memory reduction."""

    @classmethod
    def is_agentic_loop_event(cls, event_type: EnumClaudeCodeHookEventType) -> bool:
        """Check if the event type is part of the agentic loop."""
        return event_type in {
            cls.PRE_TOOL_USE,
            cls.PERMISSION_REQUEST,
            cls.POST_TOOL_USE,
            cls.POST_TOOL_USE_FAILURE,
            cls.SUBAGENT_START,
            cls.SUBAGENT_STOP,
        }

    @classmethod
    def is_session_lifecycle_event(
        cls, event_type: EnumClaudeCodeHookEventType
    ) -> bool:
        """Check if the event type is a session lifecycle event."""
        return event_type in {
            cls.SESSION_START,
            cls.SESSION_END,
            cls.STOP,
            cls.PRE_COMPACT,
        }

    @classmethod
    def is_prompt_event(cls, event_type: EnumClaudeCodeHookEventType) -> bool:
        """Check if the event type is a prompt submission event."""
        return event_type == cls.USER_PROMPT_SUBMIT

    @classmethod
    def is_async_event(cls, event_type: EnumClaudeCodeHookEventType) -> bool:
        """Check if the event type is an async event that can occur at any point."""
        return event_type == cls.NOTIFICATION


__all__ = ["EnumClaudeCodeHookEventType"]
