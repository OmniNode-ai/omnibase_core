from pydantic import BaseModel, Field

"""Metadata about the validation process."""


class ModelValidationMetadata(BaseModel):
    """Metadata about the validation process."""

    validation_type: str | None = Field(
        None,
        description="Type of validation performed (e.g., 'schema', 'security', 'business')",
    )
    duration_ms: int | None = Field(
        None,
        description="Validation duration in milliseconds",
    )
    files_processed: int | None = Field(
        None,
        description="Number of files processed during validation",
    )
    rules_applied: int | None = Field(
        None,
        description="Number of validation rules applied",
    )
    timestamp: str | None = Field(
        None,
        description="ISO timestamp when validation was performed",
    )
    validator_version: str | None = Field(
        None,
        description="Version of the validator used",
    )
