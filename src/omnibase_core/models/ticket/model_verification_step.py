"""Verification step model for ticket validation."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.ticket import (
    EnumTicketStepStatus,
    EnumVerificationKind,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelVerificationStep(BaseModel):
    """A verification step that must pass before completion.

    Immutability:
        This model uses frozen=True, making instances immutable after creation.
        This enables safe sharing across threads without synchronization.
    """

    id: str = Field(..., description="Unique identifier for the step")
    kind: EnumVerificationKind = Field(..., description="Type of verification")
    command: str | None = Field(
        default=None, description="Command to run for verification"
    )
    blocking: bool = Field(
        default=True, description="Whether failure blocks completion"
    )
    status: EnumTicketStepStatus = Field(
        default=EnumTicketStepStatus.PENDING, description="Current status of the step"
    )
    output: str | None = Field(
        default=None, description="Output from the verification run"
    )
    run_at: datetime | None = Field(default=None, description="When the step was run")

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    @field_validator("status", mode="before")
    @classmethod
    def validate_status_not_approved(cls, value: object) -> EnumTicketStepStatus:
        """Validate that verification steps cannot have status=approved.

        Verification steps use passed/failed/skipped semantics, not approval.

        Args:
            value: The status value to validate.

        Returns:
            The validated status.

        Raises:
            ModelOnexError: If status is 'approved'.
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
            if value == EnumTicketStepStatus.APPROVED:
                raise ModelOnexError(
                    message=(
                        "Verification steps cannot have status='approved'. "
                        "Use 'passed', 'failed', 'skipped', or 'pending'."
                    ),
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    invalid_status=str(value),
                )

        return value  # type: ignore[return-value]


# Alias for cleaner imports
VerificationStep = ModelVerificationStep

__all__ = [
    "ModelVerificationStep",
    "VerificationStep",
]
