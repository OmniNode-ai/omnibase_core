"""
ModelCorpusCaptureWindow - Capture window model for execution corpus.

This module provides the ModelCorpusCaptureWindow model which represents
the time window during which executions were collected for inclusion
in the corpus.

Thread Safety:
    ModelCorpusCaptureWindow is frozen (immutable) after creation, making it
    safe to share across threads.

Usage:
    .. code-block:: python

        from omnibase_core.models.replay import ModelCorpusCaptureWindow
        from datetime import datetime, UTC

        window = ModelCorpusCaptureWindow(
            start_time=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
            end_time=datetime(2024, 1, 8, 0, 0, 0, tzinfo=UTC),
        )
        print(f"Duration: {window.duration}")

Related:
    - OMN-1202: Execution Corpus Model for beta demo
    - ModelExecutionCorpus: Collection of execution manifests

.. versionadded:: 0.4.0
"""

from datetime import datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors import ModelOnexError


class ModelCorpusCaptureWindow(BaseModel):
    """
    Capture window for corpus collection.

    Represents the time window during which executions were collected
    for inclusion in the corpus.

    Attributes:
        start_time: Start of capture window.
        end_time: End of capture window.

    Properties:
        duration: Length of the capture window.

    Thread Safety:
        This model is frozen (immutable) after creation, making it safe
        to share across threads.

    Example:
        >>> window = ModelCorpusCaptureWindow(
        ...     start_time=datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        ...     end_time=datetime(2024, 1, 8, 0, 0, 0, tzinfo=UTC),
        ... )
        >>> window.duration
        timedelta(days=7)

    .. versionadded:: 0.4.0
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    start_time: datetime = Field(
        ...,
        description="Start of capture window",
    )

    end_time: datetime = Field(
        ...,
        description="End of capture window",
    )

    @model_validator(mode="after")
    def _validate_time_order(self) -> "ModelCorpusCaptureWindow":
        """Validate that start_time <= end_time.

        Returns:
            Self if validation passes.

        Raises:
            ModelOnexError: If start_time > end_time.
        """
        if self.start_time > self.end_time:
            msg = "start_time must be <= end_time"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return self

    @property
    def duration(self) -> timedelta:
        """Get the length of the capture window.

        Returns:
            The timedelta between end_time and start_time.
        """
        return self.end_time - self.start_time


__all__ = ["ModelCorpusCaptureWindow"]
