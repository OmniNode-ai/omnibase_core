"""Model for snapshot of execution input.

Captures the input data for an execution, with support for
truncation of large payloads while preserving metadata about
the original size.

Thread Safety:
    ModelInputSnapshot is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict

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
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    raw: dict[str, Any]
    truncated: bool = False
    original_size_bytes: int
    display_size_bytes: int


__all__ = ["ModelInputSnapshot"]
