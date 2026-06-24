# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Cursor hook event type.

Cursor (OmniCursor) is an interchangeable dispatcher peer to Claude Code. To keep
the two frontends behaviorally identical, Cursor shares Claude Code's canonical
hook lifecycle vocabulary rather than introducing a parallel set of event names.

OmniCursor normalizes its native hook names to the canonical values at emit time
(see OmniCursor .cursor/hooks/scripts): for example ``beforeSubmitPrompt`` ->
``UserPromptSubmit``, ``stop`` -> ``Stop``. Cursor's distinct identity is carried
by its dedicated event model (ModelCursorHookEvent), its dedicated
``cursor-hook-event.v1`` topic, its dedicated effect node, and the
``agent_source="cursor"`` provenance stamped onto downstream events — not by a
separate event-name enum.

``EnumCursorHookEventType`` is therefore an alias of EnumClaudeCodeHookEventType.
It exists as a named symbol so Cursor-side modules can import a Cursor-namespaced
type, and so the relationship can later be specialized if Cursor diverges.
"""

from __future__ import annotations

from omnibase_core.enums.hooks.claude_code.enum_claude_code_hook_event_type import (
    EnumClaudeCodeHookEventType,
)

# Alias: Cursor shares Claude Code's canonical hook lifecycle vocabulary.
EnumCursorHookEventType = EnumClaudeCodeHookEventType

__all__ = ["EnumCursorHookEventType"]
