"""Metadata about the validation process."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelValidationMetadata(BaseModel):
    """Metadata about the validation process."""

    model_config = ConfigDict(extra="allow")

    validation_type: str | None = Field(
        default=None,
        description="Type of validation performed (e.g., 'schema', 'security', 'business')",
    )
    duration_ms: int | None = Field(
        default=None,
        ge=0,
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
    violations_found: int | None = Field(
        default=None,
        description="Total number of violations found during validation",
    )
    files_with_violations: list[str] | int | None = Field(
        default=None,
        description="Files with violations (list of paths) or count",
    )
    yaml_files_found: int | None = Field(
        default=None,
        description="Number of YAML files found during contract validation",
    )
    manual_yaml_violations: int | None = Field(
        default=None,
        description="Number of manual YAML violations found",
    )
    strict_mode: bool | None = Field(
        default=None,
        description="Whether strict validation mode was enabled",
    )
    max_violations: int | None = Field(
        default=None,
        description="Maximum allowed violations for validation to pass",
    )
    files_with_violations_count: int | None = Field(
        default=None,
        description="Number of files with violations",
    )
    total_unions: int | None = Field(
        default=None,
        description="Total number of Union types found",
    )
    complex_patterns: int | None = Field(
        default=None,
        description="Number of complex type patterns found",
    )
    max_unions: int | None = Field(
        default=None,
        description="Maximum allowed number of Union types",
    )
