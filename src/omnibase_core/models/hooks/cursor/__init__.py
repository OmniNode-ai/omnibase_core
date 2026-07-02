# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Cursor IDE hook models.

Models for Cursor IDE hook events and payloads emitted by the OmniCursor plugin.
"""

from __future__ import annotations

from omnibase_core.models.hooks.cursor.model_cursor_hook_event import (
    ModelCursorHookEvent,
)
from omnibase_core.models.hooks.cursor.model_cursor_hook_event_payload import (
    ModelCursorHookEventPayload,
)

__all__ = [
    "ModelCursorHookEvent",
    "ModelCursorHookEventPayload",
]
