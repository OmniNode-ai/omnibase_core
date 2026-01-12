"""
Retry Execution Model.

Execution tracking and state management for retries.
Part of the ModelRetryPolicy restructuring to reduce excessive string fields.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.types.type_serializable_value import SerializedDict

from .model_retry_failure_info import ModelRetryFailureInfo


class ModelRetryExecution(BaseModel):
    """
    Retry execution tracking and state.

    Contains execution state, timing, and error tracking
    without configuration concerns.
    Implements Core protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    """

    # Execution tracking
    current_attempt: int = Field(
        default=0,
        description="Current retry attempt number",
        ge=0,
    )
    last_attempt_time: ModelSchemaValue = Field(
        default_factory=lambda: ModelSchemaValue.from_value(""),
        description="Timestamp of last retry attempt as ISO string",
    )
    error_message: ModelSchemaValue = Field(
        default_factory=lambda: ModelSchemaValue.from_value(""),
        description="Last error message encountered",
    )
    last_status_code: ModelSchemaValue = Field(
        default_factory=lambda: ModelSchemaValue.from_value(0),
        description="Last HTTP status code encountered",
    )

    # Success tracking
    total_execution_time_seconds: float = Field(
        default=0.0,
        description="Total time spent across all attempts",
        ge=0.0,
    )
    successful_attempt: ModelSchemaValue = Field(
        default_factory=lambda: ModelSchemaValue.from_value(0),
        description="Attempt number that succeeded (0 if none)",
    )

    def can_retry(self, max_retries: int) -> bool:
        """Check if retries are still available."""
        return self.current_attempt < max_retries

    def is_exhausted(self, max_retries: int) -> bool:
        """Check if all retries have been exhausted."""
        return self.current_attempt >= max_retries

    def get_retry_attempts_made(self) -> int:
        """Get number of retry attempts made (excluding initial attempt)."""
        return max(0, self.current_attempt - 1)

    def get_success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.current_attempt == 0:
            return 0.0
        successful_value = self.successful_attempt.to_value()
        if isinstance(successful_value, int) and successful_value > 0:
            return 100.0
        return 0.0

    def record_attempt(
        self,
        success: bool = False,
        error: Exception | None = None,
        status_code: int = 0,
        execution_time_seconds: float = 0.0,
    ) -> None:
        """Record the result of an attempt."""
        self.current_attempt += 1
        self.last_attempt_time = ModelSchemaValue.from_value(
            datetime.now(UTC).isoformat(),
        )
        self.total_execution_time_seconds += execution_time_seconds

        if error is not None:
            self.error_message = ModelSchemaValue.from_value(str(error))
        if status_code != 0:
            self.last_status_code = ModelSchemaValue.from_value(status_code)

        if success:
            successful_value = self.successful_attempt.to_value()
            if not isinstance(successful_value, int) or successful_value == 0:
                self.successful_attempt = ModelSchemaValue.from_value(
                    self.current_attempt,
                )

    def get_next_attempt_time(self, delay_seconds: float) -> datetime:
        """Get timestamp for next retry attempt."""
        return datetime.now(UTC) + timedelta(seconds=delay_seconds)

    def get_average_execution_time(self) -> float:
        """Get average execution time per attempt."""
        if self.current_attempt == 0:
            return 0.0
        return self.total_execution_time_seconds / self.current_attempt

    def reset(self) -> None:
        """Reset execution state to initial values."""
        self.current_attempt = 0
        self.last_attempt_time = ModelSchemaValue.from_value("")
        self.error_message = ModelSchemaValue.from_value("")
        self.last_status_code = ModelSchemaValue.from_value(0)
        self.total_execution_time_seconds = 0.0
        self.successful_attempt = ModelSchemaValue.from_value(0)

    def is_successful(self) -> bool:
        """Check if execution was successful."""
        successful_value = self.successful_attempt.to_value()
        return isinstance(successful_value, int) and successful_value > 0

    def get_failure_info(self) -> ModelRetryFailureInfo:
        """Get failure information."""
        error_value = self.error_message.to_value()
        status_value = self.last_status_code.to_value()

        error_str = error_value if isinstance(error_value, str) else ""
        status_int = status_value if isinstance(status_value, int) else 0

        return ModelRetryFailureInfo.from_retry_execution(
            last_error=error_str,
            last_status_code=status_int,
            attempts_made=self.current_attempt,
        )

    def has_recent_attempt(self, seconds: int = 60) -> bool:
        """Check if there was a recent attempt."""
        time_value = self.last_attempt_time.to_value()
        if not isinstance(time_value, str) or time_value == "":
            return False
        try:
            last_time = datetime.fromisoformat(time_value.replace("Z", "+00:00"))
            delta = datetime.now(UTC) - last_time
            return delta.total_seconds() <= seconds
        except (AttributeError, ValueError):
            return False

    @classmethod
    def create_fresh(cls) -> ModelRetryExecution:
        """Create fresh execution state."""
        return cls()

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol).

        Raises:
            AttributeError: If setting an attribute fails
            Exception: If execution logic fails
        """
        # Update any relevant execution fields
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return True

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol).

        Raises:
            AttributeError: If setting an attribute fails
            Exception: If configuration logic fails
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return True

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


# Export for use
__all__ = ["ModelRetryExecution"]
