"""
Validation Metadata Model

Type-safe validation metadata that replaces Dict[str, Any] usage.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from ..core.model_custom_fields import ModelCustomFields


class ModelValidationMetadata(BaseModel):
    """
    Type-safe validation metadata.

    Provides structured metadata for validation issues with
    common fields for tracking and analysis.
    """

    # Common validation metadata fields
    field_name: Optional[str] = Field(None, description="Field that failed validation")
    expected_value: Optional[str] = Field(None, description="Expected value or pattern")
    actual_value: Optional[str] = Field(None, description="Actual value found")

    # Validation context
    validation_rule: Optional[str] = Field(
        None, description="Name of validation rule that failed"
    )
    validation_type: Optional[str] = Field(
        None, description="Type of validation (schema, business, etc.)"
    )
    line_number: Optional[int] = Field(
        None, description="Line number where issue occurred"
    )
    column_number: Optional[int] = Field(
        None, description="Column number where issue occurred"
    )

    # Related information
    related_fields: List[str] = Field(
        default_factory=list, description="Other fields related to this issue"
    )
    error_code: Optional[str] = Field(
        None, description="Specific error code for this validation failure"
    )

    # Fix information
    auto_fixable: bool = Field(
        False, description="Whether this issue can be automatically fixed"
    )
    fix_complexity: Optional[str] = Field(
        None, description="Complexity of fix (simple, medium, complex)"
    )

    # Custom metadata for extensibility
    custom_fields: Optional[ModelCustomFields] = Field(
        None, description="Custom metadata fields for specific validation types"
    )
