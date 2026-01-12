"""Mixin for truncation validation in snapshot models.

Provides reusable validation logic for models that track truncation
state with size metadata.

Thread Safety:
    This mixin is stateless and thread-safe.
"""

from typing import Self

from pydantic import model_validator


class MixinTruncationValidation:
    """Mixin providing truncation validation for snapshot models.

    Validates logical constraints between truncation flag and size fields:
    - display_size_bytes must be <= original_size_bytes
    - If truncated=True, display_size_bytes must be < original_size_bytes
    - If truncated=False, display_size_bytes must equal original_size_bytes

    Thread Safety:
        This mixin is stateless and thread-safe.

    Usage:
        class MySnapshot(MixinTruncationValidation, BaseModel):
            truncated: bool
            original_size_bytes: int
            display_size_bytes: int
    """

    truncated: bool
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
            # error-ok: Pydantic model_validator requires ValueError
            raise ValueError(
                f"display_size_bytes ({self.display_size_bytes}) cannot exceed "
                f"original_size_bytes ({self.original_size_bytes})"
            )

        if self.truncated:
            if self.display_size_bytes >= self.original_size_bytes:
                # error-ok: Pydantic model_validator requires ValueError
                raise ValueError(
                    f"When truncated=True, display_size_bytes ({self.display_size_bytes}) "
                    f"must be less than original_size_bytes ({self.original_size_bytes})"
                )
        elif self.display_size_bytes != self.original_size_bytes:
            # error-ok: Pydantic model_validator requires ValueError
            raise ValueError(
                f"When truncated=False, display_size_bytes ({self.display_size_bytes}) "
                f"must equal original_size_bytes ({self.original_size_bytes})"
            )

        return self


__all__ = ["MixinTruncationValidation"]
