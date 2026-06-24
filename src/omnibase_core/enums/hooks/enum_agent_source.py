# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Agent source for hook-derived events.

Identifies which interchangeable dispatcher frontend produced a hook event.
Claude Code and OmniCursor are behaviorally identical peers that share the same
canonical hook lifecycle vocabulary (see EnumClaudeCodeHookEventType /
EnumCursorHookEventType); ``EnumAgentSource`` is the provenance stamp that keeps
their downstream events distinguishable once normalized onto the bus.

This is the canonical type for the ``agent_source`` seam carried through hook
dispatch and routing. It deliberately enumerates only the supported frontends —
add a member when a new dispatcher peer is introduced.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import UtilStrValueHelper


@unique
class EnumAgentSource(UtilStrValueHelper, str, Enum):
    """Frontend dispatcher that produced a hook event.

    Stamped onto downstream events as provenance so Claude Code and Cursor
    paths remain distinguishable after normalization onto shared topics.
    """

    CLAUDE = "claude"
    CURSOR = "cursor"


__all__ = ["EnumAgentSource"]
