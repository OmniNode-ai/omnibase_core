# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ModelTaskDispatch - Captures a single task dispatch event in the hierarchy.

Records the parent-to-child dispatch relationship, including the dispatched
agent type, tool scope, context budget, and timestamp. Used by the correlation
manager to track the task hierarchy that is currently flat.

Strict typing is enforced: No Any types allowed in implementation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ModelTaskDispatch(BaseModel):
    """
    Captures a single task dispatch event in the task hierarchy.

    Records the parent-child relationship when a task dispatches a sub-agent,
    including the agent type, declared tool scope, context budget, and timing.

    This model enables:
    - Tracking parent-child dispatch chains for audit
    - Recording what tools and budget were declared at dispatch time
    - Correlating dispatch events with return events
    - Building the full task tree for visualization

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Identity
    task_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this dispatch event",
    )

    parent_task_id: UUID | None = Field(
        default=None,
        description="Parent task ID (None for root-level dispatches)",
    )

    # Dispatch details
    agent_type: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Type of agent dispatched (e.g., 'onex:polymorphic-agent')",
    )

    tool_scope: list[str] = Field(
        default_factory=list,
        description="Tools declared as allowed at dispatch time",
    )

    context_budget_tokens: int | None = Field(
        default=None,
        ge=1,
        description="Context budget declared at dispatch time (None = unconstrained)",
    )

    # Correlation
    session_id: UUID | None = Field(
        default=None,
        description="Session ID from correlation manager",
    )

    correlation_id: UUID | None = Field(
        default=None,
        description="Correlation ID for tracing across dispatches",
    )

    # Timing
    dispatched_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the dispatch occurred (UTC)",
    )

    # Description
    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Human-readable description of the dispatch intent",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
        from_attributes=True,
    )


__all__ = [
    "ModelTaskDispatch",
]
