"""Configuration for field presence invariant.

Verifies that specified fields exist in the output,
supporting nested paths via dot notation.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelFieldPresenceConfig(BaseModel):
    """Configuration for field presence invariant.

    Verifies that specified fields exist in the output, supporting nested
    paths via dot notation (e.g., 'user.profile.email').

    Attributes:
        fields: List of required field paths. Must contain at least one path.
            Each path uses dot notation for nested fields.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    fields: list[str] = Field(
        ...,
        min_length=1,
        description="Required field paths (dot notation, e.g., 'user.email')",
    )


__all__ = ["ModelFieldPresenceConfig"]
