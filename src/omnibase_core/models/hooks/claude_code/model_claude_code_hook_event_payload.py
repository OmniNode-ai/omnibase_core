"""Claude Code hook event payload base class.

Provides a base model for event-specific payloads from Claude Code hooks.
Uses extra="allow" to accept new fields from Claude Code without breaking.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelClaudeCodeHookEventPayload(BaseModel):
    """Base class for Claude Code hook event payloads.

    Downstream consumers should define specific payload models that inherit
    from this base class for their event types.

    Uses extra="allow" to accept any fields from Claude Code, allowing
    new fields to be added without breaking existing consumers.

    Example:
        >>> class PromptSubmitPayload(ModelClaudeCodeHookEventPayload):
        ...     prompt: str
        ...     prompt_length: int
        >>>
        >>> payload = PromptSubmitPayload(prompt="Hello", prompt_length=5)
    """

    # NOTE(OMN-1474): extra="allow" accepts new fields from Claude Code hooks.
    # This is intentional for external hook payloads receiving upstream data.
    model_config = ConfigDict(
        frozen=True,
        extra="allow",
        from_attributes=True,
    )


__all__ = ["ModelClaudeCodeHookEventPayload"]
