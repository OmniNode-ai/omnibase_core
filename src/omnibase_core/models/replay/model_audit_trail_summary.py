"""
ModelAuditTrailSummary - Summary statistics for enforcement decisions.

This module provides the ModelAuditTrailSummary model that aggregates
enforcement decision statistics for a replay session.

Design:
    Summary statistics provide at-a-glance understanding of:
    - Total enforcement decisions made
    - Breakdown by outcome (allowed, blocked, warned, mocked)
    - Breakdown by non-determinism source (time, random, network, etc.)
    - Breakdown by enforcement mode (strict, warn, permissive, mocked)
    - Time range of decisions
    - List of blocked effect types for quick identification

Architecture:
    The ServiceAuditTrail computes ModelAuditTrailSummary from the
    recorded entries on demand. This supports:
    - Quick session overview
    - Identification of problematic patterns
    - Compliance reporting

Thread Safety:
    ModelAuditTrailSummary is frozen (immutable) after creation, making it
    safe to share across threads.

Usage:
    .. code-block:: python

        from uuid import UUID
        from omnibase_core.models.replay import ModelAuditTrailSummary
        from omnibase_core.services.replay.service_audit_trail import ServiceAuditTrail

        # Get summary from audit trail service
        service = ServiceAuditTrail(session_id=UUID("550e8400-e29b-41d4-a716-446655440000"))
        # ... record some decisions ...
        summary = service.get_summary()

        print(f"Total decisions: {summary.total_decisions}")
        print(f"Blocked outcomes: {summary.decisions_by_outcome.get('blocked', 0)}")

Related:
    - OMN-1150: Replay Safety Enforcement
    - ModelAuditTrailEntry: Individual entries that are aggregated
    - ServiceAuditTrail: Service that computes summaries

.. versionadded:: 0.6.3
"""

__all__ = ["ModelAuditTrailSummary"]

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelAuditTrailSummary(BaseModel):
    """
    Summary statistics for enforcement decisions in a session.

    Provides aggregated view of all enforcement decisions made during
    a replay session for monitoring and compliance.

    Attributes:
        session_id: The replay session this summary covers.
        total_decisions: Total number of enforcement decisions made.
        decisions_by_outcome: Count of decisions by outcome type.
            Keys: "allowed", "blocked", "warned", "mocked"
        decisions_by_source: Count of decisions by non-determinism source.
            Keys: "time", "random", "uuid", "network", "database", "filesystem", "environment"
        decisions_by_mode: Count of decisions by enforcement mode.
            Keys: "strict", "warn", "permissive", "mocked"
        first_decision_at: Timestamp of the first decision, or None if no decisions.
        last_decision_at: Timestamp of the last decision, or None if no decisions.
        blocked_effects: List of unique effect types that were blocked.

    Example:
        >>> from datetime import datetime, timezone
        >>> from uuid import UUID
        >>> summary = ModelAuditTrailSummary(
        ...     session_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        ...     total_decisions=10,
        ...     decisions_by_outcome={"allowed": 6, "blocked": 2, "mocked": 2},
        ...     decisions_by_source={"time": 3, "random": 2, "network": 5},
        ...     decisions_by_mode={"strict": 8, "mocked": 2},
        ...     first_decision_at=datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc),
        ...     last_decision_at=datetime(2024, 6, 15, 12, 5, 0, tzinfo=timezone.utc),
        ...     blocked_effects=["http.get", "file.read"],
        ... )
        >>> summary.total_decisions
        10
        >>> "http.get" in summary.blocked_effects
        True

    Thread Safety:
        Thread-safe. Model is frozen (immutable) after creation.

    .. versionadded:: 0.6.3
    """

    # from_attributes=True allows Pydantic to accept objects with matching
    # attributes even when class identity differs (e.g., in pytest-xdist
    # parallel execution where model classes are imported in separate workers).
    # See CLAUDE.md section "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    session_id: UUID = Field(
        ...,
        description="The replay session this summary covers.",
    )
    total_decisions: int = Field(
        ...,
        ge=0,
        description="Total number of enforcement decisions made.",
    )
    decisions_by_outcome: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Count of decisions by outcome type. "
            "Keys: 'allowed', 'blocked', 'warned', 'mocked'"
        ),
    )
    decisions_by_source: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Count of decisions by non-determinism source. "
            "Keys: 'time', 'random', 'uuid', 'network', 'database', 'filesystem', 'environment'"
        ),
    )
    decisions_by_mode: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Count of decisions by enforcement mode. "
            "Keys: 'strict', 'warn', 'permissive', 'mocked'"
        ),
    )
    first_decision_at: datetime | None = Field(
        default=None,
        description="Timestamp of the first decision, or None if no decisions.",
    )
    last_decision_at: datetime | None = Field(
        default=None,
        description="Timestamp of the last decision, or None if no decisions.",
    )
    blocked_effects: list[str] = Field(
        default_factory=list,
        description="List of unique effect types that were blocked.",
    )
