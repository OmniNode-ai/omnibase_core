"""Pattern Error Model.

Represents structured errors during pattern extraction operations.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types.type_json import JsonType


class ModelPatternError(BaseModel):
    """Structured error during pattern extraction (non-throwing).

    Errors represent failures during extraction that may be
    recoverable or terminal, captured as data rather than exceptions.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    code: str = Field(
        ...,
        min_length=1,
        description="Error code for categorization (e.g., 'SESSION_NOT_FOUND')",
    )

    message: str = Field(
        ...,
        min_length=1,
        description="Human-readable error message",
    )

    recoverable: bool = Field(
        ...,
        description="Whether extraction can continue despite this error",
    )

    context: dict[str, JsonType] = Field(
        default_factory=dict,
        description="Additional context about the error",
    )


__all__ = ["ModelPatternError"]
