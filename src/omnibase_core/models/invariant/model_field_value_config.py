"""Configuration for field value invariant.

Validates that a specific field matches an expected value
or pattern.

Thread Safety:
    ModelFieldValueConfig is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types.type_json import JsonType


class ModelFieldValueConfig(BaseModel):
    """Configuration for field value invariant.

    Validates that a specific field matches an expected value or pattern.

    Attributes:
        field_path: Field path to check using dot notation (e.g., 'status.code').
        expected_value: Expected exact value for the field. Setting this to None
            explicitly means "check that the field's value is None" (e.g., to
            verify response.error is None).
        pattern: Regex pattern to match against field value (as a string).

    Usage Guidance:
        For meaningful value validation, it is recommended to set at least one
        of expected_value or pattern. However, this is not enforced by validation
        - the model allows field_path alone, which can be used for field presence
        checks or when validation logic is handled externally.

    Example:
        # Value matching: check that status.code equals 200
        ModelFieldValueConfig(field_path="status.code", expected_value=200)

        # Pattern matching: check that id matches UUID format
        ModelFieldValueConfig(field_path="id", pattern=r"^[0-9a-f-]{36}$")

        # Presence check only: verify the field exists (validation handled externally)
        ModelFieldValueConfig(field_path="response.data")

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it
        thread-safe for concurrent read access. No synchronization is needed
        when sharing instances across threads.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    field_path: str = Field(
        ...,
        description="Field path to check (dot notation, e.g., 'status.code')",
    )
    expected_value: JsonType = Field(
        default=None,
        description="Expected exact value for the field",
    )
    pattern: str | None = Field(
        default=None,
        description="Regex pattern to match against field value",
    )


__all__ = ["ModelFieldValueConfig"]
