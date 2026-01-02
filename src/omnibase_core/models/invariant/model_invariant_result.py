"""
Invariant result model for validation evaluation outcomes.

Captures the result of evaluating a single invariant against a model,
including pass/fail status, actual vs expected values, and timing information.
"""

from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_invariant_severity import EnumInvariantSeverity


class ModelInvariantResult(BaseModel):
    """
    Result of evaluating a single invariant.

    Captures all relevant information about an invariant evaluation,
    including whether it passed, what values were observed vs expected,
    and when the evaluation occurred.

    Attributes:
        invariant_id: ID of the evaluated invariant.
        invariant_name: Name of the evaluated invariant.
        passed: Whether the invariant passed validation.
        severity: Severity of the invariant (for determining impact).
        actual_value: Actual value observed during evaluation.
        expected_value: Expected value per the invariant configuration.
        message: Human-readable message describing the result.
        evaluated_at: Timestamp when the evaluation occurred.
    """

    invariant_id: UUID = Field(
        ...,
        description="ID of the evaluated invariant",
    )
    invariant_name: str = Field(
        ...,
        description="Name of the evaluated invariant",
    )
    passed: bool = Field(
        ...,
        description="Whether the invariant passed validation",
    )
    severity: EnumInvariantSeverity = Field(
        ...,
        description="Severity of the invariant (for determining impact)",
    )
    actual_value: object = Field(
        default=None,
        description="Actual value observed during evaluation",
    )
    expected_value: object = Field(
        default=None,
        description="Expected value per the invariant configuration",
    )
    message: str = Field(
        default="",
        description="Human-readable message describing the result",
    )
    evaluated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp when the evaluation occurred",
    )


__all__ = ["ModelInvariantResult"]
