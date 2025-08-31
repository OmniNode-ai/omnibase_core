"""
Validation Metadata Model

Type-safe validation metadata that replaces Dict[str, Any] usage.
"""

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_custom_fields import ModelCustomFields


class ModelValidationMetadata(BaseModel):
    """
    Type-safe validation metadata.

    Provides structured metadata for validation issues with
    common fields for tracking and analysis.
    """

    # Common validation metadata fields
    field_name: str | None = Field(None, description="Field that failed validation")
    expected_value: str | None = Field(None, description="Expected value or pattern")
    actual_value: str | None = Field(None, description="Actual value found")

    # Validation context
    validation_rule: str | None = Field(
        None,
        description="Name of validation rule that failed",
    )
    validation_type: str | None = Field(
        None,
        description="Type of validation (schema, business, etc.)",
    )
    line_number: int | None = Field(
        None,
        description="Line number where issue occurred",
    )
    column_number: int | None = Field(
        None,
        description="Column number where issue occurred",
    )

    # Related information
    related_fields: list[str] = Field(
        default_factory=list,
        description="Other fields related to this issue",
    )
    error_code: str | None = Field(
        None,
        description="Specific error code for this validation failure",
    )

    # Fix information
    auto_fixable: bool = Field(
        False,
        description="Whether this issue can be automatically fixed",
    )
    fix_complexity: str | None = Field(
        None,
        description="Complexity of fix (simple, medium, complex)",
    )

    # Custom metadata for extensibility
    custom_fields: ModelCustomFields | None = Field(
        None,
        description="Custom metadata fields for specific validation types",
    )
