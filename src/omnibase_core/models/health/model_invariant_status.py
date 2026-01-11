"""
Model for invariant status tracking.

Invariants are conditions that must remain true for the system to be
considered healthy.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelInvariantStatus(BaseModel):
    """Status of a single invariant check.

    Invariants are conditions that must remain true for the system to be
    considered healthy. This model captures the result of checking a single
    invariant.

    Attributes:
        invariant_id: Unique identifier for the invariant.
        name: Human-readable name of the invariant.
        passed: Whether the invariant check passed.
        details: Optional details about the check result.

    Example:
        >>> from uuid import uuid4
        >>> status = ModelInvariantStatus(
        ...     invariant_id=uuid4(),
        ...     name="response_format_valid",
        ...     passed=True,
        ...     details="All responses match expected schema"
        ... )
        >>> status.passed
        True
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    invariant_id: UUID = Field(
        ...,
        description="Unique identifier for the invariant",
    )
    name: str = Field(
        ...,
        description="Human-readable name of the invariant",
    )
    passed: bool = Field(
        ...,
        description="Whether the invariant check passed",
    )
    details: str | None = Field(
        default=None,
        description="Optional details about the check result",
    )
