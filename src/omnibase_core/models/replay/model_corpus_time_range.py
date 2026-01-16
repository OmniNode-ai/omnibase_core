"""
ModelCorpusTimeRange - Time range model for execution corpus.

This module provides the ModelCorpusTimeRange model which represents
the min/max time range of execution manifests in a corpus.

Thread Safety:
    ModelCorpusTimeRange is frozen (immutable) after creation, making it
    safe to share across threads.

Usage:
    .. code-block:: python

        from omnibase_core.models.replay import ModelCorpusTimeRange
        from datetime import datetime, UTC

        time_range = ModelCorpusTimeRange(
            min_time=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            max_time=datetime(2024, 1, 1, 13, 0, 0, tzinfo=UTC),
        )
        print(f"Duration: {time_range.duration}")

Related:
    - OMN-1202: Execution Corpus Model for beta demo
    - ModelExecutionCorpus: Collection of execution manifests

.. versionadded:: 0.4.0
"""

from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import ModelOnexError


class ModelCorpusTimeRange(BaseModel):
    """
    Time range for corpus executions.

    Represents the min/max time range of execution manifests in a corpus.

    Attributes:
        min_time: Earliest execution timestamp.
        max_time: Latest execution timestamp.

    Properties:
        duration: Time span between min and max.

    Thread Safety:
        This model is frozen (immutable) after creation, making it safe
        to share across threads.

    Example:
        >>> time_range = ModelCorpusTimeRange(
        ...     min_time=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        ...     max_time=datetime(2024, 1, 1, 13, 0, 0, tzinfo=UTC),
        ... )
        >>> time_range.duration
        timedelta(hours=1)

    .. versionadded:: 0.4.0
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    min_time: datetime = Field(
        ...,
        description="Earliest execution timestamp",
    )

    max_time: datetime = Field(
        ...,
        description="Latest execution timestamp",
    )

    @model_validator(mode="after")
    def _validate_time_order(self) -> "ModelCorpusTimeRange":
        """Validate that min_time <= max_time.

        Returns:
            Self if validation passes.

        Raises:
            ModelOnexError: If min_time > max_time.
        """
        if self.min_time > self.max_time:
            msg = "min_time must be <= max_time"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return self

    @property
    def duration(self) -> timedelta:
        """Get the time span between min and max.

        Returns:
            The timedelta between max_time and min_time.
        """
        return self.max_time - self.min_time


__all__ = ["ModelCorpusTimeRange"]
