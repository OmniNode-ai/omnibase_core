"""
Integrations module for external system type definitions.

This module provides input-facing types for integrating with external systems.
Types here represent the "integration surface" - canonical input schemas that
match external system contracts without transformation.

Submodules:
    claude_code: Types for Claude Code hook events
"""

from __future__ import annotations

# Re-export claude_code types at integrations level for convenience
from omnibase_core.integrations.claude_code import (
    ClaudeCodeHookEventType,
    ClaudeHookEvent,
    ClaudeHookEventPayload,
)

__all__ = [
    "ClaudeCodeHookEventType",
    "ClaudeHookEvent",
    "ClaudeHookEventPayload",
]
