# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Projection Result Model.

Represents the result of a projection operation, including success status,
number of rows affected, and any error information. This model is returned
by projector implementations after processing an event.

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

from pydantic import BaseModel, ConfigDict, Field

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
            Zero for skipped events or failed projections.
        error: Error message if the projection failed. None for successful
            or skipped projections.

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
        description="Number of rows affected by the projection",
    )

    error: str | None = Field(
        default=None,
        description="Error message if projection failed",
    )

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
