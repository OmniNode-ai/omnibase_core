"""
Progress Timing Model.

Timing and duration calculations for progress tracking.
Follows ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.infrastructure.model_time_based import ModelTimeBased
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelProgressTiming(BaseModel):
    """
    Progress timing with duration calculations and estimates.

    Focused on time-based progress tracking functionality.
    Implements Core protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    """

    # Timing information
    start_time: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Progress tracking start time",
    )
    last_update_time: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last progress update time",
    )
    estimated_completion_time: datetime | None = Field(
        default=None,
        description="Estimated completion time",
    )

    # Time-based calculations using ModelTimeBased
    estimated_total_duration: ModelTimeBased[float] | None = Field(
        default=None,
        description="Estimated total duration",
    )
    estimated_remaining_duration: ModelTimeBased[float] | None = Field(
        default=None,
        description="Estimated remaining duration",
    )

    @property
    def elapsed_time(self) -> timedelta:
        """Get elapsed time since start."""
        return datetime.now(UTC) - self.start_time

    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        return self.elapsed_time.total_seconds()

    @property
    def elapsed_minutes(self) -> float:
        """Get elapsed time in minutes."""
        return self.elapsed_seconds / 60.0

    @property
    def elapsed_time_based(self) -> ModelTimeBased[float]:
        """Get elapsed time as ModelTimeBased for consistent time operations."""
        return ModelTimeBased.from_seconds(self.elapsed_seconds)

    def update_timestamp(self) -> None:
        """Update the last update timestamp."""
        self.last_update_time = datetime.now(UTC)

    def update_time_estimates(self, current_percentage: float) -> None:
        """Update time estimates based on current progress percentage."""
        if current_percentage <= 0.0:
            self.estimated_total_duration = None
            self.estimated_remaining_duration = None
            self.estimated_completion_time = None
            return

        elapsed_seconds = self.elapsed_seconds
        estimated_total_seconds = (elapsed_seconds / current_percentage) * 100.0

        self.estimated_total_duration = ModelTimeBased.from_seconds(
            estimated_total_seconds,
        )

        if current_percentage >= 100.0:
            self.estimated_remaining_duration = ModelTimeBased.from_seconds(0.0)
            self.estimated_completion_time = datetime.now(UTC)
        else:
            remaining_seconds = estimated_total_seconds - elapsed_seconds
            self.estimated_remaining_duration = ModelTimeBased.from_seconds(
                max(0.0, remaining_seconds),
            )

            # Update estimated completion time
            if self.estimated_remaining_duration:
                self.estimated_completion_time = (
                    datetime.now(UTC) + self.estimated_remaining_duration.to_timedelta()
                )

        self.update_timestamp()

    def get_completion_rate_per_minute(self, current_percentage: float) -> float:
        """Get completion rate as percentage per minute."""
        if self.elapsed_minutes <= 0.0:
            return 0.0
        return current_percentage / self.elapsed_minutes

    def get_time_remaining_formatted(self) -> str:
        """Get formatted remaining time string."""
        if self.estimated_remaining_duration is None:
            return "Unknown"
        return str(self.estimated_remaining_duration)

    def get_elapsed_formatted(self) -> str:
        """Get formatted elapsed time string."""
        return str(self.elapsed_time_based)

    def get_estimated_total_formatted(self) -> str:
        """Get formatted estimated total time string."""
        if self.estimated_total_duration is None:
            return "Unknown"
        return str(self.estimated_total_duration)

    def reset(self) -> None:
        """Reset timing to initial state."""
        self.start_time = datetime.now(UTC)
        self.last_update_time = self.start_time
        self.estimated_completion_time = None
        self.estimated_total_duration = None
        self.estimated_remaining_duration = None

    @classmethod
    def create_started(cls) -> ModelProgressTiming:
        """Create timing instance with current timestamp."""
        return cls()

    @classmethod
    def create_with_start_time(cls, start_time: datetime) -> ModelProgressTiming:
        """Create timing instance with specific start time."""
        return cls(
            start_time=start_time,
            last_update_time=start_time,
        )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


# Export for use
__all__ = ["ModelProgressTiming"]
