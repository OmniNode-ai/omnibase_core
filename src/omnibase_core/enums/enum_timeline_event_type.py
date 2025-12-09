"""
Timeline Event Type Enumeration

ONEX-compatible enumeration for unified timeline dashboard event types.
Supports user messages, tool executions, and Claude responses in chronological timeline.
"""

from enum import Enum


class EnumTimelineEventType(str, Enum):
    """
    Timeline event types for unified dashboard.

    Represents the three main event types in Claude Code conversation flows:
    - USER_MESSAGE: User prompts and requests
    - TOOL_EXECUTION: Tool calls with parameters and results
    - CLAUDE_RESPONSE: Claude's responses to user requests
    """

    USER_MESSAGE = "USER_MESSAGE"
    TOOL_EXECUTION = "TOOL_EXECUTION"
    CLAUDE_RESPONSE = "CLAUDE_RESPONSE"
