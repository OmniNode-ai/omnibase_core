"""
ModelClaudeCodeSessionSnapshot - Immutable snapshot of a Claude Code session.

Defines the ModelClaudeCodeSessionSnapshot model which represents a complete
snapshot of a Claude Code session for OmniMemory storage. This model composes
ModelMemorySnapshot for core memory state (decisions, failures, costs) and adds
Claude Code-specific session data (prompts, tools, lifecycle state).

This model is consumed by:
- omniclaude: Session storage and retrieval
- omnidash: Session display and analytics
- omniintelligence: Pattern learning from sessions

This is a pure data model with no side effects.

.. versionadded:: 0.6.0
    Added as part of OmniMemory Claude Code session infrastructure (OMN-1489)
"""

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.hooks.claude_code.enum_claude_code_session_status import (
    EnumClaudeCodeSessionStatus,
)
from omnibase_core.models.omnimemory.model_claude_code_prompt_record import (
    ModelClaudeCodePromptRecord,
)
from omnibase_core.models.omnimemory.model_claude_code_tool_record import (
    ModelClaudeCodeToolRecord,
)
from omnibase_core.models.omnimemory.model_memory_snapshot import ModelMemorySnapshot
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.utils.util_validators import ensure_timezone_aware


class ModelClaudeCodeSessionSnapshot(BaseModel):
    """Immutable snapshot of a Claude Code session for OmniMemory storage.

    Represents a complete point-in-time snapshot of a Claude Code session,
    combining core memory state (via ModelMemorySnapshot composition) with
    Claude Code-specific session data including prompts, tool executions,
    and lifecycle metadata.

    Attributes:
        snapshot_id: Unique identifier for this snapshot (auto-generated).
        session_id: Claude Code session identifier (string per API).
        correlation_id: Links related events across services.
        memory_snapshot: Composed core memory state (decisions, failures, costs).
        status: Current session lifecycle status.
        started_at: When the session started.
        ended_at: When the session ended (if applicable).
        duration_seconds: Total session duration in seconds.
        working_directory: Filesystem path where session is running.
        git_branch: Current git branch (if in a git repository).
        hook_source: How the session was initiated.
        end_reason: Why the session ended (if applicable).
        prompts: Immutable tuple of prompt records.
        tools: Immutable tuple of tool execution records.
        prompt_count: Total number of prompts in session.
        tool_count: Total number of tool executions in session.
        tools_used_count: Number of unique tools used in session.
        last_event_at: Timestamp of most recent event.
        event_count: Total number of events processed.
        schema_version: Schema version for serialization format tracking.

    Note:
        This model is frozen (immutable). Session updates should create new
        snapshots rather than modifying existing ones, enabling full lineage
        tracking and audit trails.

    Note:
        The session_id uses string type (not UUID) to match the Claude Code
        API's session identifier format.

    Example:
        >>> from datetime import datetime, UTC
        >>> from uuid import uuid4
        >>> from omnibase_core.enums.enum_subject_type import EnumSubjectType
        >>> from omnibase_core.enums.hooks.claude_code import EnumClaudeCodeSessionStatus
        >>> from omnibase_core.models.omnimemory import (
        ...     ModelCostLedger,
        ...     ModelMemorySnapshot,
        ...     ModelSubjectRef,
        ... )
        >>> # Create base memory snapshot
        >>> subject = ModelSubjectRef(
        ...     subject_type=EnumSubjectType.AGENT,
        ...     subject_id=uuid4(),
        ... )
        >>> ledger = ModelCostLedger(budget_total=100.0)
        >>> memory = ModelMemorySnapshot(subject=subject, cost_ledger=ledger)
        >>> # Create session snapshot
        >>> snapshot = ModelClaudeCodeSessionSnapshot(
        ...     session_id="session-abc123",
        ...     memory_snapshot=memory,
        ...     status=EnumClaudeCodeSessionStatus.ACTIVE,
        ...     working_directory="/path/to/project",
        ...     hook_source="startup",
        ...     last_event_at=datetime.now(UTC),
        ... )
        >>> snapshot.prompt_count
        0

    .. versionadded:: 0.6.0
        Added as part of OmniMemory Claude Code session infrastructure (OMN-1489)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    # === Identity ===

    snapshot_id: UUID = Field(
        default_factory=uuid4,
        description="Unique snapshot identifier",
    )

    # string-id-ok: Claude Code API uses string session identifiers, not UUIDs
    session_id: str = Field(
        ...,
        min_length=1,
        description="Claude Code session identifier (string per API)",
    )

    correlation_id: UUID | None = Field(
        default=None,
        description="Links related events across services",
    )

    # === Core Memory (composition) ===

    memory_snapshot: ModelMemorySnapshot = Field(
        ...,
        description="Composed core memory state (decisions, failures, costs)",
    )

    # === Session Lifecycle ===

    status: EnumClaudeCodeSessionStatus = Field(
        ...,
        description="Current session lifecycle status",
    )

    started_at: datetime | None = Field(
        default=None,
        description="When the session started",
    )

    ended_at: datetime | None = Field(
        default=None,
        description="When the session ended",
    )

    duration_seconds: float | None = Field(
        default=None,
        ge=0.0,
        description="Total session duration in seconds",
    )

    # === Context ===

    working_directory: str = Field(
        ...,
        min_length=1,
        description="Filesystem path where session is running",
    )

    git_branch: str | None = Field(
        default=None,
        description="Current git branch (if in a git repository)",
    )

    hook_source: str = Field(
        ...,
        description="How the session was initiated (startup|resume|compact|synthetic)",
    )

    end_reason: str | None = Field(
        default=None,
        description="Why the session ended",
    )

    # === Collections (immutable tuples) ===

    prompts: tuple[ModelClaudeCodePromptRecord, ...] = Field(
        default=(),
        description="Prompt records for this session",
    )

    tools: tuple[ModelClaudeCodeToolRecord, ...] = Field(
        default=(),
        description="Tool execution records for this session",
    )

    # === Metrics ===

    prompt_count: int = Field(
        default=0,
        ge=0,
        description="Total number of prompts in session",
    )

    tool_count: int = Field(
        default=0,
        ge=0,
        description="Total number of tool executions in session",
    )

    tools_used_count: int = Field(
        default=0,
        ge=0,
        description="Number of unique tools used in session",
    )

    # === Aggregation Metadata ===

    last_event_at: datetime = Field(
        ...,
        description="Timestamp of most recent event",
    )

    event_count: int = Field(
        default=0,
        ge=0,
        description="Total number of events processed",
    )

    schema_version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Schema version for serialization format tracking",
    )

    # === Validators ===

    @field_validator("started_at", "ended_at", "last_event_at", mode="before")
    @classmethod
    def validate_timestamps_have_timezone(cls, v: datetime | None) -> datetime | None:
        """Validate timestamps are timezone-aware using shared utility."""
        if v is None:
            return None
        return ensure_timezone_aware(v, "timestamp")

    # === Utility Properties ===

    @property
    def is_active(self) -> bool:
        """Check if the session is currently active."""
        return self.status.is_active()

    @property
    def total_decisions(self) -> int:
        """Get total decisions from composed memory snapshot."""
        return self.memory_snapshot.decision_count

    @property
    def total_failures(self) -> int:
        """Get total failures from composed memory snapshot."""
        return self.memory_snapshot.failure_count

    @property
    def total_cost(self) -> float:
        """Get total cost from composed memory snapshot."""
        return self.memory_snapshot.cost_ledger.total_spent

    # === Utility Methods ===

    def __str__(self) -> str:
        status_str = f"status={self.status}"
        duration = f", {self.duration_seconds:.1f}s" if self.duration_seconds else ""
        return (
            f"SessionSnapshot({self.session_id[:12]}...: "
            f"{status_str}, prompts={self.prompt_count}, "
            f"tools={self.tool_count}{duration})"
        )

    def __repr__(self) -> str:
        return (
            f"ModelClaudeCodeSessionSnapshot(snapshot_id={self.snapshot_id!r}, "
            f"session_id={self.session_id!r}, "
            f"status={self.status!r}, "
            f"prompt_count={self.prompt_count!r}, "
            f"tool_count={self.tool_count!r})"
        )


__all__ = ["ModelClaudeCodeSessionSnapshot"]
