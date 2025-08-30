"""
ModelRateLimitPolicy - Comprehensive rate limiting policy configuration

Rate limiting policy model that combines window configuration, user limits,
throttling behavior, and burst handling for complete rate limiting management.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from .model_burst_config import ModelBurstConfig
from .model_per_user_limits import ModelPerUserLimits
from .model_rate_limit_window import ModelRateLimitWindow
from .model_retry_policy import ModelRetryPolicy
from .model_throttling_behavior import ModelThrottlingBehavior


class ModelRateLimitPolicy(BaseModel):
    """
    Comprehensive rate limiting policy configuration

    This model combines all aspects of rate limiting including time windows,
    user-specific limits, throttling behavior, and burst handling.
    """

    policy_name: str = Field(
        ..., description="Policy identifier", pattern="^[a-z][a-z0-9_-]*$"
    )

    description: str = Field(
        default="", description="Human-readable policy description"
    )

    enabled: bool = Field(
        default=True, description="Whether this rate limiting policy is enabled"
    )

    global_rate_limit: Optional[float] = Field(
        None,
        description="Global requests per second limit (overrides all other limits)",
        gt=0,
        le=100000,
    )

    window_config: ModelRateLimitWindow = Field(
        default_factory=ModelRateLimitWindow, description="Time window configuration"
    )

    per_user_limits: Optional[ModelPerUserLimits] = Field(
        None, description="Per-user rate limiting configuration"
    )

    throttling_behavior: ModelThrottlingBehavior = Field(
        default_factory=ModelThrottlingBehavior,
        description="Behavior when rate limits are exceeded",
    )

    burst_config: Optional[ModelBurstConfig] = Field(
        None, description="Burst handling configuration"
    )

    retry_policy: ModelRetryPolicy = Field(
        default_factory=ModelRetryPolicy,
        description="Retry policy for rate limited requests",
    )

    per_endpoint_limits: Dict[str, float] = Field(
        default_factory=dict,
        description="Per-endpoint rate limits (requests per second)",
    )

    per_method_limits: Dict[str, float] = Field(
        default_factory=dict,
        description="Per-HTTP-method rate limits (requests per second)",
    )

    ip_whitelist: List[str] = Field(
        default_factory=list,
        description="IP addresses/CIDR blocks exempt from rate limiting",
    )

    ip_blacklist: List[str] = Field(
        default_factory=list,
        description="IP addresses/CIDR blocks that are completely blocked",
    )

    geographic_limits: Dict[str, float] = Field(
        default_factory=dict,
        description="Rate limits by geographic region (country codes)",
    )

    priority_lanes: Dict[str, float] = Field(
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

    alert_thresholds: Dict[str, float] = Field(
        default_factory=lambda: {
            "high_rejection_rate": 0.1,  # 10% rejection rate
            "burst_frequency": 0.05,  # 5% of windows have bursts
            "queue_overflow": 0.8,  # 80% queue utilization
        },
        description="Thresholds for alerting on rate limiting metrics",
    )

    def get_effective_rate_limit(
        self,
        endpoint: str = "",
        method: str = "GET",
        user_id: str = "",
        user_tier: str = "",
        priority: str = "normal",
    ) -> float:
        """Get effective rate limit based on all applicable limits"""
        if not self.enabled:
            return float("inf")  # No limit when disabled

        limits = []

        # Global rate limit (highest priority)
        if self.global_rate_limit:
            limits.append(self.global_rate_limit)

        # Window-based limit
        window_limit = self.window_config.get_requests_per_second_limit()
        limits.append(window_limit)

        # Per-user limits
        if self.per_user_limits and user_id:
            user_limit = self.per_user_limits.get_user_limit(user_id, user_tier)
            if user_limit > 0:  # 0 means blocked user
                limits.append(user_limit / self.window_config.window_duration_seconds)

        # Per-endpoint limits
        if endpoint and endpoint in self.per_endpoint_limits:
            limits.append(self.per_endpoint_limits[endpoint])

        # Per-method limits
        if method and method in self.per_method_limits:
            limits.append(self.per_method_limits[method])

        # Priority-based limits
        if priority and priority in self.priority_lanes:
            limits.append(self.priority_lanes[priority])

        # Return the most restrictive limit
        return min(limits) if limits else float("inf")

    def is_ip_whitelisted(self, ip_address: str) -> bool:
        """Check if IP address is whitelisted"""
        # Simple implementation - in production would use CIDR matching
        return ip_address in self.ip_whitelist

    def is_ip_blacklisted(self, ip_address: str) -> bool:
        """Check if IP address is blacklisted"""
        # Simple implementation - in production would use CIDR matching
        return ip_address in self.ip_blacklist

    def get_geographic_limit(self, country_code: str) -> Optional[float]:
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

        # Time until window resets
        retry_after = max(1, int(window_end - current_time))
        return min(retry_after, 3600)  # Cap at 1 hour

    def get_monitoring_metrics(self) -> Dict[str, bool]:
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

    def validate_policy_consistency(self) -> List[str]:
        """Validate policy configuration for consistency and conflicts"""
        issues = []

        # Check if global limit conflicts with other limits
        if self.global_rate_limit:
            window_limit = self.window_config.get_requests_per_second_limit()
            if self.global_rate_limit < window_limit:
                issues.append("Global rate limit is lower than window-based limit")

        # Check if throttling behavior is compatible with queue settings
        if (
            self.throttling_behavior.queue_enabled
            and self.throttling_behavior.behavior_type not in ["queue", "delay"]
        ):
            issues.append("Queue enabled but behavior type doesn't support queuing")

        # Check burst configuration compatibility
        if (
            self.burst_config
            and self.burst_config.burst_detection_enabled
            and self.window_config.window_type == "fixed"
        ):
            issues.append("Burst detection may not work optimally with fixed windows")

        # Check distributed settings
        if self.distributed_enabled and self.cache_backend == "memory":
            issues.append("Distributed rate limiting requires shared cache backend")

        return issues

    @classmethod
    def create_api_rate_limiting(cls) -> "ModelRateLimitPolicy":
        """Create standard API rate limiting policy"""
        return cls(
            policy_name="standard_api",
            description="Standard API rate limiting with user tiers",
            window_config=ModelRateLimitWindow.create_sliding_window(60, 1000),
            per_user_limits=ModelPerUserLimits.create_api_key_limits(),
            throttling_behavior=ModelThrottlingBehavior.create_graceful_delay(),
            burst_config=ModelBurstConfig.create_conservative_burst(),
            per_endpoint_limits={
                "/api/v1/search": 100.0,
                "/api/v1/upload": 10.0,
                "/api/v1/analytics": 50.0,
            },
            monitoring_enabled=True,
        )

    @classmethod
    def create_web_application_policy(cls) -> "ModelRateLimitPolicy":
        """Create web application rate limiting policy"""
        return cls(
            policy_name="web_application",
            description="Web application rate limiting with IP-based limits",
            window_config=ModelRateLimitWindow.create_sliding_window(60, 500),
            per_user_limits=ModelPerUserLimits.create_ip_based_limits(),
            throttling_behavior=ModelThrottlingBehavior.create_service_degradation(),
            burst_config=ModelBurstConfig.create_aggressive_burst(),
            per_method_limits={"POST": 50.0, "PUT": 30.0, "DELETE": 20.0, "GET": 200.0},
        )

    @classmethod
    def create_enterprise_policy(cls) -> "ModelRateLimitPolicy":
        """Create enterprise-grade rate limiting policy"""
        return cls(
            policy_name="enterprise",
            description="Enterprise rate limiting with advanced features",
            window_config=ModelRateLimitWindow.create_token_bucket(10000, 100.0),
            per_user_limits=ModelPerUserLimits.create_enterprise_user_limits(),
            throttling_behavior=ModelThrottlingBehavior.create_adaptive_throttling(),
            burst_config=ModelBurstConfig.create_predictive_burst(),
            distributed_enabled=True,
            cache_backend="redis",
            geographic_limits={"US": 5000.0, "EU": 3000.0, "APAC": 2000.0},
            monitoring_enabled=True,
        )

    @classmethod
    def create_strict_security_policy(cls) -> "ModelRateLimitPolicy":
        """Create strict security-focused rate limiting policy"""
        return cls(
            policy_name="security_strict",
            description="Strict rate limiting for high-security environments",
            window_config=ModelRateLimitWindow.create_fixed_window(60, 100),
            per_user_limits=ModelPerUserLimits.create_basic_user_limits(),
            throttling_behavior=ModelThrottlingBehavior.create_strict_rejection(),
            burst_config=ModelBurstConfig.create_disabled_burst(),
            priority_lanes={
                "critical": 200.0,
                "high": 100.0,
                "normal": 50.0,
                "low": 20.0,
            },
            alert_thresholds={
                "high_rejection_rate": 0.05,  # 5% rejection rate
                "burst_frequency": 0.01,  # 1% burst frequency
                "queue_overflow": 0.5,  # 50% queue utilization
            },
        )
