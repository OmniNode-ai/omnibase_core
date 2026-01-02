"""Configuration for field presence invariant.

Verifies that specified fields exist in the output,
supporting nested paths via dot notation.
"""

from pydantic import BaseModel, Field


class ModelFieldPresenceConfig(BaseModel):
    """Configuration for field presence invariant.

    Verifies that specified fields exist in the output,
    supporting nested paths via dot notation.
    """

    fields: list[str] = Field(
        ...,
        min_length=1,
        description="Required field paths (dot notation, e.g., 'user.email')",
    )


__all__ = ["ModelFieldPresenceConfig"]
