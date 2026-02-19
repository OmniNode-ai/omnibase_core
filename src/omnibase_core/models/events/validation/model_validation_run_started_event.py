# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Cross-repo validation run started event model.

This module provides the event model for when a cross-repo validation run begins.
This event marks the start of a validation lifecycle and should be followed
by zero or more violations batch events, and finally a completed event with
the same run_id.

Location:
    ``omnibase_core.models.events.validation.model_validation_run_started_event``

Import Example:
    .. code-block:: python

        from omnibase_core.models.events.validation import (
            ModelValidationRunStartedEvent,
            VALIDATION_RUN_STARTED_EVENT,
        )

Event Type:
    ``onex.validation.cross_repo.run.started.v1``

See Also:
    - :class:`ModelValidationViolationsBatchEvent`: Emitted for each batch of violations
    - :class:`ModelValidationRunCompletedEvent`: Emitted when validation completes

.. versionadded:: 0.13.0
    Initial implementation as part of OMN-1776 cross-repo orchestrator.
"""

from datetime import datetime
from pathlib import Path
from uuid import UUID

from pydantic import Field, field_validator

from omnibase_core.models.events.validation.model_validation_event_base import (
    ModelValidationEventBase,
)

__all__ = ["ModelValidationRunStartedEvent", "VALIDATION_RUN_STARTED_EVENT"]

VALIDATION_RUN_STARTED_EVENT = "onex.validation.cross_repo.run.started.v1"


class ModelValidationRunStartedEvent(ModelValidationEventBase):
    """
    Event emitted when a cross-repo validation run begins.

    This event marks the start of a validation lifecycle. The ``run_id`` from
    this event should be used in subsequent violations batch and completed events
    to maintain lifecycle correlation.

    The model is immutable (frozen) to ensure event integrity after creation.

    Attributes:
        event_type: Event type identifier (onex.validation.cross_repo.run.started.v1).
        root_path: Root directory path being validated.
        policy_name: Name of the validation policy being applied.
        rules_enabled: List of rule IDs that are enabled for this run.
        baseline_applied: Whether a baseline is being applied to suppress known violations.
        started_at: When the validation run started (UTC).

    Example:
        >>> from uuid import uuid4
        >>> from pathlib import Path
        >>> from omnibase_core.models.events.validation import (
        ...     ModelValidationRunStartedEvent,
        ... )
        >>>
        >>> event = ModelValidationRunStartedEvent(
        ...     run_id=uuid4(),
        ...     repo_id="omnibase_core",
        ...     root_path=Path("/workspace/omnibase_core"),
        ...     policy_name="omnibase_core_policy",
        ...     rules_enabled=["repo_boundaries", "forbidden_imports"],
        ...     baseline_applied=False,
        ... )
        >>> event.event_type
        'onex.validation.cross_repo.run.started.v1'

    .. versionadded:: 0.13.0
    """

    event_type: str = Field(
        default=VALIDATION_RUN_STARTED_EVENT,
        description="Event type identifier.",
    )

    root_path: str = Field(
        ...,
        description="Root directory path being validated (as string for JSON serialization).",
    )

    policy_name: str = Field(
        ...,
        description="Name of the validation policy being applied.",
        min_length=1,
    )

    rules_enabled: tuple[str, ...] = Field(
        default_factory=tuple,
        description="List of rule IDs that are enabled for this run.",
    )

    baseline_applied: bool = Field(
        default=False,
        description="Whether a baseline is being applied to suppress known violations.",
    )

    started_at: datetime = Field(
        ...,
        description="When the validation run started (UTC).",
    )

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Validate that event_type matches the expected constant."""
        if v != VALIDATION_RUN_STARTED_EVENT:
            raise ValueError(
                f"event_type must be '{VALIDATION_RUN_STARTED_EVENT}', got '{v}'"
            )
        return v

    @classmethod
    def create(
        cls,
        run_id: UUID,
        repo_id: str,
        root_path: Path | str,
        policy_name: str,
        started_at: datetime,
        *,
        rules_enabled: tuple[str, ...] | list[str] | None = None,
        baseline_applied: bool = False,
        correlation_id: UUID | None = None,
    ) -> "ModelValidationRunStartedEvent":
        """
        Factory method for creating a validation run started event.

        Args:
            run_id: Unique identifier for this validation run.
            repo_id: Identifier of the repository being validated.
            root_path: Root directory path being validated.
            policy_name: Name of the validation policy being applied.
            started_at: When the validation run started (UTC).
            rules_enabled: List of rule IDs that are enabled.
            baseline_applied: Whether a baseline is being applied.
            correlation_id: Optional correlation ID for tracing.

        Returns:
            A new ModelValidationRunStartedEvent instance.
        """
        return cls(
            run_id=run_id,
            repo_id=repo_id,
            root_path=str(root_path),
            policy_name=policy_name,
            started_at=started_at,
            rules_enabled=tuple(rules_enabled) if rules_enabled else (),
            baseline_applied=baseline_applied,
            correlation_id=correlation_id,
        )
