# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Cross-repo validation violations batch event model.

This module provides the event model for batches of violations found during
a cross-repo validation run. Violations are emitted in batches to manage
volume (default: 50 violations per batch).

Location:
    ``omnibase_core.models.events.validation.model_validation_violations_batch_event``

Import Example:
    .. code-block:: python

        from omnibase_core.models.events.validation import (
            ModelValidationViolationsBatchEvent,
            ModelViolationRecord,
            VALIDATION_VIOLATIONS_BATCH_EVENT,
        )

Event Type:
    ``onex.evt.validation.cross-repo-violations-batch.v1``

See Also:
    - :class:`ModelValidationRunStartedEvent`: Emitted when validation starts
    - :class:`ModelValidationRunCompletedEvent`: Emitted when validation completes

.. versionadded:: 0.13.0
    Initial implementation as part of OMN-1776 cross-repo orchestrator.
"""

from uuid import UUID

from pydantic import Field, field_validator

from omnibase_core.models.events.validation.model_validation_event_base import (
    ModelValidationEventBase,
)
from omnibase_core.models.events.validation.model_violation_record import (
    ModelViolationRecord,
)

__all__ = [
    "ModelValidationViolationsBatchEvent",
    "VALIDATION_VIOLATIONS_BATCH_EVENT",
]

VALIDATION_VIOLATIONS_BATCH_EVENT = "onex.evt.validation.cross-repo-violations-batch.v1"


class ModelValidationViolationsBatchEvent(ModelValidationEventBase):
    """
    Event emitted for each batch of violations found during validation.

    Violations are batched to manage volume. The ``batch_index`` and
    ``total_batches`` fields enable consumers to reconstruct the complete
    set of violations and detect missing batches.

    The model is immutable (frozen) to ensure event integrity after creation.

    Attributes:
        event_type: Event type identifier (onex.evt.validation.cross-repo-violations-batch.v1).
        batch_index: Zero-based index of this batch (0, 1, 2, ...).
        batch_size: Number of violations in this batch.
        total_batches: Total number of batches that will be emitted for this run.
        violations: Tuple of violations in this batch.

    Example:
        >>> from uuid import uuid4
        >>> from omnibase_core.models.events.validation import (
        ...     ModelValidationViolationsBatchEvent,
        ...     ModelViolationRecord,
        ... )
        >>>
        >>> event = ModelValidationViolationsBatchEvent(
        ...     run_id=uuid4(),
        ...     repo_id="omnibase_core",
        ...     batch_index=0,
        ...     batch_size=2,
        ...     total_batches=1,
        ...     violations=(
        ...         ModelViolationRecord(
        ...             severity="ERROR",
        ...             message="Forbidden import: omnibase_infra",
        ...             rule_name="forbidden_imports",
        ...         ),
        ...         ModelViolationRecord(
        ...             severity="WARNING",
        ...             message="Non-standard topic name",
        ...             rule_name="topic_naming",
        ...         ),
        ...     ),
        ... )

    .. versionadded:: 0.13.0
    """

    event_type: str = Field(
        default=VALIDATION_VIOLATIONS_BATCH_EVENT,
        description="Event type identifier.",
    )

    batch_index: int = Field(
        ...,
        ge=0,
        description="Zero-based index of this batch (0, 1, 2, ...).",
    )

    batch_size: int = Field(
        ...,
        ge=0,
        description="Number of violations in this batch.",
    )

    total_batches: int = Field(
        ...,
        ge=1,
        description="Total number of batches that will be emitted for this run.",
    )

    violations: tuple[ModelViolationRecord, ...] = Field(
        ...,
        description="Tuple of violations in this batch.",
    )

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Validate that event_type matches the expected constant."""
        if v != VALIDATION_VIOLATIONS_BATCH_EVENT:
            raise ValueError(
                f"event_type must be '{VALIDATION_VIOLATIONS_BATCH_EVENT}', got '{v}'"
            )
        return v

    @classmethod
    def create(
        cls,
        run_id: UUID,
        repo_id: str,
        batch_index: int,
        total_batches: int,
        violations: tuple[ModelViolationRecord, ...] | list[ModelViolationRecord],
        *,
        correlation_id: UUID | None = None,
    ) -> "ModelValidationViolationsBatchEvent":
        """
        Factory method for creating a violations batch event.

        Args:
            run_id: Unique identifier for this validation run.
            repo_id: Identifier of the repository being validated.
            batch_index: Zero-based index of this batch.
            total_batches: Total number of batches for this run.
            violations: Violations in this batch.
            correlation_id: Optional correlation ID for tracing.

        Returns:
            A new ModelValidationViolationsBatchEvent instance.
        """
        violations_tuple = (
            tuple(violations) if isinstance(violations, list) else violations
        )
        return cls(
            run_id=run_id,
            repo_id=repo_id,
            batch_index=batch_index,
            batch_size=len(violations_tuple),
            total_batches=total_batches,
            violations=violations_tuple,
            correlation_id=correlation_id,
        )
