"""Bootstrap result model for event bus initialization.

Thread Safety:
    ModelEventBusBootstrapResult instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelEventBusBootstrapResult(BaseModel):
    """
    Result model for event bus bootstrap operations (canonical, ONEX-compatible).

    Represents the outcome of an event bus bootstrap/initialization operation,
    including success/failure status and a descriptive message.

    Attributes:
        status: Bootstrap status indicator (e.g., 'ok', 'error', 'pending').
        message: Human-readable description of the bootstrap result.
    """

    # Note on frozen=True: This bootstrap result is immutable to prevent accidental
    # mutation after creation. Use a new instance for different results.
    # Note on from_attributes=True: Added for pytest-xdist parallel execution
    # compatibility. See CLAUDE.md "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    status: str = Field(
        ...,
        description="Bootstrap status, e.g. 'ok' or 'error'.",
    )
    message: str = Field(
        ...,
        description="Human-readable message about the bootstrap result.",
    )

    def is_successful(self) -> bool:
        """Check if the bootstrap was successful."""
        return self.status.lower() == "ok"

    def is_failed(self) -> bool:
        """Check if the bootstrap failed."""
        return self.status.lower() == "error"

    @classmethod
    def create_success(
        cls, message: str = "Bootstrap completed successfully"
    ) -> "ModelEventBusBootstrapResult":
        """Create a successful bootstrap result."""
        return cls(status="ok", message=message)

    @classmethod
    def create_failure(cls, message: str) -> "ModelEventBusBootstrapResult":
        """Create a failed bootstrap result."""
        return cls(status="error", message=message)


__all__ = ["ModelEventBusBootstrapResult"]
