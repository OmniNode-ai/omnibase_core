"""
ModelThrottlingBehavior - Throttling behavior configuration for rate limiting

Throttling behavior model for defining how to handle requests when rate limits
are exceeded, including blocking, queuing, delay, and custom responses.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.configuration.model_throttle_response import (
    ModelThrottleResponse,
)


class ModelThrottlingBehavior(BaseModel):
    """
    Throttling behavior configuration for rate limiting

    This model defines how to handle requests that exceed rate limits,
    including different strategies for blocking, delaying, queuing, and responding.
    """

    behavior_type: str = Field(
        default="reject",
        description="Primary throttling behavior",
        pattern="^(reject|delay|queue|degrade|custom)$",
    )

    reject_status_code: int = Field(
        default=429,
        description="HTTP status code for rejected requests",
        ge=200,
        le=599,
    )

    reject_message: str = Field(
        default="Rate limit exceeded. Please try again later.",
        description="Message to include with rejected requests",
    )

    include_retry_after_header: bool = Field(
        default=True,
        description="Whether to include Retry-After header in response",
    )

    retry_after_seconds: int | None = Field(
        default=None,
        description="Value for Retry-After header (auto-calculated if None)",
        ge=1,
        le=3600,
    )

    delay_type: str = Field(
        default="fixed",
        description="Type of delay to apply",
        pattern="^(fixed|exponential|jittered|adaptive)$",
    )

    base_delay_ms: int = Field(
        default=100,
        description="Base delay in milliseconds",
        ge=10,
        le=10000,
    )

    max_delay_ms: int = Field(
        default=5000,
        description="Maximum delay in milliseconds",
        ge=100,
        le=60000,
    )

    delay_multiplier: float = Field(
        default=2.0,
        description="Multiplier for exponential delay",
        ge=1.0,
        le=10.0,
    )

    jitter_factor: float = Field(
        default=0.1,
        description="Jitter factor for randomized delays (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    queue_enabled: bool = Field(
        default=False,
        description="Whether to queue requests when rate limited",
    )

    queue_max_size: int = Field(
        default=100,
        description="Maximum queue size for throttled requests",
        ge=1,
        le=10000,
    )

    queue_timeout_seconds: int = Field(
        default=30,
        description="Maximum time to keep requests in queue",
        ge=1,
        le=300,
    )

    queue_priority_method: str = Field(
        default="fifo",
        description="Queue priority method",
        pattern="^(fifo|lifo|priority|user_tier)$",
    )

    degradation_enabled: bool = Field(
        default=False,
        description="Whether to degrade service quality instead of blocking",
    )

    degradation_level: float = Field(
        default=0.5,
        description="Service degradation level (0.0-1.0, lower = more degraded)",
        ge=0.0,
        le=1.0,
    )

    degradation_features: dict[str, bool] = Field(
        default_factory=lambda: {
            "detailed_responses": False,
            "real_time_data": False,
            "premium_features": False,
            "high_quality_images": False,
        },
        description="Features to disable during degradation",
    )

    custom_response_enabled: bool = Field(
        default=False,
        description="Whether to use custom response for throttled requests",
    )

    custom_response_body: str | None = Field(
        default=None,
        description="Custom response body for throttled requests",
    )

    custom_response_headers: dict[str, str] = Field(
        default_factory=dict,
        description="Custom headers to include with throttled responses",
    )

    escalation_enabled: bool = Field(
        default=True,
        description="Whether to escalate behavior based on violation severity",
    )

    escalation_threshold: float = Field(
        default=2.0,
        description="Rate multiplier threshold for behavior escalation",
        ge=1.0,
        le=10.0,
    )

    escalated_behavior: str = Field(
        default="reject",
        description="Behavior when escalation threshold is exceeded",
        pattern="^(reject|block_ip|block_user|captcha|manual_review)$",
    )

    block_duration_seconds: int = Field(
        default=300,
        description="Duration to block users/IPs when escalated",
        ge=60,
        le=86400,
    )

    def calculate_delay(self, violation_count: int = 1, base_rate: float = 0.0) -> int:
        """Calculate delay in milliseconds based on throttling configuration"""
        if self.delay_type == "fixed":
            delay = self.base_delay_ms
        elif self.delay_type == "exponential":
            delay = int(
                min(
                    self.base_delay_ms
                    * (self.delay_multiplier ** (violation_count - 1)),
                    self.max_delay_ms,
                )
            )
        elif self.delay_type == "adaptive":
            # Adaptive delay based on current load
            load_multiplier = max(1.0, base_rate / 100.0) if base_rate > 0 else 1.0
            delay = min(int(self.base_delay_ms * load_multiplier), self.max_delay_ms)
        else:  # jittered
            import random

            jitter = random.uniform(-self.jitter_factor, self.jitter_factor)
            delay = int(self.base_delay_ms * (1.0 + jitter))
            delay = max(self.base_delay_ms // 2, min(delay, self.max_delay_ms))

        return max(self.base_delay_ms, delay)

    def should_escalate(self, current_rate: float, allowed_rate: float) -> bool:
        """Check if behavior should be escalated based on violation severity"""
        if not self.escalation_enabled or allowed_rate == 0:
            return False

        violation_ratio = current_rate / allowed_rate
        return violation_ratio >= self.escalation_threshold

    def get_retry_after_value(self, window_reset_seconds: int | None = None) -> int:
        """Get Retry-After header value in seconds"""
        if self.retry_after_seconds:
            return self.retry_after_seconds
        if window_reset_seconds:
            return window_reset_seconds
        # Default: suggest retry after a reasonable interval
        return 60

    def get_response_headers(self, retry_after: int | None = None) -> dict[str, str]:
        """Get response headers for throttled requests"""
        headers = {}

        # Add standard rate limit headers
        if self.include_retry_after_header and retry_after:
            headers["Retry-After"] = str(retry_after)

        headers["X-RateLimit-Status"] = "exceeded"
        headers["X-Throttle-Behavior"] = self.behavior_type

        # Add custom headers
        headers.update(self.custom_response_headers)

        return headers

    def is_request_queueable(self, queue_current_size: int) -> bool:
        """Check if request can be added to throttling queue"""
        return (
            self.queue_enabled
            and self.behavior_type in ["queue", "delay"]
            and queue_current_size < self.queue_max_size
        )

    def should_degrade_service(self) -> bool:
        """Check if service should be degraded instead of blocked"""
        return self.degradation_enabled and self.behavior_type == "degrade"

    def get_enabled_features(self) -> dict[str, bool]:
        """Get features that should remain enabled during degradation"""
        if not self.should_degrade_service():
            # All features enabled when not degrading
            return dict.fromkeys(self.degradation_features.keys(), True)

        # During degradation, return the configured feature states
        return self.degradation_features.copy()

    def get_throttle_response(
        self,
        retry_after: int | None = None,
    ) -> ModelThrottleResponse:
        """Get complete response for throttled requests"""
        return ModelThrottleResponse(
            status_code=self.reject_status_code,
            headers=self.get_response_headers(retry_after),
            message=self.reject_message,
            body=self.custom_response_body if self.custom_response_enabled else None,
        )

    @classmethod
    def create_strict_rejection(cls) -> "ModelThrottlingBehavior":
        """Create strict rejection throttling behavior"""
        return cls(
            behavior_type="reject",
            reject_status_code=429,
            reject_message="Rate limit exceeded. Access denied.",
            include_retry_after_header=True,
            escalation_enabled=True,
            escalated_behavior="block_user",
        )

    @classmethod
    def create_graceful_delay(cls) -> "ModelThrottlingBehavior":
        """Create graceful delay throttling behavior"""
        return cls(
            behavior_type="delay",
            delay_type="exponential",
            base_delay_ms=200,
            max_delay_ms=2000,
            delay_multiplier=1.5,
            jitter_factor=0.2,
            escalation_enabled=False,
        )

    @classmethod
    def create_queue_based(cls) -> "ModelThrottlingBehavior":
        """Create queue-based throttling behavior"""
        return cls(
            behavior_type="queue",
            queue_enabled=True,
            queue_max_size=200,
            queue_timeout_seconds=45,
            queue_priority_method="user_tier",
            reject_status_code=429,
            reject_message="Request queued due to high load. Please wait.",
        )

    @classmethod
    def create_service_degradation(cls) -> "ModelThrottlingBehavior":
        """Create service degradation throttling behavior"""
        return cls(
            behavior_type="degrade",
            degradation_enabled=True,
            degradation_level=0.6,
            degradation_features={
                "detailed_responses": False,
                "real_time_data": False,
                "premium_features": False,
                "high_quality_images": False,
                "advanced_analytics": False,
            },
            reject_status_code=200,  # Success but degraded service quality
            custom_response_headers={
                "X-Service-Level": "degraded",
                "X-Degradation-Reason": "rate_limited",
            },
        )

    @classmethod
    def create_adaptive_throttling(cls) -> "ModelThrottlingBehavior":
        """Create adaptive throttling behavior that adjusts based on load"""
        return cls(
            behavior_type="delay",
            delay_type="adaptive",
            base_delay_ms=100,
            max_delay_ms=3000,
            escalation_enabled=True,
            escalation_threshold=3.0,
            escalated_behavior="reject",
            queue_enabled=True,
            queue_max_size=50,
            degradation_enabled=True,
            degradation_level=0.7,
        )
