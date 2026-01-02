"""
Action validation metadata model.

Provides typed model for validation metadata,
replacing dict[str, Any] metadata field in ModelActionValidationResult.
"""

from pydantic import BaseModel, Field


class ModelActionValidationMetadata(BaseModel):
    """
    Typed model for action validation metadata.

    Replaces dict[str, Any] metadata field in ModelActionValidationResult.
    """

    # Validation context
    validation_strategy: str | None = Field(
        default=None,
        description="Validation strategy used",
    )
    validator_version: str | None = Field(  # string-version-ok: validator version id
        default=None,
        description="Version of the validator",
    )

    # Performance metrics
    validation_time_ms: int | None = Field(
        default=None,
        description="Time taken for validation (ms)",
        ge=0,
    )
    checks_performed: int | None = Field(
        default=None,
        description="Number of validation checks performed",
        ge=0,
    )

    # Source information
    source_node: str | None = Field(
        default=None,
        description="Node that performed validation",
    )
    request_id: str | None = Field(
        default=None,
        description="Request ID for tracking",
    )

    # Result details
    skipped_checks: list[str] = Field(
        default_factory=list,
        description="Names of validation checks that were skipped",
    )
    failed_checks: list[str] = Field(
        default_factory=list,
        description="Names of validation checks that failed",
    )

    # Custom string values
    custom_fields: dict[str, str] = Field(
        default_factory=dict,
        description="Additional custom string metadata",
    )


__all__ = ["ModelActionValidationMetadata"]
