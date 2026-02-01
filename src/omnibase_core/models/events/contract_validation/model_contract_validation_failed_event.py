"""
Contract validation failed event model.

This module provides the event model for when contract validation fails.
This event should have the same run_id as the corresponding started event.

Location:
    ``omnibase_core.models.events.contract_validation.model_contract_validation_failed_event``

Import Example:
    .. code-block:: python

        from omnibase_core.models.events.contract_validation import (
            ModelContractValidationFailedEvent,
        )

Event Type:
    ``onex.contract.validation.failed``

See Also:
    - :class:`ModelContractValidationStartedEvent`: Emitted when validation starts
    - :class:`ModelContractValidationPassedEvent`: Emitted when validation passes

.. versionadded:: 0.4.0
    Initial implementation as part of OMN-1146 contract validation events.
"""

from uuid import UUID

from pydantic import Field, field_validator

from omnibase_core.models.events.contract_validation.model_contract_ref import (
    ModelContractRef,
)
from omnibase_core.models.events.contract_validation.model_contract_validation_event_base import (
    ModelContractValidationEventBase,
)

MAX_VIOLATION_ENTRIES = 100
"""
Maximum number of violation entries in failed validation events.

Bounded to 100 entries to:
- Prevent event payload bloat in message queues (Kafka/Redpanda typically have 1MB message limits)
- Ensure reasonable serialization/deserialization performance
- Maintain readability in logs and audit trails

For complete violation details beyond this limit, use the result_ref field
to reference the full validation result in persistent storage.
"""

__all__ = [
    "ModelContractValidationFailedEvent",
    "CONTRACT_VALIDATION_FAILED_EVENT",
    "MAX_VIOLATION_ENTRIES",
]

CONTRACT_VALIDATION_FAILED_EVENT = "onex.contract.validation.failed"


class ModelContractValidationFailedEvent(ModelContractValidationEventBase):
    """
    Event emitted when contract validation fails.

    This event indicates that contract validation encountered one or more
    errors that prevented successful completion. The ``run_id`` should match
    the corresponding started event for lifecycle correlation.

    The model is immutable (frozen) to ensure event integrity after creation.

    Attributes:
        event_type: Event type identifier (onex.contract.validation.failed).
        validator_set_name: Optional identifier of the validator set that was used.
        error_count: Number of validation errors encountered (minimum 1).
        first_error_code: Error code of the first/primary validation error.
        duration_ms: Time taken for validation in milliseconds.
        violations: List of violation descriptions (max MAX_VIOLATION_ENTRIES).
        result_ref: Optional pointer to stored detailed validation result.

    Example:
        >>> from uuid import uuid4
        >>> from omnibase_core.models.events.contract_validation import (
        ...     ModelContractValidationFailedEvent,
        ... )
        >>>
        >>> event = ModelContractValidationFailedEvent(
        ...     contract_name="runtime-host-contract",
        ...     run_id=uuid4(),
        ...     error_count=3,
        ...     first_error_code="CONTRACT_SCHEMA_INVALID",
        ...     duration_ms=150,
        ...     violations=[
        ...         "Missing required field: name",
        ...         "Invalid type for field: version",
        ...         "Unknown field: deprecated_field",
        ...     ],
        ... )
        >>> event.event_type
        'onex.contract.validation.failed'

    Note:
        The ``first_error_code`` provides quick identification of the primary
        failure reason. For full details, check the ``violations`` list or
        retrieve the full result using ``result_ref``.

    .. versionadded:: 0.4.0
    """

    event_type: str = Field(
        default=CONTRACT_VALIDATION_FAILED_EVENT,
        description="Event type identifier.",
    )

    validator_set_name: str | None = Field(
        default=None,
        description="Optional identifier of the validator set that was used.",
    )

    error_count: int = Field(
        ...,
        ge=1,
        description="Number of validation errors encountered. Must be at least 1 "
        "since this is a failure event.",
    )

    first_error_code: str = Field(
        ...,
        min_length=1,
        description="Error code of the first/primary validation error.",
    )

    duration_ms: int = Field(
        ...,
        ge=0,
        description="Time taken for validation in milliseconds.",
    )

    violations: list[str] = Field(
        default_factory=list,
        max_length=MAX_VIOLATION_ENTRIES,
        description=f"List of violation descriptions (max {MAX_VIOLATION_ENTRIES}). "
        "For full details, use result_ref.",
    )

    result_ref: str | None = Field(
        default=None,
        description="Optional pointer to stored detailed validation result. "
        "Use this to retrieve full validation details when violations list "
        "is truncated or for auditing purposes.",
    )

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Validate that event_type matches the expected constant."""
        if v != CONTRACT_VALIDATION_FAILED_EVENT:
            raise ValueError(
                f"event_type must be '{CONTRACT_VALIDATION_FAILED_EVENT}', got '{v}'"
            )
        return v

    @classmethod
    def create(
        cls,
        contract_name: str,
        run_id: UUID,
        error_count: int,
        first_error_code: str,
        duration_ms: int,
        *,
        validator_set_name: str | None = None,
        violations: list[str] | None = None,
        result_ref: str | None = None,
        actor: UUID | None = None,
        contract_ref: ModelContractRef | None = None,
        correlation_id: UUID | None = None,
    ) -> "ModelContractValidationFailedEvent":
        """
        Factory method for creating a contract validation failed event.

        Args:
            contract_name: Identifier of the contract that was validated.
            run_id: Unique identifier for this validation run (matches started event).
            error_count: Number of validation errors encountered (minimum 1).
            first_error_code: Error code of the first/primary validation error.
            duration_ms: Time taken for validation in milliseconds.
            validator_set_name: Optional identifier of the validator set.
            violations: Optional list of violation descriptions.
            result_ref: Optional pointer to stored detailed result.
            actor: Optional UUID of the triggering node/service.
            contract_ref: Optional full contract reference.
            correlation_id: Optional correlation ID for tracing.

        Returns:
            A new ModelContractValidationFailedEvent instance.
        """
        return cls(
            contract_name=contract_name,
            run_id=run_id,
            error_count=error_count,
            first_error_code=first_error_code,
            duration_ms=duration_ms,
            validator_set_name=validator_set_name,
            violations=violations if violations is not None else [],
            result_ref=result_ref,
            actor=actor,
            contract_ref=contract_ref,
            correlation_id=correlation_id,
        )
