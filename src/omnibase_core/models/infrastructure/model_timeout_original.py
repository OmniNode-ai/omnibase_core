"""
Timeout Model.

Specialized model for handling timeout configurations with validation and utilities.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field, field_validator

from ...enums.enum_runtime_category import EnumRuntimeCategory


class ModelTimeout(BaseModel):
    """
    Timeout configuration model.

    Provides comprehensive timeout handling with multiple time units,
    validation, and runtime category integration.
    """

    # Core timeout configuration
    timeout_seconds: int = Field(
        ...,
        description="Timeout value in seconds",
        ge=1,
        le=86400 * 30,  # Max 30 days
    )

    # Optional timeout configurations
    warning_threshold_seconds: int | None = Field(
        default=None,
        description="Warning threshold in seconds (triggers before timeout)",
        ge=1,
    )

    # Timeout behavior
    is_strict: bool = Field(
        default=True,
        description="Whether timeout is strictly enforced",
    )
    allow_extension: bool = Field(
        default=False,
        description="Whether timeout can be extended during execution",
    )
    extension_limit_seconds: int | None = Field(
        default=None,
        description="Maximum extension time in seconds",
        ge=1,
    )

    # Runtime categorization
    runtime_category: EnumRuntimeCategory | None = Field(
        default=None,
        description="Runtime category for this timeout",
    )

    # Metadata
    description: str | None = Field(
        default=None,
        description="Human-readable timeout description",
    )
    custom_metadata: dict[str, str | int | bool | float] = Field(
        default_factory=dict,
        description="Custom timeout metadata",
    )

    @field_validator("warning_threshold_seconds")
    @classmethod
    def validate_warning_threshold(cls, v: int | None, info: Any) -> int | None:
        """Validate warning threshold is less than timeout."""
        if v is not None and "timeout_seconds" in info.data:
            timeout = info.data["timeout_seconds"]
            if v >= timeout:
                msg = "Warning threshold must be less than timeout"
                raise ValueError(msg)
        return v

    @field_validator("extension_limit_seconds")
    @classmethod
    def validate_extension_limit(cls, v: int | None, info: Any) -> int | None:
        """Validate extension limit when extension is allowed."""
        if v is not None and info.data.get("allow_extension", False) is False:
            msg = "Extension limit requires allow_extension=True"
            raise ValueError(msg)
        return v

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization to set runtime category if not provided."""
        if self.runtime_category is None:
            self.runtime_category = EnumRuntimeCategory.from_seconds(
                self.timeout_seconds
            )

    @property
    def timeout_timedelta(self) -> timedelta:
        """Get timeout as timedelta object."""
        return timedelta(seconds=self.timeout_seconds)

    @property
    def timeout_minutes(self) -> float:
        """Get timeout in minutes."""
        return self.timeout_seconds / 60.0

    @property
    def timeout_hours(self) -> float:
        """Get timeout in hours."""
        return self.timeout_seconds / 3600.0

    @property
    def warning_threshold_timedelta(self) -> timedelta | None:
        """Get warning threshold as timedelta object."""
        if self.warning_threshold_seconds is None:
            return None
        return timedelta(seconds=self.warning_threshold_seconds)

    @property
    def extension_limit_timedelta(self) -> timedelta | None:
        """Get extension limit as timedelta object."""
        if self.extension_limit_seconds is None:
            return None
        return timedelta(seconds=self.extension_limit_seconds)

    @property
    def max_total_seconds(self) -> int:
        """Get maximum total seconds including extensions."""
        base = self.timeout_seconds
        if self.allow_extension and self.extension_limit_seconds is not None:
            return base + self.extension_limit_seconds
        return base

    def get_deadline(self, start_time: datetime | None = None) -> datetime:
        """Get deadline datetime for this timeout."""
        if start_time is None:
            start_time = datetime.now(UTC)
        return start_time + self.timeout_timedelta

    def get_warning_time(self, start_time: datetime | None = None) -> datetime | None:
        """Get warning datetime for this timeout."""
        if self.warning_threshold_seconds is None:
            return None
        if start_time is None:
            start_time = datetime.now(UTC)
        return start_time + timedelta(seconds=self.warning_threshold_seconds)

    def is_expired(
        self, start_time: datetime, current_time: datetime | None = None
    ) -> bool:
        """Check if timeout has expired."""
        if current_time is None:
            current_time = datetime.now(UTC)
        deadline = self.get_deadline(start_time)
        return current_time >= deadline

    def is_warning_triggered(
        self, start_time: datetime, current_time: datetime | None = None
    ) -> bool:
        """Check if warning threshold has been reached."""
        warning_time = self.get_warning_time(start_time)
        if warning_time is None:
            return False
        if current_time is None:
            current_time = datetime.now(UTC)
        return current_time >= warning_time

    def get_remaining_seconds(
        self, start_time: datetime, current_time: datetime | None = None
    ) -> float:
        """Get remaining seconds until timeout."""
        if current_time is None:
            current_time = datetime.now(UTC)
        deadline = self.get_deadline(start_time)
        remaining = deadline - current_time
        return max(0.0, remaining.total_seconds())

    def get_elapsed_seconds(
        self, start_time: datetime, current_time: datetime | None = None
    ) -> float:
        """Get elapsed seconds since start."""
        if current_time is None:
            current_time = datetime.now(UTC)
        elapsed = current_time - start_time
        return elapsed.total_seconds()

    def get_progress_percentage(
        self, start_time: datetime, current_time: datetime | None = None
    ) -> float:
        """Get timeout progress as percentage (0-100)."""
        elapsed = self.get_elapsed_seconds(start_time, current_time)
        return min(100.0, (elapsed / self.timeout_seconds) * 100.0)

    def extend_timeout(self, additional_seconds: int) -> bool:
        """Extend timeout by additional seconds if allowed."""
        if not self.allow_extension:
            return False

        if self.extension_limit_seconds is not None:
            max_extension = self.extension_limit_seconds
            if additional_seconds > max_extension:
                return False

        self.timeout_seconds += additional_seconds
        # Update runtime category based on new timeout
        self.runtime_category = EnumRuntimeCategory.from_seconds(self.timeout_seconds)
        return True

    @classmethod
    def from_seconds(
        cls,
        seconds: int,
        description: str | None = None,
        is_strict: bool = True,
    ) -> "ModelTimeout":
        """Create timeout from seconds."""
        return cls(
            timeout_seconds=seconds,
            description=description,
            is_strict=is_strict,
        )

    @classmethod
    def from_minutes(
        cls,
        minutes: float,
        description: str | None = None,
        is_strict: bool = True,
    ) -> "ModelTimeout":
        """Create timeout from minutes."""
        seconds = int(minutes * 60)
        return cls.from_seconds(seconds, description, is_strict)

    @classmethod
    def from_hours(
        cls,
        hours: float,
        description: str | None = None,
        is_strict: bool = True,
    ) -> "ModelTimeout":
        """Create timeout from hours."""
        seconds = int(hours * 3600)
        return cls.from_seconds(seconds, description, is_strict)

    @classmethod
    def from_runtime_category(
        cls,
        category: EnumRuntimeCategory,
        description: str | None = None,
        use_max_estimate: bool = True,
    ) -> "ModelTimeout":
        """Create timeout from runtime category."""
        min_seconds, max_seconds = category.estimated_seconds
        if use_max_estimate and max_seconds is not None:
            timeout_seconds = int(max_seconds)
        else:
            # Use minimum with some buffer
            timeout_seconds = max(int(min_seconds * 2), 30)

        return cls(
            timeout_seconds=timeout_seconds,
            runtime_category=category,
            description=description,
        )


# Export for use
__all__ = ["ModelTimeout"]
