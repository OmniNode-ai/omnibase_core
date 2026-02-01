"""Label validation result model for metrics policy enforcement."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.observability.model_label_violation import ModelLabelViolation


class ModelLabelValidationResult(BaseModel):
    """Result of validating labels against a ModelMetricsPolicy.

    Returned by ModelMetricsPolicy.validate_labels() to provide
    a complete picture of validation status, any violations found,
    and optionally sanitized labels that pass policy.

    Attributes:
        is_valid: True if no violations were found.
        violations: List of policy violations (empty if valid).
        sanitized_labels: Labels with violations removed/fixed, or None if
            sanitization is not possible (e.g., all labels were invalid).
    """

    is_valid: bool = Field(
        ...,
        description="True if all labels pass policy validation",
    )
    violations: list[ModelLabelViolation] = Field(
        default_factory=list,
        description="List of policy violations found",
    )
    sanitized_labels: dict[str, str] | None = Field(
        default=None,
        description="Labels with violations removed/truncated, or None if not applicable",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )


__all__ = ["ModelLabelValidationResult"]
