"""Pattern Warning Model.

Represents non-fatal warnings during pattern extraction operations.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types.type_json import JsonType


class ModelPatternWarning(BaseModel):
    """Non-fatal warning during pattern extraction.

    Warnings indicate issues that didn't prevent extraction but
    may affect result quality or completeness.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    code: str = Field(
        ...,
        min_length=1,
        description="Warning code for categorization (e.g., 'INCOMPLETE_SESSION')",
    )

    message: str = Field(
        ...,
        min_length=1,
        description="Human-readable warning message",
    )

    context: dict[str, JsonType] = Field(
        default_factory=dict,
        description="Additional context about the warning",
    )


__all__ = ["ModelPatternWarning"]
