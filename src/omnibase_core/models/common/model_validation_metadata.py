from pydantic import BaseModel, Field

from omnibase_core.primitives.model_semver import ModelSemVer

"""Metadata about the validation process."""


class ModelValidationMetadata(BaseModel):
    """Metadata about the validation process."""

    validation_type: str | None = Field(
        default=None,
        description="Type of validation performed (e.g., 'schema', 'security', 'business')",
    )
    duration_ms: int | None = Field(
        default=None,
        description="Validation duration in milliseconds",
    )
    files_processed: int | None = Field(
        default=None,
        description="Number of files processed during validation",
    )
    rules_applied: int | None = Field(
        default=None,
        description="Number of validation rules applied",
    )
    timestamp: str | None = Field(
        default=None,
        description="ISO timestamp when validation was performed",
    )
    validator_version: ModelSemVer | None = Field(
        default=None,
        description="Version of the validator used",
    )
