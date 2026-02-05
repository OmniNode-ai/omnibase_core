"""
Result model for cross-repo validation orchestrator.

This module provides the result container for validation orchestrator runs,
holding the emitted events for inspection and testing.

Related ticket: OMN-1776
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field

from omnibase_core.models.events.validation import (
    ModelValidationRunCompletedEvent,
    ModelValidationRunStartedEvent,
    ModelValidationViolationsBatchEvent,
)

__all__ = ["ModelCrossRepoValidationOrchestratorResult"]

# Type alias for the union of event types
ValidationEvent = (
    ModelValidationRunStartedEvent
    | ModelValidationViolationsBatchEvent
    | ModelValidationRunCompletedEvent
)


class ModelCrossRepoValidationOrchestratorResult(BaseModel):
    """
    Result from orchestrator containing emitted events.

    Per ONEX Four-Node Architecture, orchestrators emit events/intents
    and do not return typed business results. This result container
    holds the emitted events for inspection/testing.

    This is a frozen Pydantic model to ensure immutability after creation
    and enable JSON serialization for test fixtures and debugging.

    Attributes:
        run_id: Unique identifier for this validation run.
        events: Tuple of all events emitted during the run.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    run_id: UUID = Field(..., description="Unique identifier for this validation run.")
    events: tuple[ValidationEvent, ...] = Field(
        ..., description="All events emitted during the run."
    )

    # NOTE(OMN-1776): mypy/pydantic computed_field+property decorator interaction requires ignore.
    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_valid(self) -> bool:
        """Return whether validation passed (from completed event)."""
        for event in self.events:
            if isinstance(event, ModelValidationRunCompletedEvent):
                return event.is_valid
        return False

    # NOTE(OMN-1776): mypy/pydantic computed_field+property decorator interaction requires ignore.
    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_violations(self) -> int:
        """Return total violation count from completed event."""
        for event in self.events:
            if isinstance(event, ModelValidationRunCompletedEvent):
                return event.total_violations
        return 0

    @property
    def started_event(self) -> ModelValidationRunStartedEvent | None:
        """Return the started event."""
        for event in self.events:
            if isinstance(event, ModelValidationRunStartedEvent):
                return event
        return None

    @property
    def completed_event(self) -> ModelValidationRunCompletedEvent | None:
        """Return the completed event."""
        for event in self.events:
            if isinstance(event, ModelValidationRunCompletedEvent):
                return event
        return None

    @property
    def violation_batches(self) -> tuple[ModelValidationViolationsBatchEvent, ...]:
        """Return all violation batch events."""
        return tuple(
            event
            for event in self.events
            if isinstance(event, ModelValidationViolationsBatchEvent)
        )
