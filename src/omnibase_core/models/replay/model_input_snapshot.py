"""Model for snapshot of execution input.

Captures the input data for an execution, with support for
truncation of large payloads while preserving metadata about
the original size.

Thread Safety:
    ModelInputSnapshot is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.decorators import allow_dict_any
from omnibase_core.mixins.mixin_truncation_validation import (
    MixinTruncationValidation,
)


@allow_dict_any(
    reason="raw field captures arbitrary execution input data which varies by node type"
)
class ModelInputSnapshot(MixinTruncationValidation, BaseModel):
    """Snapshot of execution input.

    Captures the input data for an execution, with support for
    truncation of large payloads while preserving metadata about
    the original size.

    Example:
        Non-truncated input (full data preserved)::

            >>> snapshot = ModelInputSnapshot(
            ...     raw={"user_id": "u123", "action": "process"},
            ...     truncated=False,
            ...     original_size_bytes=42,
            ...     display_size_bytes=42,  # Must equal original when not truncated
            ... )

        Truncated input (large payload shortened)::

            >>> snapshot = ModelInputSnapshot(
            ...     raw={"user_id": "u123", "data": "...truncated..."},
            ...     truncated=True,
            ...     original_size_bytes=1048576,  # 1MB original
            ...     display_size_bytes=1024,       # 1KB displayed
            ... )

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
    original_size_bytes: int = Field(
        ge=0, description="Original size of the input in bytes (must be >= 0)"
    )
    display_size_bytes: int = Field(
        ge=0, description="Size of the displayed/stored input in bytes (must be >= 0)"
    )


__all__ = ["ModelInputSnapshot"]
