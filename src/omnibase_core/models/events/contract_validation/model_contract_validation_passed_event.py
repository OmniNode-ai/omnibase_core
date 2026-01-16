"""
Contract validation passed event model.

This module provides the event model for when contract validation succeeds.
This event should have the same run_id as the corresponding started event.

Location:
    ``omnibase_core.models.events.contract_validation.model_contract_validation_passed_event``

Import Example:
    .. code-block:: python

        from omnibase_core.models.events.contract_validation import (
            ModelContractValidationPassedEvent,
        )

Event Type:
    ``onex.contract.validation.passed``

See Also:
    - :class:`ModelContractValidationStartedEvent`: Emitted when validation starts
    - :class:`ModelContractValidationFailedEvent`: Emitted when validation fails

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

__all__ = ["ModelContractValidationPassedEvent", "CONTRACT_VALIDATION_PASSED_EVENT"]

CONTRACT_VALIDATION_PASSED_EVENT = "onex.contract.validation.passed"


class ModelContractValidationPassedEvent(ModelContractValidationEventBase):
    """
    Event emitted when contract validation succeeds.

    This event indicates that contract validation completed successfully,
    possibly with warnings. The ``run_id`` should match the corresponding
    started event for lifecycle correlation.

    The model is immutable (frozen) to ensure event integrity after creation.

    Attributes:
        event_type: Event type identifier (onex.contract.validation.passed).
        validator_set_name: Optional identifier of the validator set that was used.
        warnings_count: Number of warnings generated during validation (default 0).
        checks_run: Number of validation checks that were executed.
        duration_ms: Time taken for validation in milliseconds.
        warnings_refs: List of references to warning details (bounded to 100).

    Example:
        >>> from uuid import uuid4
        >>> from omnibase_core.models.events.contract_validation import (
        ...     ModelContractValidationPassedEvent,
        ... )
        >>>
        >>> event = ModelContractValidationPassedEvent(
        ...     contract_name="runtime-host-contract",
        ...     run_id=uuid4(),
        ...     checks_run=15,
        ...     duration_ms=250,
        ...     warnings_count=2,
        ...     warnings_refs=["warn://deprecation/field-x", "warn://style/naming"],
        ... )
        >>> event.event_type
        'onex.contract.validation.passed'

    Note:
        Even when validation passes, there may be warnings. Check ``warnings_count``
        and ``warnings_refs`` for non-critical issues that should be addressed.

    .. versionadded:: 0.4.0
    """

    event_type: str = Field(
        default=CONTRACT_VALIDATION_PASSED_EVENT,
        description="Event type identifier.",
    )

    validator_set_name: str | None = Field(
        default=None,
        description="Optional identifier of the validator set that was used.",
    )

    warnings_count: int = Field(
        default=0,
        ge=0,
        description="Number of warnings generated during validation.",
    )

    checks_run: int = Field(
        default=0,
        ge=0,
        description="Number of validation checks that were executed.",
    )

    duration_ms: int = Field(
        ...,
        ge=0,
        description="Time taken for validation in milliseconds.",
    )

    warnings_refs: list[str] = Field(
        default_factory=list,
        max_length=100,
        description="List of references to warning details. Bounded to 100 entries "
        "to prevent unbounded growth.",
    )

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Validate that event_type matches the expected constant."""
        if v != CONTRACT_VALIDATION_PASSED_EVENT:
            raise ValueError(
                f"event_type must be '{CONTRACT_VALIDATION_PASSED_EVENT}', got '{v}'"
            )
        return v

    @classmethod
    def create(
        cls,
        contract_name: str,
        run_id: UUID,
        duration_ms: int,
        *,
        validator_set_name: str | None = None,
        warnings_count: int = 0,
        checks_run: int = 0,
        warnings_refs: list[str] | None = None,
        actor: UUID | None = None,
        contract_ref: ModelContractRef | None = None,
        correlation_id: UUID | None = None,
    ) -> "ModelContractValidationPassedEvent":
        """
        Factory method for creating a contract validation passed event.

        Args:
            contract_name: Identifier of the contract that was validated.
            run_id: Unique identifier for this validation run (matches started event).
            duration_ms: Time taken for validation in milliseconds.
            validator_set_name: Optional identifier of the validator set.
            warnings_count: Number of warnings generated (default 0).
            checks_run: Number of validation checks executed (default 0).
            warnings_refs: Optional list of warning references.
            actor: Optional UUID of the triggering node/service.
            contract_ref: Optional full contract reference.
            correlation_id: Optional correlation ID for tracing.

        Returns:
            A new ModelContractValidationPassedEvent instance.
        """
        return cls(
            contract_name=contract_name,
            run_id=run_id,
            duration_ms=duration_ms,
            validator_set_name=validator_set_name,
            warnings_count=warnings_count,
            checks_run=checks_run,
            warnings_refs=warnings_refs if warnings_refs is not None else [],
            actor=actor,
            contract_ref=contract_ref,
            correlation_id=correlation_id,
        )
