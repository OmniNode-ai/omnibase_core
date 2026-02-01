"""
ModelAuditTrailEntry - Individual entry in enforcement decision audit trail.

This module provides the ModelAuditTrailEntry model that wraps an enforcement
decision with session context and sequencing information.

Design:
    Audit trail entries extend enforcement decisions with:
    - Unique entry identifier for deduplication
    - Session identifier for grouping related decisions
    - Sequence number for ordering within session
    - Additional context for debugging and analysis

Architecture:
    The ServiceAuditTrail produces ModelAuditTrailEntry instances for each
    recorded enforcement decision. These entries can be:
    - Queried by session, outcome, source
    - Exported for debugging and compliance
    - Aggregated into summary statistics

Thread Safety:
    ModelAuditTrailEntry is frozen (immutable) after creation, making it
    safe to share across threads.

Usage:
    .. code-block:: python

        from uuid import UUID
        from omnibase_core.models.replay import (
            ModelAuditTrailEntry,
            ModelEnforcementDecision,
        )

        # Create an audit trail entry
        entry = ModelAuditTrailEntry(
            id=UUID("550e8400-e29b-41d4-a716-446655440001"),
            session_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            sequence_number=0,
            decision=decision,
            context={"handler": "my_handler"},
        )

Related:
    - OMN-1150: Replay Safety Enforcement
    - ModelEnforcementDecision: The wrapped decision
    - ServiceAuditTrail: Service that produces these entries

.. versionadded:: 0.6.3
"""

__all__ = ["ModelAuditTrailEntry"]

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.replay.model_enforcement_decision import (
    ModelEnforcementDecision,
)
from omnibase_core.types.type_json import JsonType


class ModelAuditTrailEntry(BaseModel):
    """
    Individual entry in the enforcement decision audit trail.

    Wraps an enforcement decision with session and sequencing metadata
    for tracking, querying, and analysis.

    Attributes:
        id: Unique identifier for this entry (UUID format).
        session_id: Replay session identifier for grouping related decisions.
        sequence_number: Order of this decision within the session (0-indexed).
        decision: The enforcement decision being recorded.
        context: Additional context for debugging (handler name, input hash, etc.).

    Example:
        >>> from datetime import datetime, timezone
        >>> from uuid import UUID
        >>> from omnibase_core.enums.replay import (
        ...     EnumEffectDeterminism,
        ...     EnumEnforcementMode,
        ... )
        >>> decision = ModelEnforcementDecision(
        ...     effect_type="time.now",
        ...     determinism=EnumEffectDeterminism.NON_DETERMINISTIC,
        ...     source=None,
        ...     mode=EnumEnforcementMode.STRICT,
        ...     decision="blocked",
        ...     reason="Time effects blocked in strict mode",
        ...     timestamp=datetime.now(timezone.utc),
        ... )
        >>> entry = ModelAuditTrailEntry(
        ...     id=UUID("550e8400-e29b-41d4-a716-446655440001"),
        ...     session_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        ...     sequence_number=0,
        ...     decision=decision,
        ... )
        >>> entry.session_id
        UUID('550e8400-e29b-41d4-a716-446655440000')

    Thread Safety:
        Thread-safe. Model is frozen (immutable) after creation.

    .. versionadded:: 0.6.3
    """

    # from_attributes=True allows Pydantic to accept objects with matching
    # attributes even when class identity differs (e.g., in pytest-xdist
    # parallel execution where model classes are imported in separate workers).
    # See CLAUDE.md section "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    id: UUID = Field(
        ...,
        description="Unique identifier for this entry.",
    )
    session_id: UUID = Field(
        ...,
        description="Replay session identifier for grouping related decisions.",
    )
    sequence_number: int = Field(
        ...,
        ge=0,
        description="Order of this decision within the session (0-indexed).",
    )
    decision: ModelEnforcementDecision = Field(
        ...,
        description="The enforcement decision being recorded.",
    )
    context: dict[str, JsonType] = Field(
        default_factory=dict,
        description="Additional context for debugging (handler name, input hash, etc.).",
    )
