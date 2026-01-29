"""Intent storage operation result model.

Represents the result of storing an intent classification.
Part of the intent storage subsystem (OMN-1645).
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelIntentStorageResult"]


class ModelIntentStorageResult(BaseModel):
    """Result of storing an intent classification.

    Returned by storage operations to indicate success/failure
    and provide metadata about the stored intent.

    Attributes:
        success: Whether the storage operation succeeded.
        intent_id: ID of the stored intent (if successful).
        created: True if new record, False if updated existing.
        error_message: Error description if operation failed.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        from_attributes=True,
    )

    success: bool = Field(
        description="Whether the storage operation succeeded",
    )
    intent_id: UUID | None = Field(
        default=None,
        description="ID of the stored intent (if successful)",
    )
    created: bool = Field(
        default=False,
        description="True if new record, False if updated existing",
    )
    error_message: str | None = Field(
        default=None,
        description="Error description if operation failed",
    )
