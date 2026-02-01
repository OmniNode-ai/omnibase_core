"""
ModelClaudeCodeToolRecord - Record of a tool execution during a Claude Code session.

Defines the ModelClaudeCodeToolRecord model which represents a single tool
invocation with execution metadata. Each record tracks the tool name, success
status, duration, and an optional summary for session analytics.

This is a pure data model with no side effects.

.. versionadded:: 0.6.0
    Added as part of OmniMemory Claude Code session infrastructure (OMN-1489)
"""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.utils.util_validators import ensure_timezone_aware


class ModelClaudeCodeToolRecord(BaseModel):
    """Record of a tool execution during a Claude Code session.

    Tracks individual tool executions within a session, including the tool
    name, success/failure status, execution duration, and an optional
    truncated summary of the result.

    Attributes:
        tool_execution_id: Unique identifier for this execution (auto-generated).
        emitted_at: When the tool execution completed.
        tool_name: Name of the tool that was executed.
        success: Whether the tool execution succeeded.
        duration_ms: Execution duration in milliseconds.
        summary: Truncated summary of the result (max 500 chars).
        causation_id: Links to parent event for causality tracking.

    Note:
        The summary field is intentionally truncated to 500 characters to
        avoid storing large tool outputs while maintaining enough context
        for debugging and analytics.

    Example:
        >>> from datetime import datetime, UTC
        >>> from uuid import uuid4
        >>> record = ModelClaudeCodeToolRecord(
        ...     tool_execution_id=uuid4(),
        ...     emitted_at=datetime.now(UTC),
        ...     tool_name="Read",
        ...     success=True,
        ...     duration_ms=150,
        ...     summary="Read file /src/main.py (245 lines)",
        ... )
        >>> record.success
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

    tool_execution_id: UUID = Field(
        default_factory=uuid4,
        description="Unique tool execution identifier",
    )

    emitted_at: datetime = Field(
        ...,
        description="When the tool execution completed",
    )

    # === Execution Details ===

    tool_name: str = Field(
        ...,
        min_length=1,
        description="Name of the tool that was executed",
    )

    success: bool = Field(
        ...,
        description="Whether the tool execution succeeded",
    )

    duration_ms: int = Field(
        ...,
        ge=0,
        description="Execution duration in milliseconds",
    )

    # === Result Summary ===

    summary: str | None = Field(
        default=None,
        max_length=500,
        description="Truncated summary of the result",
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
        status = "ok" if self.success else "failed"
        return f"ToolRecord({self.tool_name}: {status}, {self.duration_ms}ms)"

    def __repr__(self) -> str:
        return (
            f"ModelClaudeCodeToolRecord(tool_execution_id={self.tool_execution_id!r}, "
            f"tool_name={self.tool_name!r}, "
            f"success={self.success!r}, "
            f"duration_ms={self.duration_ms!r})"
        )


__all__ = ["ModelClaudeCodeToolRecord"]
