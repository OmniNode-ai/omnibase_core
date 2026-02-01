"""
Time-Based Model.

Universal time-based model replacing ModelDuration, ModelTimeout, and timing
aspects of ModelProgress with a single generic type-safe implementation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_runtime_category import EnumRuntimeCategory
from omnibase_core.enums.enum_time_unit import EnumTimeUnit
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelTimeBased[T: (int, float)](BaseModel):
    """
    Universal time-based model replacing Duration, Timeout, and timing aspects.

    This generic model provides a unified interface for all time-based operations,
    supporting both integer and float values with flexible unit conversion.
    Implements Core protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    """

    value: T = Field(default=..., description="The time-based value")
    unit: EnumTimeUnit = Field(default=EnumTimeUnit.SECONDS, description="Time unit")
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Additional metadata for context",
    )

    # Timeout-specific fields (optional)
    warning_threshold_value: T | None = Field(
        default=None,
        description="Warning threshold value (in same unit)",
    )
    is_strict: bool = Field(
        default=True,
        description="Whether this is strictly enforced (for timeouts)",
    )
    allow_extension: bool = Field(
        default=False,
        description="Whether this can be extended (for timeouts)",
    )
    extension_limit_value: T | None = Field(
        default=None,
        description="Maximum extension value (in same unit)",
    )
    runtime_category: EnumRuntimeCategory | None = Field(
        default=None,
        description="Runtime category for this time value",
    )

    @model_validator(mode="after")
    def validate_warning_threshold(self) -> ModelTimeBased[T]:
        """Validate warning threshold is less than main value."""
        if self.warning_threshold_value is not None:
            if self.warning_threshold_value >= self.value:
                msg = "Warning threshold must be less than main value"
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg
                )
        return self

    @field_validator("extension_limit_value")
    @classmethod
    def validate_extension_limit(cls, v: T | None, info: ValidationInfo) -> T | None:
        """Validate extension limit when extension is allowed."""
        if v is not None and info.data.get("allow_extension", False) is False:
            msg = "Extension limit requires allow_extension=True"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg
            )
        return v

    def model_post_init(self, __context: object) -> None:
        """Post-initialization to set runtime category if not provided."""
        if self.runtime_category is None:
            seconds = self.to_seconds()
            self.runtime_category = EnumRuntimeCategory.from_seconds(seconds)

    def to_milliseconds(self) -> int:
        """Convert to milliseconds."""
        multiplier = self.unit.to_milliseconds_multiplier()
        if isinstance(self.value, float):
            return int(self.value * multiplier)
        return self.value * multiplier

    def to_seconds(self) -> float:
        """Convert to seconds."""
        return self.to_milliseconds() / 1000.0

    def to_minutes(self) -> float:
        """Convert to minutes."""
        return self.to_seconds() / 60.0

    def to_hours(self) -> float:
        """Convert to hours."""
        return self.to_seconds() / 3600.0

    def to_days(self) -> float:
        """Convert to days."""
        return self.to_seconds() / (24 * 3600.0)

    def to_timedelta(self) -> timedelta:
        """Convert to timedelta object."""
        return timedelta(seconds=self.to_seconds())

    def is_zero(self) -> bool:
        """Check if value is zero."""
        return self.value == 0

    def is_positive(self) -> bool:
        """Check if value is positive."""
        return self.value > 0

    def __str__(self) -> str:
        """Return human-readable time string."""
        if self.is_zero():
            return f"0{self.unit.value}"

        # For display, convert to most appropriate unit
        ms = self.to_milliseconds()
        if ms == 0:
            return "0ms"

        parts = []
        remaining_ms = ms

        # Days
        days = remaining_ms // (24 * 60 * 60 * 1000)
        if days > 0:
            parts.append(f"{days}d")
            remaining_ms %= 24 * 60 * 60 * 1000

        # Hours
        hours = remaining_ms // (60 * 60 * 1000)
        if hours > 0:
            parts.append(f"{hours}h")
            remaining_ms %= 60 * 60 * 1000

        # Minutes
        minutes = remaining_ms // (60 * 1000)
        if minutes > 0:
            parts.append(f"{minutes}m")
            remaining_ms %= 60 * 1000

        # Seconds
        seconds = remaining_ms // 1000
        if seconds > 0:
            parts.append(f"{seconds}s")
            remaining_ms %= 1000

        # Milliseconds
        if remaining_ms > 0:
            parts.append(f"{remaining_ms}ms")

        return "".join(parts)

    # Timeout-specific methods
    def get_deadline(self, start_time: datetime | None = None) -> datetime:
        """Get deadline datetime for this timeout."""
        if start_time is None:
            start_time = datetime.now(UTC)
        return start_time + self.to_timedelta()

    def get_warning_time(self, start_time: datetime | None = None) -> datetime | None:
        """Get warning datetime for this timeout."""
        if self.warning_threshold_value is None:
            return None
        if start_time is None:
            start_time = datetime.now(UTC)

        warning_time_based = ModelTimeBased(
            value=self.warning_threshold_value,
            unit=self.unit,
        )
        return start_time + warning_time_based.to_timedelta()

    def is_expired(
        self,
        start_time: datetime,
        current_time: datetime | None = None,
    ) -> bool:
        """Check if timeout has expired."""
        if current_time is None:
            current_time = datetime.now(UTC)
        deadline = self.get_deadline(start_time)
        return current_time >= deadline

    def is_warning_triggered(
        self,
        start_time: datetime,
        current_time: datetime | None = None,
    ) -> bool:
        """Check if warning threshold has been reached."""
        warning_time = self.get_warning_time(start_time)
        if warning_time is None:
            return False
        if current_time is None:
            current_time = datetime.now(UTC)
        return current_time >= warning_time

    def get_remaining_seconds(
        self,
        start_time: datetime,
        current_time: datetime | None = None,
    ) -> float:
        """Get remaining seconds until timeout."""
        if current_time is None:
            current_time = datetime.now(UTC)
        deadline = self.get_deadline(start_time)
        remaining = deadline - current_time
        return max(0.0, remaining.total_seconds())

    def get_elapsed_seconds(
        self,
        start_time: datetime,
        current_time: datetime | None = None,
    ) -> float:
        """Get elapsed seconds since start."""
        if current_time is None:
            current_time = datetime.now(UTC)
        elapsed = current_time - start_time
        return elapsed.total_seconds()

    def get_progress_percentage(
        self,
        start_time: datetime,
        current_time: datetime | None = None,
    ) -> float:
        """Get timeout progress as percentage (0-100)."""
        elapsed = self.get_elapsed_seconds(start_time, current_time)
        total_seconds = self.to_seconds()
        if total_seconds <= 0:
            return 100.0
        return min(100.0, (elapsed / total_seconds) * 100.0)

    def extend_time(self, additional_value: T) -> bool:
        """Extend time by additional value if allowed."""
        if not self.allow_extension:
            return False

        if self.extension_limit_value is not None:
            if additional_value > self.extension_limit_value:
                return False

        # Extend the value
        if isinstance(self.value, (int, float)) and isinstance(
            additional_value,
            (int, float),
        ):
            self.value = self.value + additional_value
            # Update runtime category based on new timeout
            self.runtime_category = EnumRuntimeCategory.from_seconds(self.to_seconds())
            return True
        return False

    # Class methods for creating instances
    @classmethod
    def duration(
        cls,
        value: T,
        unit: EnumTimeUnit = EnumTimeUnit.SECONDS,
        description: str | None = None,
    ) -> ModelTimeBased[T]:
        """Create a duration instance."""
        metadata = {"type": "duration"}
        if description:
            metadata["description"] = description
        return cls(value=value, unit=unit, metadata=metadata)

    @classmethod
    def timeout(
        cls,
        value: T,
        unit: EnumTimeUnit = EnumTimeUnit.SECONDS,
        description: str | None = None,
        is_strict: bool = True,
        warning_threshold_value: T | None = None,
        allow_extension: bool = False,
        extension_limit_value: T | None = None,
    ) -> ModelTimeBased[T]:
        """Create a timeout instance."""
        metadata = {"type": "timeout"}
        if description:
            metadata["description"] = description
        return cls(
            value=value,
            unit=unit,
            metadata=metadata,
            is_strict=is_strict,
            warning_threshold_value=warning_threshold_value,
            allow_extension=allow_extension,
            extension_limit_value=extension_limit_value,
        )

    @classmethod
    def from_milliseconds(cls, ms: int) -> ModelTimeBased[int]:
        """Create from milliseconds."""
        return ModelTimeBased[int](value=ms, unit=EnumTimeUnit.MILLISECONDS)

    @classmethod
    def from_seconds(cls, seconds: float) -> ModelTimeBased[float]:
        """Create from seconds."""
        return ModelTimeBased[float](value=seconds, unit=EnumTimeUnit.SECONDS)

    @classmethod
    def from_minutes(cls, minutes: float) -> ModelTimeBased[float]:
        """Create from minutes."""
        return ModelTimeBased[float](value=minutes, unit=EnumTimeUnit.MINUTES)

    @classmethod
    def from_hours(cls, hours: float) -> ModelTimeBased[float]:
        """Create from hours."""
        return ModelTimeBased[float](value=hours, unit=EnumTimeUnit.HOURS)

    @classmethod
    def from_days(cls, days: float) -> ModelTimeBased[float]:
        """Create from days."""
        return ModelTimeBased[float](value=days, unit=EnumTimeUnit.DAYS)

    @classmethod
    def zero(cls) -> ModelTimeBased[int]:
        """Create zero duration."""
        return ModelTimeBased[int](value=0, unit=EnumTimeUnit.MILLISECONDS)

    @classmethod
    def from_timedelta(cls, delta: timedelta) -> ModelTimeBased[float]:
        """Create from timedelta object."""
        return ModelTimeBased[float](
            value=delta.total_seconds(),
            unit=EnumTimeUnit.SECONDS,
        )

    @classmethod
    def from_runtime_category(
        cls,
        category: EnumRuntimeCategory,
        description: str | None = None,
        use_max_estimate: bool = True,
    ) -> ModelTimeBased[int]:
        """Create timeout from runtime category."""
        min_seconds, max_seconds = category.estimated_seconds
        if use_max_estimate and max_seconds is not None:
            timeout_seconds = int(max_seconds)
        else:
            # Use minimum with some buffer
            timeout_seconds = max(int(min_seconds * 2), 30)

        metadata = {"type": "timeout"}
        if description:
            metadata["description"] = description

        return cls(
            value=timeout_seconds,
            unit=EnumTimeUnit.SECONDS,
            runtime_category=category,
            metadata=metadata,
        )  # type: ignore[return-value]

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
__all__ = ["ModelTimeBased"]
