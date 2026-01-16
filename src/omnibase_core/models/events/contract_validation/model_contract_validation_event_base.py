"""
Base model for contract validation events.

This module provides the base class for all contract validation lifecycle events,
including validation started/passed/failed and merge started/completed events.

Location:
    ``omnibase_core.models.events.contract_validation.model_contract_validation_event_base``

Import Example:
    .. code-block:: python

        from omnibase_core.models.events.contract_validation import (
            ModelContractValidationEventBase,
        )

Design Notes:
    - **Lifecycle Sequencing**: The ``run_id`` field enables sequencing of events
      within a single validation run (started -> passed/failed).
    - **Actor Tracking**: The optional ``actor`` field identifies the node or
      service that triggered the validation.
    - **Contract Reference**: The optional ``contract_ref`` provides a full
      reference to the contract being validated.
    - **Immutable**: All event models are frozen to ensure event integrity.

See Also:
    - :class:`ModelContractValidationStartedEvent`: Validation started event
    - :class:`ModelContractValidationPassedEvent`: Validation passed event
    - :class:`ModelContractValidationFailedEvent`: Validation failed event
    - :class:`ModelContractMergeStartedEvent`: Merge started event
    - :class:`ModelContractMergeCompletedEvent`: Merge completed event

.. versionadded:: 0.4.0
    Initial implementation as part of OMN-1146 contract validation events.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.events.contract_validation.model_contract_ref import (
    ModelContractRef,
)

__all__ = ["ModelContractValidationEventBase"]


class ModelContractValidationEventBase(BaseModel):
    """
    Base model for all contract validation lifecycle events.

    This base class provides common fields for tracking contract validation
    events, including the contract being validated, the validation run identifier,
    and optional actor and reference information.

    The model is immutable (frozen) to ensure event integrity after creation.

    Attributes:
        event_id: Unique identifier for this event instance.
        contract_name: Identifier of the contract being validated (required).
        run_id: Unique identifier for this validation run, enabling lifecycle
            sequencing (started -> passed/failed).
        actor: Optional UUID of the node or service that triggered the validation.
        contract_ref: Optional full reference to the contract being validated.
        timestamp: When this event was created (UTC).
        correlation_id: Optional correlation ID for request tracing across services.

    Example:
        >>> from uuid import uuid4
        >>> from omnibase_core.models.events.contract_validation import (
        ...     ModelContractValidationEventBase,
        ...     ModelContractRef,
        ... )
        >>>
        >>> event = ModelContractValidationEventBase(
        ...     contract_name="runtime-host-contract",
        ...     run_id=uuid4(),
        ...     actor=uuid4(),
        ...     contract_ref=ModelContractRef(contract_name="runtime-host-contract"),
        ... )

    Note:
        This is a base class. Use the specific event classes for actual events:
        - ModelContractValidationStartedEvent
        - ModelContractValidationPassedEvent
        - ModelContractValidationFailedEvent
        - ModelContractMergeStartedEvent
        - ModelContractMergeCompletedEvent

    .. versionadded:: 0.4.0
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    event_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this event instance.",
    )

    contract_name: str = Field(
        ...,
        description="Identifier of the contract being validated.",
        min_length=1,
    )

    run_id: UUID = Field(
        ...,
        description="Unique identifier for this validation run. Used for lifecycle "
        "sequencing (started -> passed/failed).",
    )

    actor: UUID | None = Field(
        default=None,
        description="Optional UUID of the node or service that triggered the validation.",
    )

    contract_ref: ModelContractRef | None = Field(
        default=None,
        description="Optional full reference to the contract being validated.",
    )

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When this event was created (UTC).",
    )

    correlation_id: UUID | None = Field(
        default=None,
        description="Optional correlation ID for request tracing across services.",
    )
