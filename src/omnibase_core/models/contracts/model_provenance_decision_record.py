# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Decision Record Model.

Provides DecisionRecord, the foundational artifact for the Decision Provenance
system. All subsequent emission, storage, and dashboard work depends on this
schema.

Design Decisions:
    - ``frozen=True``: Immutable after emission — decision events are facts,
      not mutable state. Matches repo invariant that events crossing system
      boundaries must be immutable to ensure auditability.
    - ``agent_rationale`` is nullable: Rationale is optional/assistive;
      provenance fields are mandatory.
    - ``reproducibility_snapshot`` as dict: Captures runtime state needed to
      re-derive the decision (e.g., model versions, feature flags, env vars).
    - ``decision_id`` is UUID: Follows repo convention (Use UUID for ID fields).
    - No ``datetime.now()`` defaults: Timestamps are injected by callers for
      deterministic testing. See repo invariant: "emitted_at timestamps must
      be explicitly injected".

Example::

    from datetime import datetime, timezone
    from uuid import UUID
    from omnibase_core.contracts import DecisionRecord, DecisionScore

    scores = [
        DecisionScore(
            candidate="model-a",
            score=0.92,
            breakdown={"accuracy": 0.95, "latency": 0.89},
        ),
    ]

    record = DecisionRecord(
        decision_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        decision_type="model_select",
        timestamp=datetime.now(timezone.utc),
        candidates_considered=["model-a", "model-b"],
        constraints_applied={"region": "us-east-1"},
        scoring_breakdown=scores,
        tie_breaker=None,
        selected_candidate="model-a",
        agent_rationale="model-a scores highest on accuracy",
        reproducibility_snapshot={"registry_version": "v2.1.0"},
    )

See Also:
    model_provenance_decision_score.py: The DecisionScore model used in scoring_breakdown.
    OMN-2350: Decision Provenance epic.
    OMN-2465: DecisionRecord Kafka emission (omniclaude).
    OMN-2466: DecisionRecord ingestion and storage (omniintelligence).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.model_provenance_decision_score import DecisionScore


class DecisionRecord(BaseModel):
    """Immutable record capturing a single decision event.

    The foundational artifact for the Decision Provenance system. Records
    every significant decision made during agent execution, providing full
    auditability and reproducibility.

    This model is frozen (immutable) because decision events are facts about
    what happened — they must not be altered after emission. This ensures
    audit trail integrity and matches the ONEX invariant that events crossing
    system boundaries are immutable.

    Attributes:
        decision_id: Unique UUID identifying this decision (caller-provided).
            No auto-generation — callers must supply this for reproducibility.
        decision_type: Classifier for the kind of decision made, e.g.
            ``"model_select"``, ``"workflow_route"``, ``"tool_pick"``.
        timestamp: UTC timestamp when the decision was made. No default —
            callers must inject this for deterministic testing.
        candidates_considered: Ordered list of candidate identifiers that were
            evaluated (e.g., model names, workflow IDs).
        constraints_applied: Key-value map of constraints that filtered or
            influenced the decision (e.g., ``{"region": "us-east-1"}``).
        scoring_breakdown: Per-candidate scoring details. May be empty if
            decision was deterministic (no scoring needed).
        tie_breaker: Identifier of the mechanism used to break a tie, if any.
            ``None`` if the decision was unambiguous.
        selected_candidate: The candidate that was chosen as the final
            decision output.
        agent_rationale: Optional free-text explanation of why this candidate
            was selected. Intended for human review and debugging.
        reproducibility_snapshot: Runtime state snapshot needed to re-derive
            this decision (e.g., model registry versions, feature flags).

    Example::

        from datetime import datetime, timezone
        from uuid import UUID

        record = DecisionRecord(
            decision_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            decision_type="model_select",
            timestamp=datetime(2026, 2, 21, 12, 0, 0, tzinfo=timezone.utc),
            candidates_considered=["model-a", "model-b"],
            constraints_applied={"region": "us-east-1"},
            scoring_breakdown=[],
            tie_breaker=None,
            selected_candidate="model-a",
            agent_rationale="Highest overall score",
            reproducibility_snapshot={"registry_version": "v2.1.0"},
        )
    """

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
        from_attributes=True,
    )

    decision_id: UUID = Field(
        ...,
        description=(
            "Unique UUID identifying this decision (caller-provided). "
            "No auto-generation — callers must supply for reproducibility."
        ),
    )
    decision_type: str = Field(
        ...,
        description=(
            'Classifier for the kind of decision, e.g. "model_select", '
            '"workflow_route", "tool_pick".'
        ),
    )
    timestamp: datetime = Field(
        ...,
        description=(
            "UTC timestamp when the decision was made. No default — "
            "callers must inject this for deterministic testing."
        ),
    )
    candidates_considered: list[str] = Field(
        ...,
        description="Ordered list of candidate identifiers that were evaluated.",
    )
    constraints_applied: dict[str, str] = Field(
        ...,
        description=(
            "Key-value map of constraints that filtered or influenced the "
            'decision, e.g. {"region": "us-east-1"}.'
        ),
    )
    scoring_breakdown: list[DecisionScore] = Field(
        ...,
        description=(
            "Per-candidate scoring details. May be empty if the decision "
            "was deterministic."
        ),
    )
    tie_breaker: str | None = Field(
        default=None,
        description=(
            "Identifier of the mechanism used to break a tie, if any. "
            "None if the decision was unambiguous."
        ),
    )
    selected_candidate: str = Field(
        ...,
        description="The candidate that was chosen as the final decision output.",
    )
    agent_rationale: str | None = Field(
        default=None,
        description=(
            "Optional free-text explanation of why this candidate was selected. "
            "Intended for human review and debugging."
        ),
    )
    reproducibility_snapshot: dict[str, str] = Field(
        ...,
        description=(
            "Runtime state snapshot needed to re-derive this decision "
            "(e.g., model registry versions, feature flags)."
        ),
    )


__all__ = ["DecisionRecord"]
