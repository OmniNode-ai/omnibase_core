"""
Health check configuration model.
"""

from typing import Any

from pydantic import BaseModel, Field

class ModelHealthCheckConfig(BaseModel):
    """
    Health check configuration with typed fields.
    Replaces Dict[str, Any] for get_health_check_config() returns.
    """

    # Endpoint configuration
    endpoint: str = Field(..., description="Health check endpoint")
    method: str = Field("GET", description="HTTP method for health check")

    # Timing
    interval_seconds: int = Field(30, description="Health check interval")
    timeout_seconds: int = Field(10, description="Health check timeout")

    # Thresholds
    healthy_threshold: int = Field(2, description="Consecutive successes for healthy")
    unhealthy_threshold: int = Field(
        3,
        description="Consecutive failures for unhealthy",
    )

    # Expected response
    expected_status_codes: list[int] = Field(
        default_factory=lambda: [200, 204],
        description="Expected HTTP status codes",
    )
    expected_response_time_ms: int | None = Field(
        None,
        description="Maximum expected response time",
    )

    # Response validation
    check_response_body: bool = Field(
        False,
        description="Whether to check response body",
    )
    expected_response_contains: str | None = Field(
        None,
        description="Expected string in response",
    )
    expected_json_path: str | None = Field(
        None,
        description="JSON path to check (e.g., $.status)",
    )
    expected_json_value: Any | None = Field(
        None,
        description="Expected value at JSON path",
    )

    # Headers
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="Headers to send with health check",
    )

    # Retry behavior
    retry_on_failure: bool = Field(True, description="Retry on failure")
    max_retries: int = Field(2, description="Maximum retry attempts")
