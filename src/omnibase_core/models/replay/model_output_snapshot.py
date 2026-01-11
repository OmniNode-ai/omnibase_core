"""Model for snapshot of execution output.

Captures the output data for an execution, with support for
truncation of large payloads while preserving metadata about
the original size and a hash for comparison.

Thread Safety:
    ModelOutputSnapshot is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.decorators import allow_dict_any
from omnibase_core.mixins.mixin_truncation_validation import (
    MixinTruncationValidation,
)


@allow_dict_any(
    reason="raw field captures arbitrary execution output data which varies by node type"
)
class ModelOutputSnapshot(MixinTruncationValidation, BaseModel):
    """Snapshot of execution output.

    Captures the output data for an execution, with support for
    truncation of large payloads while preserving metadata about
    the original size and a hash for comparison.

    Attributes:
        raw: The raw output data dictionary.
        truncated: Whether the output was truncated due to size limits.
        original_size_bytes: Size of the original output in bytes.
        display_size_bytes: Size of the displayed/stored output in bytes.
        output_hash: Hash identifier of the original output for comparison.
            Typically formatted as "algorithm:hexdigest" (e.g., "sha256:abc123").
            Must be non-empty.

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
        ge=0, description="Size of the original output in bytes (must be >= 0)"
    )
    display_size_bytes: int = Field(
        ge=0, description="Size of the displayed/stored output in bytes (must be >= 0)"
    )
    output_hash: str = Field(
        min_length=1,
        description=(
            "Hash identifier of the original output for comparison. "
            "Typically formatted as 'algorithm:hexdigest' (e.g., 'sha256:abc123')."
        ),
    )


__all__ = ["ModelOutputSnapshot"]
