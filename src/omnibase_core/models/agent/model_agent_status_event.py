# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Agent status event model for real-time agent visibility (OMN-1847).

GI-1 (Global Invariant): All status events are OBSERVATIONAL. They must never
directly cause state mutation without passing through a reducer.

Note: This is a status EVENT model distinct from ModelAgentStatus in
models/core/, which is a monitoring/resource model.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.decorators.decorator_allow_dict_any import allow_dict_any
from omnibase_core.enums.enum_agent_state import EnumAgentState


@allow_dict_any(
    reason="Agent status event metadata accepts arbitrary key-value pairs for "
    "extensible observability context. This is explicitly the extension point "
    "for downstream consumers to attach domain-specific metadata."
)
class ModelAgentStatusEvent(BaseModel):
    """Immutable status event reporting the observable state of an agent.

    Status events are observational snapshots emitted by an agent to describe
    its current lifecycle state. They flow through the event bus and must never
    directly mutate system state — all state changes pass through a reducer.

    Attributes:
        id: Unique event ID (auto-generated).
        correlation_id: Correlation ID for distributed tracing.
        agent_name: Name of the reporting agent.
        session_id: Session ID for intra-session ordering.
        state: Current agent state from EnumAgentState.
        status_schema_version: Schema version (default 1, increment on breaking change).
        message: Human-readable status message.
        progress: Optional progress indicator in range [0.0, 1.0].
        current_phase: Optional current workflow phase label.
        current_task: Optional description of the current task.
        blocking_reason: Optional reason the agent is blocked (state == BLOCKED).
        created_at: Timestamp of event creation. Must be injected explicitly.
        metadata: Additional metadata key-value pairs.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique event ID (auto-generated)",
    )
    correlation_id: UUID = Field(
        description="Correlation ID for distributed tracing",
    )
    agent_name: str = Field(
        description="Name of the reporting agent",
    )
    session_id: str = Field(  # string-id-ok: session IDs are opaque string tokens from external systems, not UUIDs
        description="Session ID for intra-session event ordering",
    )
    state: EnumAgentState = Field(
        description="Current agent lifecycle state",
    )
    status_schema_version: int = Field(
        default=1,
        description="Schema version; increment on breaking field changes",
        ge=1,
    )
    message: str = Field(
        description="Human-readable status message",
    )
    progress: float | None = Field(
        default=None,
        description="Optional progress indicator in [0.0, 1.0]; monotonic within a task",
    )
    current_phase: str | None = Field(
        default=None,
        description="Current workflow phase label",
    )
    current_task: str | None = Field(
        default=None,
        description="Description of the current task being executed",
    )
    blocking_reason: str | None = Field(
        default=None,
        description="Reason the agent is blocked; populated when state == BLOCKED",
    )
    created_at: datetime = Field(
        description="Timestamp of event creation. Must be injected explicitly; no default.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata key-value pairs",
    )

    @field_validator("progress")
    @classmethod
    def validate_progress_range(cls, v: float | None) -> float | None:
        """Ensure progress is in [0.0, 1.0] when provided."""
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError(f"progress must be in range [0.0, 1.0], got {v!r}")
        return v


__all__ = ["ModelAgentStatusEvent"]
