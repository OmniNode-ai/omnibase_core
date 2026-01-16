"""
Projection Result Model.

Represents the result of a projection operation, including success status,
number of rows affected, and any error information. This model is returned
by projector implementations after processing an event.

Validation:
    - ``rows_affected`` must be >= 0 (negative values raise ValidationError)
    - A ``model_validator`` documents semantic expectations between fields
      but does not enforce them strictly for flexibility

Example Usage:
    >>> from omnibase_core.models.projectors import ModelProjectionResult
    >>>
    >>> # Successful projection that affected 1 row
    >>> result = ModelProjectionResult(success=True, rows_affected=1)
    >>> result.success
    True
    >>> result.rows_affected
    1
    >>>
    >>> # Skipped projection (event type not in consumed_events)
    >>> result = ModelProjectionResult(success=True, skipped=True)
    >>> result.skipped
    True
    >>>
    >>> # Failed projection with error message
    >>> result = ModelProjectionResult(success=False, error="Database connection failed")
    >>> result.success
    False
    >>> result.error
    'Database connection failed'

Thread Safety:
    This model is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access.

.. versionadded:: 0.6.0
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = ["ModelProjectionResult"]


class ModelProjectionResult(BaseModel):
    """
    Result of a projection operation.

    Captures the outcome of projecting an event to a materialized view or
    database table. Used by projector implementations to report success,
    failure, or skip status.

    Attributes:
        success: Whether the projection operation succeeded.
        skipped: Whether the event was skipped because its type was not
            in the projector's consumed_events list.
        rows_affected: Number of database rows affected by the projection.
            Must be non-negative (>= 0). Zero for skipped events or failed
            projections.
        error: Error message if the projection failed. None for successful
            or skipped projections.

    Validation:
        - ``rows_affected`` must be >= 0 (negative values raise ValidationError)

    Semantic Expectations:
        The model enforces minimal validation to remain flexible, but callers
        should generally follow these semantic conventions:

        - If ``skipped=True``, ``rows_affected`` should typically be 0
          (no rows processed for skipped events)
        - If ``success=False``, ``error`` should typically be set to provide
          diagnostic information
        - If ``success=True`` and not skipped, ``rows_affected`` indicates
          how many rows were affected

        Note: The model intentionally allows "unusual" combinations (e.g.,
        ``success=True`` with ``error`` set, or ``skipped=True`` with
        ``rows_affected > 0``) for flexibility in edge cases like warnings
        or partial processing scenarios.

    Examples:
        Successful projection:

        >>> result = ModelProjectionResult(success=True, rows_affected=1)
        >>> result.success
        True
        >>> result.rows_affected
        1

        Skipped event (not in consumed_events):

        >>> result = ModelProjectionResult(success=True, skipped=True)
        >>> result.skipped
        True
        >>> result.rows_affected
        0

        Failed projection:

        >>> result = ModelProjectionResult(
        ...     success=False,
        ...     error="Unique constraint violation"
        ... )
        >>> result.success
        False
        >>> result.error
        'Unique constraint violation'

        Negative rows_affected rejected:

        >>> result = ModelProjectionResult(success=True, rows_affected=-1)
        Traceback (most recent call last):
            ...
        pydantic_core._pydantic_core.ValidationError: ...

    Note:
        **Why from_attributes=True is Required**

        This model uses ``from_attributes=True`` in its ConfigDict to ensure
        pytest-xdist compatibility. When running tests with pytest-xdist,
        each worker process imports the class independently, creating separate
        class objects. The ``from_attributes=True`` flag enables Pydantic's
        "duck typing" mode, allowing fixtures from one worker to be validated
        in another.

        **Thread Safety**: This model is frozen (immutable) after creation,
        making it thread-safe for concurrent read access.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    success: bool = Field(
        description="Whether the projection operation succeeded",
    )

    skipped: bool = Field(
        default=False,
        description="True if event type not in consumed_events",
    )

    rows_affected: int = Field(
        default=0,
        ge=0,
        description="Number of rows affected by the projection (must be >= 0)",
    )

    error: str | None = Field(
        default=None,
        description="Error message if projection failed",
    )

    @model_validator(mode="after")
    def _validate_semantic_consistency(self) -> Self:
        """Validate semantic consistency between fields.

        This validator documents expected field relationships but does NOT
        enforce them strictly, allowing flexibility for edge cases.

        Semantic Expectations (not enforced):
            - If ``skipped=True``, ``rows_affected`` should typically be 0
            - If ``success=False``, ``error`` should typically be set
            - If ``success=True`` and not skipped, ``rows_affected >= 0``
              (enforced by field constraint)

        The model intentionally allows "unusual" combinations for flexibility:
            - ``success=True`` with ``error`` set (for warnings)
            - ``skipped=True`` with ``rows_affected > 0`` (partial processing)

        Returns:
            Self: The validated model instance (unchanged).

        Note:
            The ``rows_affected >= 0`` constraint is enforced at the field
            level via ``ge=0``, not in this validator.
        """
        # No hard enforcement - just return self
        # The docstring documents semantic expectations for callers
        return self

    def __repr__(self) -> str:
        """Return a concise representation for debugging.

        Returns:
            String representation showing key attributes.

        Examples:
            >>> result = ModelProjectionResult(success=True, rows_affected=1)
            >>> repr(result)
            'ModelProjectionResult(success=True, skipped=False, rows_affected=1)'

            >>> result = ModelProjectionResult(success=False, error="DB error")
            >>> repr(result)
            "ModelProjectionResult(success=False, skipped=False, rows_affected=0, error='DB error')"
        """
        base = (
            f"ModelProjectionResult(success={self.success}, "
            f"skipped={self.skipped}, rows_affected={self.rows_affected}"
        )
        if self.error is not None:
            return f"{base}, error={self.error!r})"
        return f"{base})"
