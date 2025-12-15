"""
Discovery Error Model

Base exception for discovery-related errors with correlation tracking.
"""

from uuid import UUID


class ModelDiscoveryError(Exception):
    """
    Base exception for discovery-related errors.

    Includes correlation ID tracking and registry error aggregation.
    """

    def __init__(
        self,
        message: str,
        correlation_id: UUID | None = None,
        registry_errors: list[str] | None = None,
    ):
        """
        Initialize discovery error.

        Args:
            message: Error message describing the failure
            correlation_id: Request correlation ID for tracking
            registry_errors: Specific errors from registry services
        """
        super().__init__(message)
        self.correlation_id = correlation_id
        self.registry_errors = registry_errors if registry_errors is not None else []

    def has_registry_errors(self) -> bool:
        """Check if specific registry errors were reported"""
        return len(self.registry_errors) > 0

    def get_error_summary(self) -> str:
        """Get a summary of all errors for logging"""
        parts = [str(self)]
        if self.correlation_id:
            parts.append(f"correlation_id: {self.correlation_id}")
        if self.registry_errors:
            parts.append(f"registry_errors: {', '.join(self.registry_errors)}")
        return " | ".join(parts)
