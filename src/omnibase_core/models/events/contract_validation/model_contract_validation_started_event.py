"""
Contract validation started event model.

This module provides the event model for when contract validation begins.
This event marks the start of a validation lifecycle and should be followed
by either a passed or failed event with the same run_id.

Location:
    ``omnibase_core.models.events.contract_validation.model_contract_validation_started_event``

Import Example:
    .. code-block:: python

        from omnibase_core.models.events.contract_validation import (
            ModelContractValidationStartedEvent,
            ModelContractValidationContext,
        )

Event Type:
    ``onex.contract.validation.started``

See Also:
    - :class:`ModelContractValidationPassedEvent`: Emitted when validation passes
    - :class:`ModelContractValidationFailedEvent`: Emitted when validation fails

.. versionadded:: 0.4.0
    Initial implementation as part of OMN-1146 contract validation events.
"""

from uuid import UUID

from pydantic import AliasChoices, Field, field_validator

from omnibase_core.models.events.contract_validation.model_contract_ref import (
    ModelContractRef,
)
from omnibase_core.models.events.contract_validation.model_contract_validation_context import (
    ModelContractValidationContext,
)
from omnibase_core.models.events.contract_validation.model_contract_validation_event_base import (
    ModelContractValidationEventBase,
)

__all__ = ["ModelContractValidationStartedEvent", "CONTRACT_VALIDATION_STARTED_EVENT"]

CONTRACT_VALIDATION_STARTED_EVENT = "onex.contract.validation.started"


class ModelContractValidationStartedEvent(ModelContractValidationEventBase):
    """
    Event emitted when contract validation begins.

    This event marks the start of a validation lifecycle. The ``run_id`` from
    this event should be used in subsequent passed/failed events to maintain
    lifecycle correlation.

    The model is immutable (frozen) to ensure event integrity after creation.

    Attributes:
        event_type: Event type identifier (onex.contract.validation.started).
        validator_set_name: Optional identifier of the validator set being used.
        context: Validation context with field-level details about what is
            being validated.

    Example:
        >>> from uuid import uuid4
        >>> from omnibase_core.models.events.contract_validation import (
        ...     ModelContractValidationStartedEvent,
        ...     ModelContractValidationContext,
        ... )
        >>>
        >>> event = ModelContractValidationStartedEvent(
        ...     contract_name="runtime-host-contract",
        ...     run_id=uuid4(),
        ...     context=ModelContractValidationContext(),
        ...     validator_set_id="standard-v1",
        ... )
        >>> event.event_type
        'onex.contract.validation.started'

    Note:
        The ``context`` field provides configuration for validation behavior,
        including the validation mode (STRICT, PERMISSIVE) and custom flags.

    .. versionadded:: 0.4.0
    """

    event_type: str = Field(
        default=CONTRACT_VALIDATION_STARTED_EVENT,
        description="Event type identifier.",
    )

    validator_set_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("validator_set_name", "validator_set_id"),
        description="Optional identifier of the validator set being used for validation.",
    )

    context: ModelContractValidationContext = Field(
        ...,
        description="Validation context with field-level details about what is "
        "being validated.",
    )

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Validate that event_type matches the expected constant."""
        if v != CONTRACT_VALIDATION_STARTED_EVENT:
            raise ValueError(
                f"event_type must be '{CONTRACT_VALIDATION_STARTED_EVENT}', got '{v}'"
            )
        return v

    @classmethod
    def create(
        cls,
        contract_name: str,
        run_id: UUID,
        context: ModelContractValidationContext,
        *,
        validator_set_name: str | None = None,
        actor: UUID | None = None,
        contract_ref: ModelContractRef | None = None,
        correlation_id: UUID | None = None,
    ) -> "ModelContractValidationStartedEvent":
        """
        Factory method for creating a contract validation started event.

        Args:
            contract_name: Identifier of the contract being validated.
            run_id: Unique identifier for this validation run.
            context: Validation context with field-level details.
            validator_set_name: Optional identifier of the validator set.
            actor: Optional UUID of the triggering node/service.
            contract_ref: Optional full contract reference.
            correlation_id: Optional correlation ID for tracing.

        Returns:
            A new ModelContractValidationStartedEvent instance.
        """
        return cls(
            contract_name=contract_name,
            run_id=run_id,
            context=context,
            validator_set_name=validator_set_name,
            actor=actor,
            contract_ref=contract_ref,
            correlation_id=correlation_id,
        )
