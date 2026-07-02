# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Cursor hook event payload.

Cursor (OmniCursor) is an interchangeable dispatcher peer to Claude Code and
shares the same payload base so the two frontends can flow through the same
intelligence pipeline. ``ModelCursorHookEventPayload`` is therefore an alias of
ModelClaudeCodeHookEventPayload (extra="allow" base for event-specific payloads).

Cursor's distinct identity is carried by ModelCursorHookEvent, its dedicated
topic/node, and the ``agent_source="cursor"`` provenance — not by a separate
payload base class. The alias exists so Cursor-side modules can import a
Cursor-namespaced type and so it can later be specialized if Cursor diverges.
"""

from __future__ import annotations

from omnibase_core.models.hooks.claude_code.model_claude_code_hook_event_payload import (
    ModelClaudeCodeHookEventPayload,
)

# Alias: Cursor shares Claude Code's hook payload base.
ModelCursorHookEventPayload = ModelClaudeCodeHookEventPayload

__all__ = ["ModelCursorHookEventPayload"]
