"""
Retry Execution Model.

Execution tracking and state management for retries.
Part of the ModelRetryPolicy restructuring to reduce excessive string fields.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field

from .model_retry_failure_info import ModelRetryFailureInfo


class ModelRetryExecution(BaseModel):
    """
    Retry execution tracking and state.

    Contains execution state, timing, and error tracking
    without configuration concerns.
    """

    # Execution tracking
    current_attempt: int = Field(
        default=0,
        description="Current retry attempt number",
        ge=0,
    )
    last_attempt_time: datetime | None = Field(
        default=None,
        description="Timestamp of last retry attempt",
    )
    last_error: str | None = Field(
        default=None,
        description="Last error message encountered",
    )
    last_status_code: int | None = Field(
        default=None,
        description="Last HTTP status code encountered",
    )

    # Success tracking
    total_execution_time_seconds: float = Field(
        default=0.0,
        description="Total time spent across all attempts",
        ge=0.0,
    )
    successful_attempt: int | None = Field(
        default=None,
        description="Attempt number that succeeded (if any)",
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
        if self.successful_attempt is not None:
            return 100.0
        return 0.0

    def record_attempt(
        self,
        success: bool = False,
        error: Exception | None = None,
        status_code: int | None = None,
        execution_time_seconds: float = 0.0,
    ) -> None:
        """Record the result of an attempt."""
        self.current_attempt += 1
        self.last_attempt_time = datetime.now(UTC)
        self.total_execution_time_seconds += execution_time_seconds

        if error is not None:
            self.last_error = str(error)
        if status_code is not None:
            self.last_status_code = status_code

        if success and self.successful_attempt is None:
            self.successful_attempt = self.current_attempt

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
        self.last_attempt_time = None
        self.last_error = None
        self.last_status_code = None
        self.total_execution_time_seconds = 0.0
        self.successful_attempt = None

    def is_successful(self) -> bool:
        """Check if execution was successful."""
        return self.successful_attempt is not None

    def get_failure_info(self) -> ModelRetryFailureInfo:
        """Get failure information."""
        return ModelRetryFailureInfo.from_retry_execution(
            last_error=self.last_error,
            last_status_code=self.last_status_code,
            attempts_made=self.current_attempt,
        )

    def has_recent_attempt(self, seconds: int = 60) -> bool:
        """Check if there was a recent attempt."""
        if not self.last_attempt_time:
            return False
        delta = datetime.now(UTC) - self.last_attempt_time
        return delta.total_seconds() <= seconds

    @classmethod
    def create_fresh(cls) -> ModelRetryExecution:
        """Create fresh execution state."""
        return cls()


# Export for use
__all__ = ["ModelRetryExecution"]
