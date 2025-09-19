"""
Health Status Enum for System Monitoring.

Provides strongly typed health status classifications for system monitoring,
health checks, and operational status reporting within the ONEX architecture.
"""

from enum import Enum


class EnumHealthStatus(str, Enum):
    """
    Health status classifications for system monitoring and health checks.

    Provides comprehensive health status options from healthy operation
    to critical failures with clear escalation hierarchy for monitoring systems.
    """

    # Healthy states
    HEALTHY = "healthy"
    AVAILABLE = "available"

    # Warning states
    DEGRADED = "degraded"
    WARNING = "warning"

    # Error states
    UNHEALTHY = "unhealthy"
    UNAVAILABLE = "unavailable"
    ERROR = "error"
    UNREACHABLE = "unreachable"

    # Critical states
    CRITICAL = "critical"

    # Unknown states
    UNKNOWN = "unknown"

    @classmethod
    def get_all_statuses(cls) -> list[str]:
        """Get all available health statuses."""
        return [status.value for status in cls]

    @classmethod
    def get_healthy_statuses(cls) -> list[str]:
        """Get health statuses that indicate healthy operation."""
        return [cls.HEALTHY.value, cls.AVAILABLE.value]

    @classmethod
    def get_warning_statuses(cls) -> list[str]:
        """Get health statuses that indicate warning conditions."""
        return [cls.DEGRADED.value, cls.WARNING.value]

    @classmethod
    def get_error_statuses(cls) -> list[str]:
        """Get health statuses that indicate error conditions."""
        return [
            cls.UNHEALTHY.value,
            cls.UNAVAILABLE.value,
            cls.ERROR.value,
            cls.UNREACHABLE.value,
        ]

    @classmethod
    def get_critical_statuses(cls) -> list[str]:
        """Get health statuses that indicate critical failures."""
        return [cls.CRITICAL.value]

    @classmethod
    def is_healthy(cls, status: str) -> bool:
        """Check if a health status indicates healthy operation."""
        return status in cls.get_healthy_statuses()

    @classmethod
    def is_warning(cls, status: str) -> bool:
        """Check if a health status indicates warning condition."""
        return status in cls.get_warning_statuses()

    @classmethod
    def is_error(cls, status: str) -> bool:
        """Check if a health status indicates error condition."""
        return status in cls.get_error_statuses()

    @classmethod
    def is_critical(cls, status: str) -> bool:
        """Check if a health status indicates critical failure."""
        return status in cls.get_critical_statuses()

    @classmethod
    def get_severity_level(cls, status: str) -> int:
        """Get numeric severity level (0=healthy, 4=critical)."""
        severity_map = {
            # Healthy states (0)
            cls.HEALTHY.value: 0,
            cls.AVAILABLE.value: 0,
            # Warning states (1)
            cls.DEGRADED.value: 1,
            cls.WARNING.value: 1,
            # Error states (2-3)
            cls.UNHEALTHY.value: 2,
            cls.UNAVAILABLE.value: 2,
            cls.ERROR.value: 3,
            cls.UNREACHABLE.value: 3,
            # Critical states (4)
            cls.CRITICAL.value: 4,
            # Unknown (default to warning level)
            cls.UNKNOWN.value: 1,
        }
        return severity_map.get(status, 1)  # Default to warning level

    def __str__(self) -> str:
        """Return the enum value as string."""
        return self.value

    def __repr__(self) -> str:
        """Return detailed representation."""
        return f"EnumHealthStatus.{self.name}"
