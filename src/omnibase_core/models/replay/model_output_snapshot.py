"""Model for snapshot of execution output.

Captures the output data for an execution, with support for
truncation of large payloads while preserving metadata about
the original size and a hash for comparison.

Thread Safety:
    ModelOutputSnapshot is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict

from omnibase_core.decorators import allow_dict_any


@allow_dict_any(
    reason="raw field captures arbitrary execution output data which varies by node type"
)
class ModelOutputSnapshot(BaseModel):
    """Snapshot of execution output.

    Captures the output data for an execution, with support for
    truncation of large payloads while preserving metadata about
    the original size and a hash for comparison.

    Attributes:
        raw: The raw output data dictionary.
        truncated: Whether the output was truncated due to size limits.
        original_size_bytes: Size of the original output in bytes.
        display_size_bytes: Size of the displayed/stored output in bytes.
        output_hash: Hash of the original output for comparison.

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it
        thread-safe for concurrent read access.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    raw: dict[str, Any]
    truncated: bool = False
    original_size_bytes: int
    display_size_bytes: int
    output_hash: str


__all__ = ["ModelOutputSnapshot"]
