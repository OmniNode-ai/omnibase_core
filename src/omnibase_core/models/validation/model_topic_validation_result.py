"""
Topic suffix validation result model for ONEX naming convention.

This module provides ModelTopicValidationResult, a Pydantic model that
encapsulates the result of validating an ONEX topic suffix.

The result includes:
- Validation status (is_valid)
- The original suffix that was validated
- Error message if validation failed
- Parsed suffix parts if validation succeeded

Example:
    >>> from omnibase_core.models.validation.model_topic_validation_result import (
    ...     ModelTopicValidationResult,
    ... )
    >>> # Valid result
    >>> result = ModelTopicValidationResult(
    ...     is_valid=True,
    ...     suffix="onex.evt.omnimemory.intent-stored.v1",
    ...     error=None,
    ...     parsed=some_parsed_parts,
    ... )
    >>> result.is_valid
    True

Thread Safety:
    ModelTopicValidationResult is immutable (frozen=True) and thread-safe.
    Instances can be safely shared across threads.

See Also:
    - validator_topic_suffix: Validation utilities that produce this result
    - ModelTopicSuffixParts: The parsed parts model
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, model_validator

if TYPE_CHECKING:
    from omnibase_core.models.validation.model_topic_suffix_parts import (
        ModelTopicSuffixParts,
    )


class ModelTopicValidationResult(BaseModel):
    """
    Result of validating an ONEX topic suffix.

    This immutable model encapsulates the outcome of suffix validation,
    providing both success/failure status and detailed information about
    the validation outcome.

    Attributes:
        is_valid: True if the suffix passes all validation rules
        suffix: The original suffix string that was validated
        error: Human-readable error message if validation failed, None otherwise
        parsed: Parsed suffix parts if validation succeeded, None otherwise

    Invariants:
        - If is_valid is True, parsed must be non-None and error must be None
        - If is_valid is False, error must be non-None and parsed must be None

    Example:
        >>> # Successful validation
        >>> result = ModelTopicValidationResult(
        ...     is_valid=True,
        ...     suffix="onex.evt.user-service.account-created.v1",
        ...     error=None,
        ...     parsed=parsed_parts,
        ... )
        >>> result.is_valid
        True
        >>> result.parsed.producer
        'user-service'

        >>> # Failed validation
        >>> result = ModelTopicValidationResult(
        ...     is_valid=False,
        ...     suffix="dev.onex.evt.user.created.v1",
        ...     error="Suffix must not start with environment prefix",
        ...     parsed=None,
        ... )
        >>> result.is_valid
        False
        >>> result.error
        'Suffix must not start with environment prefix'
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    is_valid: bool = Field(
        ...,
        description="True if the suffix passes all validation rules",
    )

    suffix: str = Field(
        ...,
        description="The original suffix string that was validated",
    )

    error: str | None = Field(
        default=None,
        description="Error message if validation failed, None otherwise",
    )

    # NOTE: Using string forward reference to avoid circular import.
    # The actual type is ModelTopicSuffixParts from model_topic_suffix_parts.py.
    # Pydantic handles forward references via model_rebuild() at runtime.
    parsed: ModelTopicSuffixParts | None = Field(
        default=None,
        description="Parsed suffix parts if validation succeeded, None otherwise",
    )

    @model_validator(mode="after")
    def validate_invariants(self) -> ModelTopicValidationResult:
        """Enforce validation result invariants."""
        if self.is_valid:
            if self.parsed is None or self.error is not None:
                raise ValueError(
                    "is_valid=True requires parsed to be set and error to be None"
                )
        elif self.error is None or self.parsed is not None:
            raise ValueError(
                "is_valid=False requires error to be set and parsed to be None"
            )
        return self

    @classmethod
    def success(
        cls,
        suffix: str,
        parsed: ModelTopicSuffixParts,
    ) -> ModelTopicValidationResult:
        """
        Create a successful validation result.

        Factory method for creating a result indicating validation passed.

        Args:
            suffix: The validated suffix string
            parsed: The parsed suffix parts

        Returns:
            A ModelTopicValidationResult with is_valid=True
        """
        return cls(
            is_valid=True,
            suffix=suffix,
            error=None,
            parsed=parsed,
        )

    @classmethod
    def failure(cls, suffix: str, error: str) -> ModelTopicValidationResult:
        """
        Create a failed validation result.

        Factory method for creating a result indicating validation failed.

        Args:
            suffix: The suffix string that failed validation
            error: Human-readable description of why validation failed

        Returns:
            A ModelTopicValidationResult with is_valid=False
        """
        return cls(
            is_valid=False,
            suffix=suffix,
            error=error,
            parsed=None,
        )


# Rebuild model to resolve forward references
# This is required because we use TYPE_CHECKING for ModelTopicSuffixParts
# to avoid circular imports at module load time
def _rebuild_model() -> None:
    """
    Rebuild model to resolve forward references for pytest-xdist compatibility.

    Required because TYPE_CHECKING imports are not available at runtime.
    pytest-xdist workers import classes independently, so explicit rebuild
    ensures ModelTopicSuffixParts type is resolved correctly across workers.
    """
    from omnibase_core.models.validation.model_topic_suffix_parts import (
        ModelTopicSuffixParts,
    )

    ModelTopicValidationResult.model_rebuild(
        _types_namespace={"ModelTopicSuffixParts": ModelTopicSuffixParts}
    )


_rebuild_model()


__all__ = [
    "ModelTopicValidationResult",
]
