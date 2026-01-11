"""Model for snapshot of execution output.

Captures the output data for an execution, with support for
truncation of large payloads while preserving metadata about
the original size and a hash for comparison.

Thread Safety:
    ModelOutputSnapshot is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.decorators import allow_dict_any

# Pattern for validating hash format: "algorithm:hexdigest"
# - Algorithm: alphanumeric (allows uppercase for flexibility, e.g., "SHA256" or "sha256")
# - Separator: colon
# - Digest: hexadecimal characters (0-9, a-f, A-F)
HASH_FORMAT_PATTERN = re.compile(r"^[a-zA-Z0-9]+:[a-fA-F0-9]+$")
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
            Must be formatted as "algorithm:hexdigest" (e.g., "sha256:abc123").
            Algorithm must be alphanumeric, digest must be hexadecimal.

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it
        thread-safe for concurrent read access.

    Validation:
        - display_size_bytes must be <= original_size_bytes
        - If truncated=True, display_size_bytes must be < original_size_bytes
        - If truncated=False, display_size_bytes must equal original_size_bytes
        - output_hash must match "algorithm:hexdigest" format (validated by regex)
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
            "Must be formatted as 'algorithm:hexdigest' (e.g., 'sha256:abc123'). "
            "Algorithm must be alphanumeric, digest must be hexadecimal."
        ),
    )

    @field_validator("output_hash")
    @classmethod
    def validate_hash_format(cls, v: str) -> str:
        """Validate that output_hash follows the 'algorithm:hexdigest' format.

        Args:
            v: The hash string to validate.

        Returns:
            The validated hash string.

        Raises:
            ValueError: If the hash format is invalid.
        """
        if not HASH_FORMAT_PATTERN.match(v):
            raise ValueError(
                f"Invalid hash format: '{v}'. "
                "Must be 'algorithm:hexdigest' format (e.g., 'sha256:abc123'). "
                "Algorithm must be alphanumeric, digest must be hexadecimal."
            )
        return v


__all__ = ["ModelOutputSnapshot"]
