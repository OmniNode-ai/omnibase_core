from uuid import UUID

from pydantic import ConfigDict, Field

"\nModelRateLimitPolicy - Comprehensive rate limiting policy configuration\n\nRate limiting policy model that combines window configuration, user limits,\nthrottling behavior, and burst handling for complete rate limiting management.\n"
from pydantic import BaseModel

from omnibase_core.models.infrastructure.model_retry_policy import ModelRetryPolicy

from .model_burst_config import ModelBurstConfig
from .model_per_user_limits import ModelPerUserLimits
from .model_rate_limit_window import ModelRateLimitWindow
from .model_throttling_behavior import ModelThrottlingBehavior


class ModelRateLimitPolicy(BaseModel):
    """
    Comprehensive rate limiting policy configuration

    This model combines all aspects of rate limiting including time windows,
    user-specific limits, throttling behavior, and burst handling.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    policy_name: str = Field(
        default=..., description="Policy identifier", pattern="^[a-z][a-z0-9_-]*$"
    )
    description: str = Field(
        default="", description="Human-readable policy description"
    )
    enabled: bool = Field(
        default=True, description="Whether this rate limiting policy is enabled"
    )
    global_rate_limit: float | None = Field(
        default=None,
        description="Global requests per second limit (overrides all other limits)",
        gt=0,
        le=100000,
    )
    window_config: ModelRateLimitWindow = Field(
        default_factory=lambda: ModelRateLimitWindow(),
        description="Time window configuration",
    )
    per_user_limits: ModelPerUserLimits | None = Field(
        default=None, description="Per-user rate limiting configuration"
    )
    throttling_behavior: ModelThrottlingBehavior = Field(
        default_factory=lambda: ModelThrottlingBehavior(),
        description="Behavior when rate limits are exceeded",
    )
    burst_config: ModelBurstConfig | None = Field(
        default=None, description="Burst handling configuration"
    )
    retry_policy: ModelRetryPolicy = Field(
        default_factory=lambda: ModelRetryPolicy(),
        description="Retry policy for rate limited requests",
    )
    per_endpoint_limits: dict[str, float] = Field(
        default_factory=dict,
        description="Per-endpoint rate limits (requests per second)",
    )
    per_method_limits: dict[str, float] = Field(
        default_factory=dict,
        description="Per-HTTP-method rate limits (requests per second)",
    )
    ip_whitelist: list[str] = Field(
        default_factory=list,
        description="IP addresses/CIDR blocks exempt from rate limiting",
    )
    ip_blacklist: list[str] = Field(
        default_factory=list,
        description="IP addresses/CIDR blocks that are completely blocked",
    )
    geographic_limits: dict[str, float] = Field(
        default_factory=dict,
        description="Rate limits by geographic region (country codes)",
    )
    priority_lanes: dict[str, float] = Field(
        default_factory=lambda: {
            "critical": 1000.0,
            "high": 500.0,
            "normal": 100.0,
            "low": 50.0,
        },
        description="Priority-based rate limits",
    )
    distributed_enabled: bool = Field(
        default=False,
        description="Whether rate limiting is distributed across multiple instances",
    )
    distributed_sync_interval_ms: int = Field(
        default=1000,
        description="Interval for syncing distributed rate limiting state",
        ge=100,
        le=10000,
    )
    cache_backend: str = Field(
        default="memory",
        description="Backend for storing rate limit state",
        pattern="^(memory|redis|database|memcached)$",
    )
    cache_key_prefix: str = Field(
        default="rate_limit", description="Prefix for cache keys"
    )
    monitoring_enabled: bool = Field(
        default=True,
        description="Whether to enable rate limiting monitoring and metrics",
    )
    alert_thresholds: dict[str, float] = Field(
        default_factory=lambda: {
            "high_rejection_rate": 0.1,
            "burst_frequency": 0.05,
            "queue_overflow": 0.8,
        },
        description="Thresholds for alerting on rate limiting metrics",
    )

    def get_effective_rate_limit(
        self,
        endpoint: str = "",
        method: str = "GET",
        user_id: UUID | None = None,
        user_tier: str = "",
        priority: str = "normal",
    ) -> float:
        """Get effective rate limit based on all applicable limits"""
        if not self.enabled:
            return float("inf")
        limits = []
        if self.global_rate_limit:
            limits.append(self.global_rate_limit)
        window_limit = self.window_config.get_requests_per_second_limit()
        limits.append(window_limit)
        if self.per_user_limits and user_id:
            user_limit = self.per_user_limits.get_user_limit(user_id, user_tier)
            if user_limit > 0:
                limits.append(user_limit / self.window_config.window_duration_seconds)
        if endpoint and endpoint in self.per_endpoint_limits:
            limits.append(self.per_endpoint_limits[endpoint])
        if method and method in self.per_method_limits:
            limits.append(self.per_method_limits[method])
        if priority and priority in self.priority_lanes:
            limits.append(self.priority_lanes[priority])
        return min(limits) if limits else float("inf")

    def is_ip_whitelisted(self, ip_address: str) -> bool:
        """Check if IP address is whitelisted"""
        return ip_address in self.ip_whitelist

    def is_ip_blacklisted(self, ip_address: str) -> bool:
        """Check if IP address is blacklisted"""
        return ip_address in self.ip_blacklist

    def get_geographic_limit(self, country_code: str) -> float | None:
        """Get rate limit for specific geographic region"""
        return self.geographic_limits.get(country_code)

    def should_apply_burst_handling(
        self, current_rate: float, base_limit: float
    ) -> bool:
        """Check if burst handling should be applied"""
        if not self.burst_config or not self.burst_config.burst_detection_enabled:
            return False
        return self.burst_config.is_burst_triggered(current_rate, int(base_limit))

    def get_cache_key(self, identifier: str, scope: str = "global") -> str:
        """Generate cache key for rate limiting state"""
        return f"{self.cache_key_prefix}:{self.policy_name}:{scope}:{identifier}"

    def calculate_retry_after(self, current_time: float) -> int:
        """Calculate retry-after value based on window configuration"""
        window_start = self.window_config.calculate_window_start(current_time)
        window_end = window_start + self.window_config.window_duration_seconds
        retry_after = max(1, int(window_end - current_time))
        return min(retry_after, 3600)

    def get_monitoring_metrics(self) -> dict[str, bool]:
        """Get metrics that should be monitored for this policy"""
        return {
            "requests_per_second": True,
            "rejection_rate": True,
            "queue_utilization": self.throttling_behavior.queue_enabled,
            "burst_frequency": self.burst_config is not None,
            "user_violations": self.per_user_limits is not None,
            "geographic_distribution": len(self.geographic_limits) > 0,
            "cache_hit_rate": True,
            "distributed_sync_latency": self.distributed_enabled,
        }

    def validate_policy_consistency(self) -> list[str]:
        """Validate policy configuration for consistency and conflicts"""
        issues = []
        if self.global_rate_limit:
            window_limit = self.window_config.get_requests_per_second_limit()
            if self.global_rate_limit < window_limit:
                issues.append("Global rate limit is lower than window-based limit")
        if (
            self.throttling_behavior.queue_enabled
            and self.throttling_behavior.behavior_type not in ["queue", "delay"]
        ):
            issues.append("Queue enabled but behavior type doesn't support queuing")
        if (
            self.burst_config
            and self.burst_config.burst_detection_enabled
            and (self.window_config.window_type == "fixed")
        ):
            issues.append("Burst detection may not work optimally with fixed windows")
        if self.distributed_enabled and self.cache_backend == "memory":
            issues.append("Distributed rate limiting requires shared cache backend")
        return issues
