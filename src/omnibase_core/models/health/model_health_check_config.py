"""
ModelHealthCheckConfig - Health check configuration for load balancing

Health check configuration model for monitoring node health in a load
balancing system with configurable intervals, timeouts, and failure handling.
"""

from pydantic import BaseModel, Field

from .model_health_check_metadata import ModelHealthCheckMetadata


class ModelHealthCheckConfig(BaseModel):
    """
    Health check configuration for load balancing

    This model defines how health checks should be performed on nodes
    to determine their availability for load balancing decisions.
    """

    enabled: bool = Field(default=True, description="Whether health checks are enabled")

    check_interval_seconds: int = Field(
        default=30,
        description="Interval between health checks in seconds",
        ge=5,
        le=3600,
    )

    timeout_seconds: int = Field(
        default=5,
        description="Health check timeout in seconds",
        ge=1,
        le=60,
    )

    healthy_threshold: int = Field(
        default=3,
        description="Number of consecutive successful checks to mark node healthy",
        ge=1,
        le=10,
    )

    unhealthy_threshold: int = Field(
        default=2,
        description="Number of consecutive failed checks to mark node unhealthy",
        ge=1,
        le=10,
    )

    check_path: str = Field(
        default="/health",
        description="HTTP path for health checks",
    )

    check_method: str = Field(
        default="GET",
        description="HTTP method for health checks",
        pattern="^(GET|POST|HEAD|OPTIONS)$",
    )

    expected_status_codes: list[int] = Field(
        default_factory=lambda: [200],
        description="HTTP status codes considered healthy",
    )

    expected_response_body: str | None = Field(
        default=None,
        description="Expected response body content (substring match)",
    )

    check_headers: dict[str, str] = Field(
        default_factory=dict,
        description="HTTP headers to send with health checks",
    )

    check_body: str | None = Field(
        default=None,
        description="HTTP body to send with health checks (for POST)",
    )

    follow_redirects: bool = Field(
        default=False,
        description="Whether to follow HTTP redirects",
    )

    validate_ssl: bool = Field(
        default=True,
        description="Whether to validate SSL certificates",
    )

    custom_validator: str | None = Field(
        default=None,
        description="Custom health check validator function name",
    )

    health_check_metadata: ModelHealthCheckMetadata | None = Field(
        default=None,
        description="Additional health check metadata",
    )

    def is_response_healthy(self, status_code: int, response_body: str = "") -> bool:
        """Check if a health check response indicates health"""
        if not self.enabled:
            return True  # If health checks disabled, assume healthy

        # Check status code
        if status_code not in self.expected_status_codes:
            return False

        # Check response body if specified
        if self.expected_response_body:
            if self.expected_response_body not in response_body:
                return False

        return True

    def get_check_url(self, base_url: str) -> str:
        """Construct full health check URL"""
        base_url = base_url.rstrip("/")
        check_path = self.check_path.lstrip("/")
        return f"{base_url}/{check_path}"

    def get_check_headers_with_defaults(self) -> dict[str, str]:
        """Get health check headers with defaults"""
        headers = {
            "User-Agent": "ONEX-LoadBalancer/1.0",
            "Accept": "application/json,text/plain,*/*",
        }
        headers.update(self.check_headers)
        return headers

    def should_check_now(
        self,
        last_check_timestamp: float,
        current_timestamp: float,
    ) -> bool:
        """Check if a health check should be performed now"""
        if not self.enabled:
            return False

        return (current_timestamp - last_check_timestamp) >= self.check_interval_seconds

    def calculate_health_status(
        self,
        consecutive_successes: int,
        consecutive_failures: int,
    ) -> str:
        """Calculate health status based on consecutive results"""
        if consecutive_failures >= self.unhealthy_threshold:
            return "unhealthy"
        if consecutive_successes >= self.healthy_threshold:
            return "healthy"
        return "degraded"  # In transition state

    def get_effective_timeout(self) -> float:
        """Get effective timeout considering check interval"""
        # Timeout should not exceed half the check interval
        max_timeout = max(1, self.check_interval_seconds // 2)
        return min(self.timeout_seconds, max_timeout)

    @classmethod
    def create_fast_checks(cls) -> "ModelHealthCheckConfig":
        """Create configuration for fast health checks"""
        return cls(
            enabled=True,
            check_interval_seconds=10,
            timeout_seconds=2,
            healthy_threshold=2,
            unhealthy_threshold=2,
            check_path="/health",
            check_method="HEAD",  # Faster than GET
        )

    @classmethod
    def create_thorough_checks(cls) -> "ModelHealthCheckConfig":
        """Create configuration for thorough health checks"""
        return cls(
            enabled=True,
            check_interval_seconds=60,
            timeout_seconds=10,
            healthy_threshold=3,
            unhealthy_threshold=3,
            check_path="/health/detailed",
            check_method="GET",
            expected_response_body="healthy",
        )

    @classmethod
    def create_production_checks(cls) -> "ModelHealthCheckConfig":
        """Create configuration for production health checks"""
        return cls(
            enabled=True,
            check_interval_seconds=30,
            timeout_seconds=5,
            healthy_threshold=3,
            unhealthy_threshold=2,
            check_path="/health",
            check_method="GET",
            expected_status_codes=[200],
            validate_ssl=True,
            check_headers={
                "X-Health-Check": "load-balancer",
                "X-Environment": "production",
            },
        )

    @classmethod
    def create_development_checks(cls) -> "ModelHealthCheckConfig":
        """Create configuration for development health checks"""
        return cls(
            enabled=True,
            check_interval_seconds=60,
            timeout_seconds=10,
            healthy_threshold=2,
            unhealthy_threshold=3,
            check_path="/health",
            check_method="GET",
            validate_ssl=False,  # More lenient for dev
            check_headers={
                "X-Health-Check": "load-balancer",
                "X-Environment": "development",
            },
        )

    @classmethod
    def create_disabled(cls) -> "ModelHealthCheckConfig":
        """Create configuration with health checks disabled"""
        return cls(enabled=False)


# Rebuild ModelHealthCheckConfig to pick up the resolved forward references
# from ModelHealthCheckMetadata (which has a forward reference to ModelCustomFields).
# This ensures the model is fully usable regardless of import path.
def _resolve_forward_references() -> None:
    """Resolve forward references for ModelHealthCheckConfig."""
    try:
        # The import of model_health_check_metadata already triggers its own
        # model_rebuild(), so we just need to rebuild this class to pick up
        # the resolved types from ModelHealthCheckMetadata
        ModelHealthCheckConfig.model_rebuild()
    except Exception:
        # init-errors-ok: model_rebuild may fail during circular import resolution
        pass


_resolve_forward_references()
