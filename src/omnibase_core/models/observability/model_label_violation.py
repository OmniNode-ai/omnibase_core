"""Label violation model for metrics policy enforcement."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_label_violation_type import EnumLabelViolationType


class ModelLabelViolation(BaseModel):
    """Represents a single label policy violation.

    Created when a label fails validation against a ModelMetricsPolicy.
    Contains details about what rule was violated and the offending data.

    Attributes:
        violation_type: Category of violation (forbidden key, not allowed, too long).
        key: The label key that caused the violation.
        value: The label value (if relevant to the violation).
        message: Human-readable description of the violation.
    """

    violation_type: EnumLabelViolationType = Field(
        ...,
        description="Type of policy violation",
    )
    key: str = Field(
        ...,
        description="Label key that violated policy",
    )
    value: str | None = Field(
        default=None,
        description="Label value (included for VALUE_TOO_LONG violations)",
    )
    message: str = Field(
        ...,
        description="Human-readable violation description",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )


__all__ = ["ModelLabelViolation"]
