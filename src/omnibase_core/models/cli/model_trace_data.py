"""
Trace Data Model.

Restrictive model for CLI execution trace data
with proper typing and validation.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelTraceData(BaseModel):
    """Restrictive model for trace data.

    Provides serialization and validation utilities for CLI trace data.
    Note: Uses Pydantic BaseModel for validation, not protocol-based interfaces.
    """

    trace_id: UUID = Field(description="Unique trace identifier")
    span_id: UUID = Field(description="Span identifier")
    parent_span_id: UUID | None = Field(
        default=None, description="Parent span identifier"
    )
    start_time: datetime = Field(description="Start timestamp")
    end_time: datetime = Field(description="End timestamp")
    duration_ms: float = Field(ge=0, description="Duration in milliseconds")
    tags: dict[str, str] = Field(default_factory=dict, description="Trace tags")
    logs: list[str] = Field(default_factory=list, description="Trace log entries")

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Utility methods

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def get_name(self) -> str:
        """Get a display name for this trace data."""
        # Try common name field patterns
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        return f"Unnamed {self.__class__.__name__}"

    def set_name(self, name: str) -> None:
        """Set a display name for this trace data."""
        # Try to set the most appropriate name field
        for field in ["name", "display_name", "title", "node_name"]:
            if hasattr(self, field):
                setattr(self, field, name)
                return

    def validate_instance(self) -> bool:
        """Validate instance integrity.

        Validates:
        - end_time is after start_time
        - duration_ms matches time difference
        - duration_ms is non-negative

        Returns:
            True if validation passes

        Raises:
            ModelOnexError: If validation fails
        """
        # Validate temporal consistency
        if self.end_time < self.start_time:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="end_time must be after start_time",
                context={
                    "start_time": self.start_time.isoformat(),
                    "end_time": self.end_time.isoformat(),
                },
            )

        # Validate duration is non-negative
        if self.duration_ms < 0:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="duration_ms must be non-negative",
                context={"duration_ms": self.duration_ms},
            )

        # Validate duration matches time difference (with tolerance for rounding)
        time_delta_ms = (self.end_time - self.start_time).total_seconds() * 1000
        tolerance_ms = 1.0  # 1ms tolerance for floating point precision
        if abs(time_delta_ms - self.duration_ms) > tolerance_ms:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="duration_ms does not match time difference",
                context={
                    "duration_ms": self.duration_ms,
                    "calculated_duration_ms": time_delta_ms,
                    "tolerance_ms": tolerance_ms,
                },
            )

        return True
