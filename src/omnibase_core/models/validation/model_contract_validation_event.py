"""
Contract validation event model.

This module provides the Pydantic model for contract validation lifecycle events.

Design Decision:
    This model intentionally lives in ``models/validation/`` rather than
    ``models/events/`` because it represents a **validation lifecycle event**,
    not a **domain event** (ModelEventEnvelope). The separation exists to:

    1. **Clear Domain Boundaries**: Validation events are internal to the
       contract validation subsystem and follow different patterns than
       domain events that flow through the event bus.

    2. **Different Serialization Needs**: Domain events (ModelEventEnvelope)
       include routing metadata, correlation IDs, and envelope structure.
       Validation events are simpler, local status notifications.

    3. **Avoid Circular Dependencies**: Validation models are imported early
       in the bootstrap sequence. Placing them in events/ could create
       circular import chains with event bus infrastructure.

    4. **Single Responsibility**: The validation/ module owns all validation
       lifecycle concerns, including status events, error models, and results.

Related:
    - OMN-1146: Contract Validation Invariant Checker
    - ServiceContractValidationInvariantChecker: Service implementation

.. versionadded:: 0.4.0
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ModelContractValidationEvent",
    "ContractValidationEventType",
]

# Type alias for valid event types
ContractValidationEventType = Literal[
    "validation_started",
    "validation_passed",
    "validation_failed",
    "merge_started",
    "merge_completed",
]


class ModelContractValidationEvent(BaseModel):
    """
    Represents a contract validation lifecycle event.

    This model captures the key information about a validation or merge
    event, including its type and the run it belongs to.

    Attributes:
        event_type: The type of validation event
        run_ref: String reference for the validation run
        message: Optional message providing additional context
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        frozen=True,
        from_attributes=True,
    )

    event_type: ContractValidationEventType = Field(
        ...,
        description="The type of contract validation event",
    )
    run_ref: str = Field(
        ...,
        min_length=1,
        description="String reference for the validation run",
    )
    message: str | None = Field(
        default=None,
        description="Optional message providing additional context",
    )
