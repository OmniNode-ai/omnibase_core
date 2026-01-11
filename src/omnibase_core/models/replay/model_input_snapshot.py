"""Model for snapshot of execution input.

Captures the input data for an execution, with support for
truncation of large payloads while preserving metadata about
the original size.

Thread Safety:
    ModelInputSnapshot is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from typing import Any, Self

from pydantic import BaseModel, ConfigDict, model_validator

from omnibase_core.decorators import allow_dict_any


@allow_dict_any(
    reason="raw field captures arbitrary execution input data which varies by node type"
)
class ModelInputSnapshot(BaseModel):
    """Snapshot of execution input.

    Captures the input data for an execution, with support for
    truncation of large payloads while preserving metadata about
    the original size.

    Attributes:
        raw: The raw input data dictionary.
        truncated: Whether the input was truncated due to size limits.
        original_size_bytes: Original size of the input in bytes.
        display_size_bytes: Size of the displayed/stored input in bytes.

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it
        thread-safe for concurrent read access.

    Validation:
        - display_size_bytes must be <= original_size_bytes
        - If truncated=True, display_size_bytes must be < original_size_bytes
        - If truncated=False, display_size_bytes must equal original_size_bytes
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    raw: dict[str, Any]
    truncated: bool = False
    original_size_bytes: int
    display_size_bytes: int

    @model_validator(mode="after")
    def validate_truncation_constraints(self) -> Self:
        """Validate logical constraints between truncation flag and size fields.

        Raises:
            ValueError: If display_size_bytes > original_size_bytes.
            ValueError: If truncated=True but display_size_bytes >= original_size_bytes.
            ValueError: If truncated=False but display_size_bytes != original_size_bytes.
        """
        if self.display_size_bytes > self.original_size_bytes:
            raise ValueError(
                f"display_size_bytes ({self.display_size_bytes}) cannot exceed "
                f"original_size_bytes ({self.original_size_bytes})"
            )

        if self.truncated:
            if self.display_size_bytes >= self.original_size_bytes:
                raise ValueError(
                    f"When truncated=True, display_size_bytes ({self.display_size_bytes}) "
                    f"must be less than original_size_bytes ({self.original_size_bytes})"
                )
        elif self.display_size_bytes != self.original_size_bytes:
            raise ValueError(
                f"When truncated=False, display_size_bytes ({self.display_size_bytes}) "
                f"must equal original_size_bytes ({self.original_size_bytes})"
            )

        return self


__all__ = ["ModelInputSnapshot"]
