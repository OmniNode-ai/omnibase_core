"""
Contract validation event model.

This module provides the Pydantic model for contract validation lifecycle events.

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
