"""
Duration Model.

A duration model that delegates to ModelTimeBased for unified time handling.
Provides convenient methods for working with time durations in various units.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_time_unit import EnumTimeUnit
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict

from .model_time_based import ModelTimeBased


class ModelDuration(BaseModel):
    """
    Duration model that provides convenient methods for time duration handling.

    This model delegates all operations to the unified ModelTimeBased model
    while providing an intuitive interface for duration operations.
    Implements Core protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    """

    time_based: ModelTimeBased[int] = Field(
        default_factory=lambda: ModelTimeBased(value=0, unit=EnumTimeUnit.MILLISECONDS),
        exclude=True,
        description="Internal time-based model",
    )

    def __init__(self, **data: object) -> None:
        """Initialize duration with flexible input formats."""
        # Handle various input formats
        if "milliseconds" in data:
            ms = data.pop("milliseconds")
            super().__init__()
            if isinstance(ms, (int, float)):
                self.time_based = ModelTimeBased(
                    value=int(ms),
                    unit=EnumTimeUnit.MILLISECONDS,
                )
            else:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="milliseconds must be a number",
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("typeerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "model_validation",
                            ),
                        },
                    ),
                )
        elif "seconds" in data:
            seconds = data.pop("seconds")
            super().__init__()
            if isinstance(seconds, (int, float)):
                self.time_based = ModelTimeBased(
                    value=int(seconds * 1000),
                    unit=EnumTimeUnit.MILLISECONDS,
                )
            else:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="seconds must be a number",
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("typeerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "model_validation",
                            ),
                        },
                    ),
                )
        elif "minutes" in data:
            minutes = data.pop("minutes")
            super().__init__()
            if isinstance(minutes, (int, float)):
                self.time_based = ModelTimeBased(
                    value=int(minutes * 60 * 1000),
                    unit=EnumTimeUnit.MILLISECONDS,
                )
            else:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="minutes must be a number",
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("typeerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "model_validation",
                            ),
                        },
                    ),
                )
        elif "hours" in data:
            hours = data.pop("hours")
            super().__init__()
            if isinstance(hours, (int, float)):
                self.time_based = ModelTimeBased(
                    value=int(hours * 60 * 60 * 1000),
                    unit=EnumTimeUnit.MILLISECONDS,
                )
            else:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="hours must be a number",
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("typeerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "model_validation",
                            ),
                        },
                    ),
                )
        elif "days" in data:
            days = data.pop("days")
            super().__init__()
            if isinstance(days, (int, float)):
                self.time_based = ModelTimeBased(
                    value=int(days * 24 * 60 * 60 * 1000),
                    unit=EnumTimeUnit.MILLISECONDS,
                )
            else:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="days must be a number",
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("typeerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "model_validation",
                            ),
                        },
                    ),
                )
        else:
            super().__init__(**data)

    @property
    def milliseconds(self) -> int:
        """Get duration in milliseconds."""
        return self.time_based.to_milliseconds()

    def total_milliseconds(self) -> int:
        """Get total duration in milliseconds."""
        return self.time_based.to_milliseconds()

    def total_seconds(self) -> float:
        """Get total duration in seconds."""
        return self.time_based.to_seconds()

    def total_minutes(self) -> float:
        """Get total duration in minutes."""
        return self.time_based.to_minutes()

    def total_hours(self) -> float:
        """Get total duration in hours."""
        return self.time_based.to_hours()

    def total_days(self) -> float:
        """Get total duration in days."""
        return self.time_based.to_days()

    def is_zero(self) -> bool:
        """Check if duration is zero."""
        return self.time_based.is_zero()

    def is_positive(self) -> bool:
        """Check if duration is positive."""
        return self.time_based.is_positive()

    def __str__(self) -> str:
        """Return human-readable duration string."""
        return str(self.time_based)

    @classmethod
    def from_milliseconds(cls, ms: int) -> ModelDuration:
        """Create duration from milliseconds."""
        instance = cls()
        instance.time_based = ModelTimeBased(value=ms, unit=EnumTimeUnit.MILLISECONDS)
        return instance

    @classmethod
    def from_seconds(cls, seconds: float) -> ModelDuration:
        """Create duration from seconds."""
        instance = cls()
        instance.time_based = ModelTimeBased(
            value=int(seconds * 1000),
            unit=EnumTimeUnit.MILLISECONDS,
        )
        return instance

    @classmethod
    def from_minutes(cls, minutes: float) -> ModelDuration:
        """Create duration from minutes."""
        instance = cls()
        instance.time_based = ModelTimeBased(
            value=int(minutes * 60 * 1000),
            unit=EnumTimeUnit.MILLISECONDS,
        )
        return instance

    @classmethod
    def from_hours(cls, hours: float) -> ModelDuration:
        """Create duration from hours."""
        instance = cls()
        instance.time_based = ModelTimeBased(
            value=int(hours * 60 * 60 * 1000),
            unit=EnumTimeUnit.MILLISECONDS,
        )
        return instance

    @classmethod
    def zero(cls) -> ModelDuration:
        """Create zero duration."""
        instance = cls()
        instance.time_based = ModelTimeBased.zero()
        return instance

    def get_time_based(self) -> ModelTimeBased[int]:
        """Get the underlying time-based model."""
        return self.time_based

    def model_dump(self, **kwargs: object) -> dict[str, int]:
        """Serialize model with typed return."""
        return {"milliseconds": self.milliseconds}

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
        # model_dump returns dict[str, int] which is compatible with SerializedDict
        result = self.model_dump(exclude_none=False, by_alias=True)
        return dict(result)  # Explicit conversion to SerializedDict


# Export for use
__all__ = ["ModelDuration"]
