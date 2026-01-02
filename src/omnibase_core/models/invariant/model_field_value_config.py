"""Configuration for field value invariant.

Validates that a specific field matches an expected value
or pattern.
"""

from pydantic import BaseModel, Field


class ModelFieldValueConfig(BaseModel):
    """Configuration for field value invariant.

    Validates that a specific field matches an expected value
    or pattern. At least one of expected_value or pattern
    should be set for meaningful validation.
    """

    field_path: str = Field(
        ...,
        description="Field path to check (dot notation, e.g., 'status.code')",
    )
    expected_value: object | None = Field(
        default=None,
        description="Expected exact value for the field",
    )
    pattern: str | None = Field(
        default=None,
        description="Regex pattern to match against field value",
    )


__all__ = ["ModelFieldValueConfig"]
