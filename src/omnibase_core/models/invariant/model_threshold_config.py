"""Configuration for threshold invariant.

Validates that a numeric metric falls within specified bounds.

Thread Safety:
    ModelThresholdConfig is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelThresholdConfig(BaseModel):
    """Configuration for threshold invariant.

    Validates that a numeric metric falls within specified bounds.
    At least one of min_value or max_value must be set to define
    a meaningful constraint.

    Attributes:
        metric_name: Name of metric to check (e.g., 'confidence', 'token_count').
        min_value: Minimum allowed value (inclusive).
        max_value: Maximum allowed value (inclusive).

    Raises:
        ValueError: If neither min_value nor max_value is provided.
        ValueError: If min_value is greater than max_value.

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it
        thread-safe for concurrent read access. No synchronization is needed
        when sharing instances across threads.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    metric_name: str = Field(
        ...,
        description="Name of metric to check (e.g., 'confidence', 'token_count')",
    )
    min_value: float | None = Field(
        default=None,
        description="Minimum allowed value (inclusive)",
    )
    max_value: float | None = Field(
        default=None,
        description="Maximum allowed value (inclusive)",
    )

    @model_validator(mode="after")
    def validate_threshold_bounds(self) -> Self:
        """Validate that at least one bound is set and bounds are consistent.

        Returns:
            Self if validation passes.

        Raises:
            ValueError: If neither min_value nor max_value is provided.
            ValueError: If min_value is greater than max_value.
        """
        if self.min_value is None and self.max_value is None:
            # error-ok: Pydantic model_validator requires ValueError
            raise ValueError(
                "At least one of 'min_value' or 'max_value' must be provided "
                "for threshold validation"
            )
        if (
            self.min_value is not None
            and self.max_value is not None
            and self.min_value > self.max_value
        ):
            # error-ok: Pydantic model_validator requires ValueError
            raise ValueError(
                f"min_value ({self.min_value}) cannot be greater than "
                f"max_value ({self.max_value})"
            )
        return self


__all__ = ["ModelThresholdConfig"]
