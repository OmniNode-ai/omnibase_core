"""Value change model for structured difference representation.

Captures a single value change between baseline and replay outputs.

Thread Safety:
    ModelValueChange is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelValueChange(BaseModel):
    """Represents a single value change between baseline and replay.

    Captures the old and new values for a specific field path when
    comparing two execution outputs.

    Attributes:
        old_value: Value in baseline output (serialized to string).
        new_value: Value in replay output (serialized to string).

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it
        thread-safe for concurrent read access.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    old_value: str = Field(
        ...,
        description="Value in baseline output (serialized to string)",
    )
    new_value: str = Field(
        ...,
        description="Value in replay output (serialized to string)",
    )


__all__ = ["ModelValueChange"]
