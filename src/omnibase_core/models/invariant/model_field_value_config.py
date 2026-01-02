"""Configuration for field value invariant.

Validates that a specific field matches an expected value
or pattern.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelFieldValueConfig(BaseModel):
    """Configuration for field value invariant.

    Validates that a specific field matches an expected value or pattern.

    Attributes:
        field_path: Field path to check using dot notation (e.g., 'status.code').
        expected_value: Expected exact value for the field. Setting this to None
            explicitly means "check that the field's value is None" (e.g., to
            verify response.error is None). If neither expected_value nor pattern
            is set, the invariant acts as a field presence check only.
        pattern: Regex pattern to match against field value (as a string).

    Note:
        For meaningful value validation, set at least one of expected_value
        or pattern. If neither is set, the invariant only verifies the field
        exists at the specified path.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

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
