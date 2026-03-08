# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed payload model for UserPromptSubmit events.

Provides a strongly-typed payload for UserPromptSubmit events from Claude Code
hooks. The ``prompt`` field is required, ensuring fail-fast behavior when the
prompt is missing instead of silently defaulting to an empty string.

.. versionadded:: 0.5.0
    Added as part of typed hook payloads (OMN-1491)
"""

from __future__ import annotations

from pydantic import Field

from omnibase_core.models.hooks.claude_code.model_claude_code_hook_event_payload import (
    ModelClaudeCodeHookEventPayload,
)


class ModelUserPromptSubmitPayload(ModelClaudeCodeHookEventPayload):
    """Typed payload for UserPromptSubmit hook events.

    Extends the base payload with a required ``prompt`` field. This replaces
    the previous pattern of extracting the prompt from ``model_extra``, giving
    type safety and fail-fast validation.

    Inherits ``extra="allow"`` from the base class so that new upstream fields
    from Claude Code do not break deserialization.

    Attributes:
        prompt: The user prompt text submitted to Claude Code. Required.

    Example:
        Direct construction::

            >>> payload = ModelUserPromptSubmitPayload(prompt="Explain this code")
            >>> payload.prompt
            'Explain this code'

        From raw hook data::

            >>> data = {"prompt": "Fix the bug", "session_id": "abc"}
            >>> payload = ModelUserPromptSubmitPayload.model_validate(data)
            >>> payload.prompt
            'Fix the bug'

    .. versionadded:: 0.5.0
        Added as part of typed hook payloads (OMN-1491)
    """

    prompt: str = Field(
        description="The user prompt text submitted to Claude Code",
    )


__all__ = ["ModelUserPromptSubmitPayload"]
