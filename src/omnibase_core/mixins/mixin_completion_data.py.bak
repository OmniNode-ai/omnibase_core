from __future__ import annotations

from pydantic import Field

"""
Canonical payload for completion events following ONEX naming conventions.
"""

from pydantic import BaseModel, ConfigDict, StrictBool, StrictInt, StrictStr


class MixinCompletionData(BaseModel):
    """
    Canonical payload for completion events following ONEX naming conventions.

    Fields are optional so producers can send only relevant data.
    Uses Strict* types to prevent silent type coercion.
    """

    model_config = ConfigDict(
        extra="forbid",  # Catch typos early
        frozen=True,  # Immutable instances for safer passing
    )

    message: StrictStr | None = Field(
        default=None, description="Human-readable completion message"
    )
    success: StrictBool | None = Field(
        default=None, description="Whether the operation succeeded"
    )
    code: StrictInt | None = Field(
        default=None, description="Numeric status or error code"
    )
    tags: list[StrictStr] | None = Field(
        default=None, description="Labels for search/filtering"
    )

    def to_event_kwargs(self) -> dict[str, object]:
        """Convert to kwargs for OnexEvent creation, excluding None values."""
        return self.model_dump(exclude_none=True)
