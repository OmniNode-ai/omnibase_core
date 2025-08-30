"""
ONEX-compliant model for rate limiting configuration and status.

Defines rate limiting policies, algorithms, and status tracking
for distributed system resource protection.
"""

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class EnumRateLimitAlgorithm(str, Enum):
    """Rate limiting algorithm enumeration."""

    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"
    LEAKY_BUCKET = "leaky_bucket"


class EnumRateLimitScope(str, Enum):
    """Rate limiting scope enumeration."""

    USER = "user"
    IP_ADDRESS = "ip_address"
    ENDPOINT = "endpoint"
    API_KEY = "api_key"
    GLOBAL = "global"
    SERVICE = "service"
    TENANT = "tenant"


class EnumRateLimitAction(str, Enum):
    """Action to take when rate limit is exceeded."""

    BLOCK = "block"
    THROTTLE = "throttle"
    LOG_ONLY = "log_only"
    QUEUE = "queue"


class ModelRateLimitConfig(BaseModel):
    """
    Rate limit configuration model.

    Defines rate limiting policy for a specific scope and identifier
    with configurable algorithms and parameters.
    """

    config_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique configuration identifier",
    )
    scope: EnumRateLimitScope = Field(..., description="Rate limiting scope")
    identifier: str = Field(..., description="Unique identifier within scope")

    # Rate limiting parameters
    algorithm: EnumRateLimitAlgorithm = Field(
        EnumRateLimitAlgorithm.TOKEN_BUCKET,
        description="Rate limiting algorithm to use",
    )
    requests_per_window: int = Field(
        ...,
        description="Maximum requests allowed per window",
    )
    window_size_seconds: int = Field(..., description="Time window size in seconds")

    # Burst and grace configurations
    burst_size: int | None = Field(
        None,
        description="Maximum burst size for token bucket",
    )
    grace_period_seconds: int = Field(
        0,
        description="Grace period before rate limiting starts",
    )

    # Action configuration
    action: EnumRateLimitAction = Field(
        EnumRateLimitAction.BLOCK,
        description="Action to take when rate limit exceeded",
    )

    # Metadata
    name: str = Field(..., description="Human-readable name for this rate limit")
    description: str | None = Field(
        None,
        description="Description of rate limiting purpose",
    )
    enabled: bool = Field(True, description="Whether rate limiting is enabled")

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Configuration creation time",
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Last update time",
    )
    expires_at: datetime | None = Field(
        None,
        description="When configuration expires",
    )

    # Tags and metadata
    tags: dict = Field(default_factory=dict, description="Rate limit metadata tags")
    priority: int = Field(5, description="Configuration priority (1-10, 1=highest)")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "config_id": "550e8400-e29b-41d4-a716-446655440000",
                "scope": "user",
                "identifier": "user_123",
                "algorithm": "token_bucket",
                "requests_per_window": 100,
                "window_size_seconds": 3600,
                "burst_size": 150,
                "grace_period_seconds": 60,
                "action": "block",
                "name": "User API Rate Limit",
                "description": "Rate limit for user API access",
                "enabled": True,
                "created_at": "2025-07-30T12:00:00Z",
                "updated_at": "2025-07-30T12:00:00Z",
                "tags": {"environment": "production", "service": "api_gateway"},
                "priority": 3,
            },
        }


class ModelRateLimitStatus(BaseModel):
    """
    Rate limit status model.

    Represents the current rate limiting status for a specific
    scope and identifier including timing and quota information.
    """

    # Rate limit decision
    allowed: bool = Field(..., description="Whether the request is allowed")
    scope: EnumRateLimitScope = Field(..., description="Rate limiting scope")
    identifier: str = Field(..., description="Unique identifier within scope")

    # Quota information
    requests_remaining: int = Field(
        ...,
        description="Number of requests remaining in window",
    )
    requests_used: int = Field(
        0,
        description="Number of requests used in current window",
    )
    limit: int = Field(0, description="Total request limit for window")

    # Timing information
    reset_time: datetime = Field(..., description="When the rate limit window resets")
    retry_after_seconds: float | None = Field(
        None,
        description="Seconds to wait before retry",
    )
    window_start: datetime | None = Field(
        None,
        description="Current window start time",
    )

    # Rate limit configuration reference
    config_id: str | None = Field(
        None,
        description="Configuration ID that generated this status",
    )
    algorithm: EnumRateLimitAlgorithm | None = Field(
        None,
        description="Algorithm used",
    )

    # Additional context
    violation_count: int = Field(0, description="Number of recent violations")
    burst_used: int = Field(0, description="Burst capacity used (for token bucket)")

    # Timestamps
    checked_at: datetime = Field(
        default_factory=datetime.now,
        description="When rate limit was checked",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "allowed": True,
                "scope": "user",
                "identifier": "user_123",
                "requests_remaining": 85,
                "requests_used": 15,
                "limit": 100,
                "reset_time": "2025-07-30T13:00:00Z",
                "retry_after_seconds": None,
                "window_start": "2025-07-30T12:00:00Z",
                "config_id": "550e8400-e29b-41d4-a716-446655440000",
                "algorithm": "token_bucket",
                "violation_count": 0,
                "burst_used": 0,
                "checked_at": "2025-07-30T12:30:00Z",
            },
        }


class ModelRateLimitViolation(BaseModel):
    """
    Rate limit violation tracking model.

    Records rate limit violations for monitoring, alerting,
    and security analysis purposes.
    """

    violation_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique violation identifier",
    )
    scope: EnumRateLimitScope = Field(..., description="Rate limiting scope")
    identifier: str = Field(..., description="Unique identifier within scope")

    # Violation details
    attempted_requests: int = Field(..., description="Number of requests attempted")
    allowed_requests: int = Field(
        ...,
        description="Number of requests that were allowed",
    )
    blocked_requests: int = Field(
        ...,
        description="Number of requests that were blocked",
    )

    # Configuration context
    config_id: str = Field(..., description="Rate limit configuration ID")
    algorithm: EnumRateLimitAlgorithm = Field(
        ...,
        description="Algorithm that detected violation",
    )
    limit: int = Field(..., description="Rate limit that was exceeded")
    window_size_seconds: int = Field(
        ...,
        description="Window size for the violated limit",
    )

    # Timing
    violation_time: datetime = Field(
        default_factory=datetime.now,
        description="When violation occurred",
    )
    window_start: datetime = Field(
        ...,
        description="Start of the window when violation occurred",
    )
    window_end: datetime = Field(
        ...,
        description="End of the window when violation occurred",
    )

    # Additional context
    source_ip: str | None = Field(None, description="Source IP address if available")
    user_agent: str | None = Field(None, description="User agent if available")
    endpoint: str | None = Field(None, description="API endpoint if applicable")

    # Severity and impact
    severity: str = Field(
        "medium",
        description="Violation severity (low, medium, high, critical)",
    )
    impact_score: float = Field(0.0, description="Calculated impact score (0.0-10.0)")

    # Metadata
    tags: dict = Field(
        default_factory=dict,
        description="Additional violation metadata",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "violation_id": "550e8400-e29b-41d4-a716-446655440001",
                "scope": "user",
                "identifier": "user_123",
                "attempted_requests": 120,
                "allowed_requests": 100,
                "blocked_requests": 20,
                "config_id": "550e8400-e29b-41d4-a716-446655440000",
                "algorithm": "token_bucket",
                "limit": 100,
                "window_size_seconds": 3600,
                "violation_time": "2025-07-30T12:30:00Z",
                "window_start": "2025-07-30T12:00:00Z",
                "window_end": "2025-07-30T13:00:00Z",
                "source_ip": "192.168.1.100",
                "user_agent": "MyApp/1.0",
                "endpoint": "/api/v1/data",
                "severity": "medium",
                "impact_score": 4.5,
                "tags": {"environment": "production", "alert_sent": "true"},
            },
        }


class ModelRateLimitMetrics(BaseModel):
    """
    Rate limiting metrics model.

    Aggregated metrics for monitoring rate limiting effectiveness
    and system performance.
    """

    # Request statistics
    total_requests: int = Field(0, description="Total requests processed")
    allowed_requests: int = Field(0, description="Number of requests allowed")
    blocked_requests: int = Field(0, description="Number of requests blocked")
    throttled_requests: int = Field(0, description="Number of requests throttled")

    # Violation statistics
    total_violations: int = Field(0, description="Total violations detected")
    unique_violators: int = Field(
        0,
        description="Number of unique violating identifiers",
    )

    # Performance metrics
    average_check_time_ms: float = Field(
        0.0,
        description="Average rate limit check time in milliseconds",
    )
    p95_check_time_ms: float = Field(
        0.0,
        description="95th percentile check time in milliseconds",
    )
    p99_check_time_ms: float = Field(
        0.0,
        description="99th percentile check time in milliseconds",
    )

    # Resource usage
    active_configurations: int = Field(
        0,
        description="Number of active rate limit configurations",
    )
    memory_usage_bytes: int = Field(0, description="Estimated memory usage in bytes")

    # Time window
    metrics_start_time: datetime = Field(
        default_factory=datetime.now,
        description="Start of metrics collection window",
    )
    metrics_end_time: datetime = Field(
        default_factory=datetime.now,
        description="End of metrics collection window",
    )
    collection_duration_seconds: float = Field(
        0.0,
        description="Duration of metrics collection in seconds",
    )

    # Algorithm breakdown
    token_bucket_requests: int = Field(
        0,
        description="Requests processed by token bucket algorithm",
    )
    sliding_window_requests: int = Field(
        0,
        description="Requests processed by sliding window algorithm",
    )
    fixed_window_requests: int = Field(
        0,
        description="Requests processed by fixed window algorithm",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "total_requests": 10000,
                "allowed_requests": 9500,
                "blocked_requests": 450,
                "throttled_requests": 50,
                "total_violations": 25,
                "unique_violators": 8,
                "average_check_time_ms": 2.5,
                "p95_check_time_ms": 8.0,
                "p99_check_time_ms": 15.0,
                "active_configurations": 12,
                "memory_usage_bytes": 1048576,
                "metrics_start_time": "2025-07-30T12:00:00Z",
                "metrics_end_time": "2025-07-30T13:00:00Z",
                "collection_duration_seconds": 3600.0,
                "token_bucket_requests": 7500,
                "sliding_window_requests": 2000,
                "fixed_window_requests": 500,
            },
        }
