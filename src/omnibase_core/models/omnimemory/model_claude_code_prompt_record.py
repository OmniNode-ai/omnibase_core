"""
ModelClaudeCodePromptRecord - Record of a prompt submitted during a Claude Code session.

Defines the ModelClaudeCodePromptRecord model which represents a single prompt
submission with metadata for session tracking. The prompt_preview is truncated
and sanitized to avoid storing sensitive content while maintaining auditability.

This is a pure data model with no side effects.

.. versionadded:: 0.6.0
    Added as part of OmniMemory Claude Code session infrastructure (OMN-1489)
"""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.utils.util_validators import ensure_timezone_aware


class ModelClaudeCodePromptRecord(BaseModel):
    """Record of a prompt submitted during a Claude Code session.

    Tracks individual prompts within a session, including a truncated preview
    for auditability, detected intent from routing, and causation tracking
    for correlating prompts with downstream tool executions.

    Attributes:
        prompt_id: Unique identifier for this prompt (auto-generated).
        emitted_at: When the prompt was submitted.
        prompt_preview: Truncated, sanitized preview (max 100 chars).
        prompt_length: Full length of the original prompt.
        detected_intent: Intent classification from routing analysis.
        causation_id: Links to parent event for causality tracking.

    Note:
        The prompt_preview is intentionally truncated to 100 characters to
        avoid storing potentially sensitive information while maintaining
        enough context for debugging and analytics.

    Example:
        >>> from datetime import datetime, UTC
        >>> from uuid import uuid4
        >>> record = ModelClaudeCodePromptRecord(
        ...     prompt_id=uuid4(),
        ...     emitted_at=datetime.now(UTC),
        ...     prompt_preview="Fix the authentication bug in...",
        ...     prompt_length=256,
        ...     detected_intent="bug_fix",
        ... )
        >>> len(record.prompt_preview) <= 100
        True

    .. versionadded:: 0.6.0
        Added as part of OmniMemory Claude Code session infrastructure (OMN-1489)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    # === Identity ===

    prompt_id: UUID = Field(
        default_factory=uuid4,
        description="Unique prompt identifier",
    )

    emitted_at: datetime = Field(
        ...,
        description="When the prompt was submitted",
    )

    # === Content (sanitized) ===

    prompt_preview: str = Field(
        ...,
        max_length=100,
        description="Truncated, sanitized preview of the prompt",
    )

    prompt_length: int = Field(
        ...,
        ge=0,
        description="Full length of the original prompt",
    )

    # === Analysis ===

    detected_intent: str | None = Field(
        default=None,
        description="Intent classification from routing analysis",
    )

    # === Causation ===

    causation_id: UUID | None = Field(
        default=None,
        description="Links to parent event for causality tracking",
    )

    # === Validators ===

    @field_validator("emitted_at")
    @classmethod
    def validate_emitted_at_has_timezone(cls, v: datetime) -> datetime:
        """Validate emitted_at is timezone-aware using shared utility."""
        return ensure_timezone_aware(v, "emitted_at")

    # === Utility Methods ===

    def __str__(self) -> str:
        intent = f", intent={self.detected_intent}" if self.detected_intent else ""
        return f"PromptRecord(len={self.prompt_length}{intent})"

    def __repr__(self) -> str:
        return (
            f"ModelClaudeCodePromptRecord(prompt_id={self.prompt_id!r}, "
            f"prompt_length={self.prompt_length!r}, "
            f"detected_intent={self.detected_intent!r})"
        )


__all__ = ["ModelClaudeCodePromptRecord"]
