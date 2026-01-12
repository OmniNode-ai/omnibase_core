"""Model for snapshot of execution output.

Captures the output data for an execution, with support for
truncation of large payloads while preserving metadata about
the original size and a hash for comparison.

Thread Safety:
    ModelOutputSnapshot is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.decorators import allow_dict_any
from omnibase_core.mixins.mixin_truncation_validation import (
    MixinTruncationValidation,
)
from omnibase_core.utils.util_hash_validation import (
    validate_hash_format as _validate_hash_format,
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
            Must be formatted as "algorithm:hexdigest"
            (e.g., "sha256:a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2").
            Algorithm must be alphanumeric, digest must be hexadecimal.
            Common algorithms: sha256 (64 hex chars), sha512 (128 hex chars), md5 (32 hex chars).

    Example:
        >>> snapshot = ModelOutputSnapshot(
        ...     raw={"result": "success", "value": 42},
        ...     truncated=False,
        ...     original_size_bytes=48,
        ...     display_size_bytes=48,
        ...     output_hash="sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        ... )

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
            "Must be formatted as 'algorithm:hexdigest' "
            "(e.g., 'sha256:a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2'). "
            "Algorithm must be alphanumeric, digest must be hexadecimal. "
            "Common algorithms: sha256 (64 hex chars), sha512 (128 hex chars), md5 (32 hex chars)."
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
            ValueError: If the hash format is invalid or too long.
        """
        return _validate_hash_format(v)


__all__ = ["ModelOutputSnapshot"]
