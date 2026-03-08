# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Payload parser for Claude Code hook events.

Maps event types to their typed payload models and provides a helper to
parse raw payload dicts into the correct typed model based on event_type.

.. versionadded:: 0.5.0
    Added as part of typed hook payloads (OMN-1491)
"""

from __future__ import annotations

from typing import Any

from omnibase_core.enums.hooks.claude_code.enum_claude_code_hook_event_type import (
    EnumClaudeCodeHookEventType,
)
from omnibase_core.models.hooks.claude_code.model_claude_code_hook_event_payload import (
    ModelClaudeCodeHookEventPayload,
)
from omnibase_core.models.hooks.claude_code.model_user_prompt_submit_payload import (
    ModelUserPromptSubmitPayload,
)

# Registry mapping event types to their typed payload classes.
# Event types not listed here fall back to the base payload class.
_PAYLOAD_TYPE_REGISTRY: dict[
    EnumClaudeCodeHookEventType, type[ModelClaudeCodeHookEventPayload]
] = {
    EnumClaudeCodeHookEventType.USER_PROMPT_SUBMIT: ModelUserPromptSubmitPayload,
}


def parse_hook_payload(
    event_type: EnumClaudeCodeHookEventType,
    data: dict[str, Any],
) -> ModelClaudeCodeHookEventPayload:
    """Parse raw payload data into the typed model for the given event type.

    Looks up the event type in the payload registry and validates the data
    against the corresponding typed model. Falls back to the base
    ``ModelClaudeCodeHookEventPayload`` for event types without a registered
    typed payload.

    Args:
        event_type: The Claude Code hook event type.
        data: Raw payload data dict from the hook event.

    Returns:
        A validated payload model instance. For ``USER_PROMPT_SUBMIT``, this
        will be a ``ModelUserPromptSubmitPayload`` with a typed ``prompt``
        field. For other event types, this will be the base payload class.

    Raises:
        pydantic.ValidationError: If the data fails validation against the
            typed payload model (e.g., missing required ``prompt`` field for
            ``UserPromptSubmit`` events).

    Example:
        Parsing a UserPromptSubmit payload::

            >>> from omnibase_core.enums.hooks.claude_code import EnumClaudeCodeHookEventType
            >>> payload = parse_hook_payload(
            ...     EnumClaudeCodeHookEventType.USER_PROMPT_SUBMIT,
            ...     {"prompt": "Hello"},
            ... )
            >>> isinstance(payload, ModelUserPromptSubmitPayload)
            True
            >>> payload.prompt
            'Hello'

        Parsing an unregistered event type falls back to base::

            >>> payload = parse_hook_payload(
            ...     EnumClaudeCodeHookEventType.SESSION_START,
            ...     {"some_field": "value"},
            ... )
            >>> isinstance(payload, ModelClaudeCodeHookEventPayload)
            True
    """
    payload_cls = _PAYLOAD_TYPE_REGISTRY.get(
        event_type, ModelClaudeCodeHookEventPayload
    )
    return payload_cls.model_validate(data)


def get_payload_type(
    event_type: EnumClaudeCodeHookEventType,
) -> type[ModelClaudeCodeHookEventPayload]:
    """Return the registered payload type for the given event type.

    Args:
        event_type: The Claude Code hook event type.

    Returns:
        The payload model class for the event type, or the base
        ``ModelClaudeCodeHookEventPayload`` if no typed payload is registered.

    Example:
        >>> get_payload_type(EnumClaudeCodeHookEventType.USER_PROMPT_SUBMIT)
        <class '...ModelUserPromptSubmitPayload'>

        >>> get_payload_type(EnumClaudeCodeHookEventType.SESSION_START)
        <class '...ModelClaudeCodeHookEventPayload'>
    """
    return _PAYLOAD_TYPE_REGISTRY.get(event_type, ModelClaudeCodeHookEventPayload)


__all__ = ["get_payload_type", "parse_hook_payload"]
