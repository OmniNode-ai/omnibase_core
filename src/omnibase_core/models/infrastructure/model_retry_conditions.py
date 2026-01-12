"""
Retry Conditions Model.

Retry trigger conditions and decision logic.
Part of the ModelRetryPolicy restructuring to reduce excessive string fields.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types.type_serializable_value import SerializedDict


class ModelRetryConditions(BaseModel):
    """
    Retry conditions and trigger logic.

    Contains rules for when retries should be attempted
    without configuration or execution tracking concerns.
    Implements Core protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    """

    # Retry conditions
    retry_on_exceptions: list[str] = Field(
        default_factory=lambda: ["ConnectionError", "TimeoutError", "HTTPError"],
        description="Exception types that should trigger retries",
    )
    retry_on_status_codes: list[int] = Field(
        default_factory=lambda: [429, 500, 502, 503, 504],
        description="HTTP status codes that should trigger retries",
    )
    stop_on_success: bool = Field(
        default=True,
        description="Whether to stop retrying on success",
    )

    def should_retry_exception(self, error: Exception) -> bool:
        """Check if exception should trigger retry."""
        error_type = type(error).__name__
        return error_type in self.retry_on_exceptions

    def should_retry_status_code(self, status_code: int) -> bool:
        """Check if status code should trigger retry."""
        return status_code in self.retry_on_status_codes

    def add_exception_type(self, exception_type: str) -> None:
        """Add exception type to retry list[Any]."""
        if exception_type not in self.retry_on_exceptions:
            self.retry_on_exceptions.append(exception_type)

    def remove_exception_type(self, exception_type: str) -> None:
        """Remove exception type from retry list[Any]."""
        if exception_type in self.retry_on_exceptions:
            self.retry_on_exceptions.remove(exception_type)

    def add_status_code(self, status_code: int) -> None:
        """Add status code to retry list[Any]."""
        if status_code not in self.retry_on_status_codes:
            self.retry_on_status_codes.append(status_code)

    def remove_status_code(self, status_code: int) -> None:
        """Remove status code from retry list[Any]."""
        if status_code in self.retry_on_status_codes:
            self.retry_on_status_codes.remove(status_code)

    def get_exception_count(self) -> int:
        """Get number of exception types configured."""
        return len(self.retry_on_exceptions)

    def get_status_code_count(self) -> int:
        """Get number of status codes configured."""
        return len(self.retry_on_status_codes)

    def is_permissive(self) -> bool:
        """Check if conditions are permissive (many trigger conditions)."""
        return len(self.retry_on_exceptions) > 5 or len(self.retry_on_status_codes) > 5

    @classmethod
    def create_http_only(cls) -> ModelRetryConditions:
        """Create conditions for HTTP-only retries."""
        return cls(
            retry_on_exceptions=["HTTPError", "ConnectionError", "TimeoutError"],
            retry_on_status_codes=[429, 500, 502, 503, 504],
        )

    @classmethod
    def create_database_only(cls) -> ModelRetryConditions:
        """Create conditions for database retries."""
        return cls(
            retry_on_exceptions=[
                "DatabaseError",
                "ConnectionError",
                "OperationalError",
                "InterfaceError",
            ],
            retry_on_status_codes=[],  # No HTTP status codes for database
        )

    @classmethod
    def create_permissive(cls) -> ModelRetryConditions:
        """Create permissive retry conditions."""
        return cls(
            retry_on_exceptions=[
                "ConnectionError",
                "TimeoutError",
                "HTTPError",
                "RequestException",
                "NetworkError",
                "DatabaseError",
                "OperationalError",
                "InterfaceError",
            ],
            retry_on_status_codes=[408, 429, 500, 502, 503, 504, 507, 509],
        )

    @classmethod
    def create_strict(cls) -> ModelRetryConditions:
        """Create strict retry conditions."""
        return cls(
            retry_on_exceptions=["TimeoutError"],
            retry_on_status_codes=[503],  # Only service unavailable
        )

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
__all__ = ["ModelRetryConditions"]
