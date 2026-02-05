"""
Base model for cross-repo validation events.

This module provides the base class for all cross-repo validation lifecycle events,
including run started, violations batch, and run completed events.

Location:
    ``omnibase_core.models.events.validation.model_validation_event_base``

Import Example:
    .. code-block:: python

        from omnibase_core.models.events.validation import (
            ModelValidationEventBase,
        )

Design Notes:
    - **Lifecycle Sequencing**: The ``run_id`` field enables sequencing of events
      within a single validation run (started -> violations batch(es) -> completed).
    - **Repo Identification**: The ``repo_id`` field identifies which repository
      is being validated.
    - **Immutable**: All event models are frozen to ensure event integrity.

See Also:
    - :class:`ModelValidationRunStartedEvent`: Validation run started event
    - :class:`ModelValidationViolationsBatchEvent`: Violations batch event
    - :class:`ModelValidationRunCompletedEvent`: Validation run completed event

.. versionadded:: 0.13.0
    Initial implementation as part of OMN-1776 cross-repo orchestrator.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelValidationEventBase"]


class ModelValidationEventBase(BaseModel):
    """
    Base model for all cross-repo validation lifecycle events.

    This base class provides common fields for tracking validation events,
    including the run identifier, repository being validated, and timestamps.

    The model is immutable (frozen) to ensure event integrity after creation.

    Attributes:
        event_id: Unique identifier for this event instance.
        run_id: Unique identifier for this validation run, enabling lifecycle
            sequencing (started -> violations batch(es) -> completed).
        repo_id: Identifier of the repository being validated.
        correlation_id: Optional correlation ID for request tracing across services.
        timestamp: When this event was created (UTC).

    Example:
        >>> from uuid import uuid4
        >>> from omnibase_core.models.events.validation import (
        ...     ModelValidationEventBase,
        ... )
        >>>
        >>> event = ModelValidationEventBase(
        ...     run_id=uuid4(),
        ...     repo_id="omnibase_core",
        ... )

    Note:
        This is a base class. Use the specific event classes for actual events:
        - ModelValidationRunStartedEvent
        - ModelValidationViolationsBatchEvent
        - ModelValidationRunCompletedEvent

    .. versionadded:: 0.13.0
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    event_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this event instance.",
    )

    run_id: UUID = Field(
        ...,
        description="Unique identifier for this validation run. Used for lifecycle "
        "sequencing (started -> violations batch(es) -> completed).",
    )

    repo_id: str = Field(  # string-id-ok: human-readable repository identifier
        ...,
        description="Identifier of the repository being validated.",
        min_length=1,
    )

    correlation_id: UUID | None = Field(
        default=None,
        description="Optional correlation ID for request tracing across services.",
    )

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this event was created (UTC).",
    )
