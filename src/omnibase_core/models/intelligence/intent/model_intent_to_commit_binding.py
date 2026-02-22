# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Commit-level causal link model for the Intent Intelligence Framework.

Represents the binding between a classified intent and a specific git commit,
enabling retrospective causal analysis of which intents produced which commits.
This binding supports traceability from user intent through tool calls to
concrete code changes.

Part of the Intent Intelligence Framework (OMN-2486).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelIntentToCommitBinding"]


class ModelIntentToCommitBinding(BaseModel):
    """Commit-level causal link between intent and code change.

    Binds a classified intent to a specific git commit, recording the tool
    calls that causally connected the intent to the resulting code change.
    Used by traceability and retrospective analysis subsystems.

    Attributes:
        intent_id: The classified intent that led to this commit.
        commit_sha: The full git commit SHA produced as an outcome.
        plan_id: Optional identifier of the execution plan that mediated
            between the intent and the commit. ``None`` if no plan was used.
        tool_call_ids: Identifiers of tool calls that causally contributed
            to producing this commit (e.g., Write, Bash, Edit calls).
        outcome_label: Human-readable label describing the commit outcome
            (e.g., ``"success"``, ``"partial"``, ``"reverted"``).
        bound_at: Timestamp when this binding was recorded (UTC).
            Callers must inject this value — no ``datetime.now()`` defaults.

    Example:
        >>> from uuid import uuid4
        >>> from datetime import UTC, datetime
        >>> binding = ModelIntentToCommitBinding(
        ...     intent_id=uuid4(),
        ...     commit_sha="a3f8c1d2e4b6789012345678901234567890abcd",
        ...     plan_id=None,
        ...     tool_call_ids=["tc-001", "tc-002", "tc-003"],
        ...     outcome_label="success",
        ...     bound_at=datetime.now(UTC),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    intent_id: UUID = Field(
        description="The classified intent that led to this commit",
    )
    commit_sha: str = Field(
        min_length=1,
        description="The full git commit SHA produced as an outcome",
    )
    plan_id: UUID | None = Field(
        default=None,
        description=(
            "Optional identifier of the execution plan that mediated between the intent "
            "and the commit. None if no plan was used."
        ),
    )
    tool_call_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Identifiers of tool calls that causally contributed to producing this commit "
            "(e.g., Write, Bash, Edit calls)"
        ),
    )
    outcome_label: str = Field(
        description=(
            "Human-readable label describing the commit outcome "
            "(e.g., 'success', 'partial', 'reverted')"
        ),
    )
    bound_at: datetime = Field(
        description=(
            "Timestamp when this binding was recorded (UTC). "
            "Callers must inject this value — no datetime.now() defaults."
        ),
    )
