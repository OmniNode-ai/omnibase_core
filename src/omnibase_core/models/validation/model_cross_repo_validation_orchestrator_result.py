"""
Result model for cross-repo validation orchestrator.

This module provides the result container for validation orchestrator runs,
holding the emitted events for inspection and testing.

Related ticket: OMN-1776
"""

from uuid import UUID

from omnibase_core.models.events.validation import (
    ModelValidationRunCompletedEvent,
    ModelValidationRunStartedEvent,
    ModelValidationViolationsBatchEvent,
)

__all__ = ["CrossRepoValidationOrchestratorResult"]


class CrossRepoValidationOrchestratorResult:
    """
    Result from orchestrator containing emitted events.

    Per ONEX Four-Node Architecture, orchestrators emit events/intents
    and do not return typed business results. This result container
    holds the emitted events for inspection/testing.

    Attributes:
        run_id: Unique identifier for this validation run.
        events: Tuple of all events emitted during the run.
        is_valid: Whether the validation passed (convenience accessor).
    """

    def __init__(
        self,
        run_id: UUID,
        events: tuple[
            ModelValidationRunStartedEvent
            | ModelValidationViolationsBatchEvent
            | ModelValidationRunCompletedEvent,
            ...,
        ],
    ) -> None:
        self.run_id = run_id
        self.events = events

    @property
    def is_valid(self) -> bool:
        """Return whether validation passed (from completed event)."""
        for event in self.events:
            if isinstance(event, ModelValidationRunCompletedEvent):
                return event.is_valid
        return False

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

    @property
    def total_violations(self) -> int:
        """Return total violation count from completed event."""
        if self.completed_event:
            return self.completed_event.total_violations
        return 0
