"""
Execution Statistics Models

Models for tracking execution errors, warnings, retries, and other statistics.
"""

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_onex_error import ModelOnexError
from omnibase_core.models.core.model_onex_warning import ModelOnexWarning


class ModelRetryAttempt(BaseModel):
    """Model for tracking retry attempts."""

    attempt_number: int = Field(..., description="Retry attempt number (1-based)")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When the retry was attempted"
    )
    reason: str = Field(..., description="Reason for retry")
    delay_ms: int | None = Field(None, description="Delay before retry in milliseconds")
    success: bool = Field(False, description="Whether the retry was successful")
    error_message: str | None = Field(None, description="Error message if retry failed")


class ModelExecutionStatistics(BaseModel):
    """Model for execution error, warning, and retry tracking."""

    # Error tracking
    errors: List[ModelOnexError] = Field(
        default_factory=list, description="List of errors encountered during execution"
    )

    # Warning tracking
    warnings: List[ModelOnexWarning] = Field(
        default_factory=list,
        description="List of warnings encountered during execution",
    )

    # Retry tracking
    retries: List[ModelRetryAttempt] = Field(
        default_factory=list, description="List of retry attempts made during execution"
    )

    @property
    def error_count(self) -> int:
        """Get the total number of errors."""
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        """Get the total number of warnings."""
        return len(self.warnings)

    @property
    def retry_count(self) -> int:
        """Get the total number of retries."""
        return len(self.retries)

    def add_error(self, error: ModelOnexError) -> None:
        """Add an error to the tracking."""
        self.errors.append(error)

    def add_warning(self, warning: ModelOnexWarning) -> None:
        """Add a warning to the tracking."""
        self.warnings.append(warning)

    def add_retry(self, retry: ModelRetryAttempt) -> None:
        """Add a retry attempt to the tracking."""
        self.retries.append(retry)

    def get_last_error(self) -> ModelOnexError | None:
        """Get the most recent error, if any."""
        return self.errors[-1] if self.errors else None

    def get_last_warning(self) -> ModelOnexWarning | None:
        """Get the most recent warning, if any."""
        return self.warnings[-1] if self.warnings else None

    def has_critical_errors(self) -> bool:
        """Check if there are any critical errors."""
        return any(
            error.status.name == "CRITICAL" if hasattr(error.status, "name") else False
            for error in self.errors
        )

    def get_successful_retries(self) -> List[ModelRetryAttempt]:
        """Get all successful retry attempts."""
        return [retry for retry in self.retries if retry.success]

    def get_failed_retries(self) -> List[ModelRetryAttempt]:
        """Get all failed retry attempts."""
        return [retry for retry in self.retries if not retry.success]
