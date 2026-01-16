"""
State Transition Notification Model.

ONEX-compatible model for state transition notifications that enable orchestrators
to reliably detect state transitions via post-commit notifications.

Pattern: Model<Name> - Pydantic model for state transition notification
Node Type: N/A (Data Model)

Design Rationale:
    State transition notifications are emitted after a reducer commits a state
    transition. They provide a bounded view of the transition for orchestrators
    to observe and react to, without requiring direct coupling to the reducer's
    internal state.

    This pattern follows the Event-Driven Architecture principle where:
    1. Reducer performs pure state transition (Intent -> State)
    2. Post-commit hook emits notification with transition details
    3. Orchestrators subscribe to notifications and coordinate workflows

Key Features:
    - Immutable (frozen=True) for thread safety
    - Forbids extra fields for strict schema compliance
    - from_attributes=True for pytest-xdist parallel compatibility
    - All required fields use explicit Field() with descriptions
    - Optional workflow_view provides bounded context for orchestrators

Usage:
    >>> from omnibase_core.models.notifications import ModelStateTransitionNotification
    >>> from datetime import datetime, UTC
    >>> from uuid import uuid4
    >>>
    >>> notification = ModelStateTransitionNotification(
    ...     aggregate_type="registration",
    ...     aggregate_id=uuid4(),
    ...     from_state="pending",
    ...     to_state="active",
    ...     projection_version=1,
    ...     correlation_id=uuid4(),
    ...     causation_id=uuid4(),
    ...     timestamp=datetime.now(UTC),
    ... )

Thread Safety:
    This model is immutable (frozen=True) and safe for concurrent access.
    Instances should not be modified after creation.

See Also:
    omnibase_core.protocols.notifications.ProtocolTransitionNotificationPublisher:
        Protocol for publishing transition notifications.
    omnibase_core.protocols.notifications.ProtocolTransitionNotificationConsumer:
        Protocol for consuming transition notifications.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelStateTransitionNotification(BaseModel):
    """
    Notification model for state transitions in ONEX aggregates.

    Emitted after a reducer commits a state transition, enabling orchestrators
    to observe and react to state changes without tight coupling.

    This model provides all necessary context for an orchestrator to understand:
    - What aggregate changed (aggregate_type, aggregate_id)
    - What the transition was (from_state, to_state)
    - Version information for ordering and idempotency (projection_version)
    - Correlation and causation for distributed tracing
    - Optional bounded view of workflow state (workflow_view)

    Attributes:
        aggregate_type: The type of aggregate (e.g., "registration", "intelligence").
            Used for routing notifications to interested orchestrators.
        aggregate_id: Unique identifier of the aggregate instance.
        from_state: The FSM state before the transition.
        to_state: The FSM state after the transition.
        projection_version: Monotonically increasing version of the projection.
            Used for ordering and detecting missed notifications.
        correlation_id: Correlation ID linking this to the original request.
        causation_id: ID of the event that caused this transition.
        timestamp: When the transition was committed (UTC recommended).
        projection_hash: Optional hash of the full projection state.
            Enables optimistic concurrency and integrity verification.
        reducer_version: Optional version of the reducer that processed the transition.
            Useful for debugging and compatibility tracking.
        workflow_view: Optional bounded view of state for orchestrator use.
            Contains only the fields needed for workflow decisions.

    Example:
        >>> from datetime import datetime, UTC
        >>> from uuid import uuid4
        >>>
        >>> # Basic notification
        >>> notification = ModelStateTransitionNotification(
        ...     aggregate_type="registration",
        ...     aggregate_id=uuid4(),
        ...     from_state="pending",
        ...     to_state="active",
        ...     projection_version=1,
        ...     correlation_id=uuid4(),
        ...     causation_id=uuid4(),
        ...     timestamp=datetime.now(UTC),
        ... )
        >>>
        >>> # Notification with workflow view
        >>> notification_with_view = ModelStateTransitionNotification(
        ...     aggregate_type="intelligence",
        ...     aggregate_id=uuid4(),
        ...     from_state="analyzing",
        ...     to_state="completed",
        ...     projection_version=5,
        ...     correlation_id=uuid4(),
        ...     causation_id=uuid4(),
        ...     timestamp=datetime.now(UTC),
        ...     projection_hash="sha256:abc123",
        ...     reducer_version=ModelSemVer(major=1, minor=2, patch=3),
        ...     workflow_view={
        ...         "analysis_type": "code_review",
        ...         "findings_count": 3,
        ...         "severity_max": "high",
        ...     },
        ... )
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    # ---- Required Fields ----

    aggregate_type: str = Field(
        default=...,
        description="Type of the aggregate (e.g., 'registration', 'intelligence')",
    )

    aggregate_id: UUID = Field(
        default=...,
        description="Unique identifier of the aggregate instance",
    )

    from_state: str = Field(
        default=...,
        description="The FSM state before the transition",
    )

    to_state: str = Field(
        default=...,
        description="The FSM state after the transition",
    )

    projection_version: int = Field(
        default=...,
        ge=0,
        description="Monotonically increasing version of the projection",
    )

    correlation_id: UUID = Field(
        default=...,
        description="Correlation ID linking this to the original request",
    )

    causation_id: UUID = Field(
        default=...,
        description="ID of the event that caused this transition",
    )

    timestamp: datetime = Field(
        default=...,
        description="When the transition was committed (UTC recommended)",
    )

    # ---- Optional Fields ----

    projection_hash: str | None = Field(
        default=None,
        description="Hash of the full projection state for integrity verification",
    )

    reducer_version: ModelSemVer | None = Field(
        default=None,
        description="Version of the reducer that processed the transition",
    )

    workflow_view: dict[str, object] | None = Field(
        default=None,
        description="Bounded view of state for orchestrator workflow decisions",
    )


__all__ = ["ModelStateTransitionNotification"]
