"""
Health Metrics Model

Health metrics for node instances including performance, resource usage,
and error tracking.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.types.type_serializable_value import SerializedDict


class ModelHealthMetrics(BaseModel):
    """
    Health metrics for node instances.

    This model tracks various health indicators including performance,
    resource usage, error rates, and availability.
    """

    cpu_usage_percent: float = Field(
        default=0.0,
        description="CPU usage percentage",
        ge=0.0,
        le=100.0,
    )

    memory_usage_mb: int = Field(
        default=0,
        description="Memory usage in megabytes",
        ge=0,
    )

    memory_usage_percent: float = Field(
        default=0.0,
        description="Memory usage percentage",
        ge=0.0,
        le=100.0,
    )

    response_time_ms: float = Field(
        default=0.0,
        description="Average response time in milliseconds",
        ge=0.0,
    )

    error_rate: float = Field(
        default=0.0,
        description="Error rate as percentage",
        ge=0.0,
        le=100.0,
    )

    success_rate: float = Field(
        default=100.0,
        description="Success rate as percentage",
        ge=0.0,
        le=100.0,
    )

    active_connections: int = Field(
        default=0,
        description="Number of active connections",
        ge=0,
    )

    requests_per_second: float = Field(
        default=0.0,
        description="Current requests per second",
        ge=0.0,
    )

    uptime_seconds: int = Field(default=0, description="Uptime in seconds", ge=0)

    last_error_timestamp: datetime | None = Field(
        default=None,
        description="Timestamp of last error",
    )

    consecutive_errors: int = Field(
        default=0,
        description="Number of consecutive errors",
        ge=0,
    )

    health_check_latency_ms: float | None = Field(
        default=None,
        description="Health check latency in milliseconds",
        ge=0.0,
    )

    # Uses SerializedDict for custom metrics (JSON-serializable values like strings, floats, etc.)
    custom_metrics: SerializedDict = Field(
        default_factory=dict,
        description="Custom health metrics (can include strings, floats, etc.)",
    )

    def is_healthy(
        self,
        cpu_threshold: float = 90.0,
        memory_threshold: float = 90.0,
        error_threshold: float = 10.0,
    ) -> bool:
        """
        Check if metrics indicate healthy state.

        Args:
            cpu_threshold: Maximum acceptable CPU usage
            memory_threshold: Maximum acceptable memory usage
            error_threshold: Maximum acceptable error rate

        Returns:
            True if all metrics are within healthy thresholds
        """
        # Check explicit status if set
        status = self.custom_metrics.get("status")
        if isinstance(status, str) and status in ["warning", "critical", "error"]:
            return False
        if isinstance(status, (int, float)) and status < 1.0:
            return False

        # Check metrics
        return (
            self.cpu_usage_percent <= cpu_threshold
            and self.memory_usage_percent <= memory_threshold
            and self.error_rate <= error_threshold
            and self.consecutive_errors < 5
        )

    def get_health_score(self) -> float:
        """
        Calculate overall health score (0.0 to 1.0).

        Returns:
            Health score where 1.0 is perfect health
        """
        # Weight different factors
        cpu_score = 1.0 - (self.cpu_usage_percent / 100.0)
        memory_score = 1.0 - (self.memory_usage_percent / 100.0)
        error_score = 1.0 - (self.error_rate / 100.0)

        # Response time score (assumes 1000ms is bad)
        response_score = max(0.0, 1.0 - (self.response_time_ms / 1000.0))

        # Weighted average
        weights = {"cpu": 0.2, "memory": 0.2, "error": 0.3, "response": 0.3}

        score = (
            cpu_score * weights["cpu"]
            + memory_score * weights["memory"]
            + error_score * weights["error"]
            + response_score * weights["response"]
        )

        # Penalize consecutive errors
        if self.consecutive_errors > 0:
            penalty = min(0.5, self.consecutive_errors * 0.1)
            score = score * (1.0 - penalty)

        return max(0.0, min(1.0, score))

    def add_custom_metric(self, name: str, value: float) -> None:
        """Add or update a custom metric."""
        self.custom_metrics[name] = value

    def get_custom_metric(self, name: str, default: float = 0.0) -> float:
        """Get a custom metric value.

        Args:
            name: The name of the custom metric to retrieve.
            default: Default value to return if metric not found or not convertible.

        Returns:
            The metric value as a float, or default if not found/convertible.

        Type Conversion Rules:
            - float: returned directly
            - bool: True -> 1.0, False -> 0.0 (checked before int due to subclass)
            - int: converted to float
            - str: parsed as float, returns default if parsing fails
            - other types: returns default

        Note:
            This method uses graceful degradation (returns default on failure)
            rather than raising exceptions, making it safe for use in health
            checks and monitoring code paths.
        """
        value = self.custom_metrics.get(name, default)
        # Type narrowing: ensure we return a float
        if isinstance(value, float):
            return value
        # NOTE: Check bool before int since bool is a subclass of int in Python
        # (isinstance(True, int) returns True, so bool must be checked first)
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        if isinstance(value, int):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except (TypeError, ValueError):
                # fallback-ok: return default if string conversion fails
                # ValueError: invalid float literal (e.g., "abc", "")
                # TypeError: defensive - should not occur but included for robustness
                return default
        return default

    @property
    def status(self) -> str:
        """
        Get health status from custom_metrics.

        Maps numeric status values to string status:
        - 1.0 or higher: "healthy"
        - 0.5-0.99: "warning"
        - Below 0.5: "critical"
        - Missing: inferred from metrics
        """
        status_value = self.custom_metrics.get("status")

        if isinstance(status_value, str):
            return status_value

        if isinstance(status_value, (int, float)):
            if status_value >= 1.0:
                return "healthy"
            elif status_value >= 0.5:
                return "warning"
            else:
                return "critical"

        # Infer from metrics if not explicitly set
        if self.is_healthy():
            return "healthy"
        elif self.error_rate >= 10.0 or self.consecutive_errors >= 5:
            return "critical"
        else:
            return "warning"
