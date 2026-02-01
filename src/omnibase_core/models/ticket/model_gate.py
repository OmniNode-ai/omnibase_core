"""Gate model for approval workflows."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.ticket import (
    EnumGateKind,
    EnumTicketStepStatus,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelGate(BaseModel):
    """A gate that requires approval before proceeding.

    Immutability:
        This model uses frozen=True, making instances immutable after creation.
        This enables safe sharing across threads without synchronization.
    """

    id: str = Field(..., description="Unique identifier for the gate")
    kind: EnumGateKind = Field(..., description="Type of gate")
    description: str = Field(..., description="Description of what needs approval")
    required: bool = Field(default=True, description="Whether approval is required")
    status: EnumTicketStepStatus = Field(
        default=EnumTicketStepStatus.PENDING, description="Current status of the gate"
    )
    approver: str | None = Field(default=None, description="Who approved/rejected")
    decided_at: datetime | None = Field(
        default=None, description="When the decision was made"
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    @field_validator("status", mode="before")
    @classmethod
    def validate_status_not_passed(cls, value: object) -> EnumTicketStepStatus:
        """Validate that gates cannot have status=passed.

        Gates use approved/rejected semantics, not passed/failed.

        Args:
            value: The status value to validate.

        Returns:
            The validated status.

        Raises:
            ModelOnexError: If status is 'passed'.
        """
        if isinstance(value, str):
            try:
                value = EnumTicketStepStatus(value)
            except ValueError as e:
                raise ModelOnexError(
                    message=f"Invalid status value: {value!r}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    invalid_status=value,
                ) from e

        if isinstance(value, EnumTicketStepStatus):
            if value == EnumTicketStepStatus.PASSED:
                raise ModelOnexError(
                    message=(
                        "Gates cannot have status='passed'. "
                        "Use 'approved', 'rejected', 'skipped', or 'pending'."
                    ),
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    invalid_status=str(value),
                )

        # NOTE: mypy cannot infer that value is EnumTicketStepStatus after the isinstance
        # checks and string conversion. Safe because all code paths either raise or return
        # the validated enum value.
        return value  # type: ignore[return-value]


# Alias for cleaner imports
Gate = ModelGate

__all__ = [
    "ModelGate",
    "Gate",
]
