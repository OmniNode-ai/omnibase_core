"""
ModelRateLimitWindow - Rate limit time window configuration

Rate limit window model for defining time-based rate limiting windows
with sliding window, fixed window, and token bucket implementations.
"""

from pydantic import BaseModel, Field


class ModelRateLimitWindow(BaseModel):
    """
    Rate limit time window configuration

    This model defines how rate limiting windows behave, including
    window types, duration, and reset behavior for rate limiting systems.
    """

    window_type: str = Field(
        default="sliding",
        description="Type of rate limiting window",
        pattern="^(fixed|sliding|token_bucket|leaky_bucket)$",
    )

    window_duration_seconds: int = Field(
        default=60,
        description="Window duration in seconds",
        ge=1,
        le=86400,  # 24 hours max
    )

    window_size: int = Field(
        default=100,
        description="Maximum requests allowed in window",
        ge=1,
        le=1000000,
    )

    sub_window_count: int | None = Field(
        default=None,
        description="Number of sub-windows for sliding window (granularity)",
        ge=1,
        le=3600,
    )

    reset_on_window_boundary: bool = Field(
        default=True,
        description="Whether to reset counters on window boundaries",
    )

    allow_burst_above_limit: bool = Field(
        default=False,
        description="Whether to allow bursts above the limit",
    )

    burst_multiplier: float = Field(
        default=1.5,
        description="Multiplier for burst capacity above normal limit",
        ge=1.0,
        le=10.0,
    )

    token_refill_rate: float | None = Field(
        default=None,
        description="Token refill rate per second (for token bucket)",
        ge=0.1,
        le=10000.0,
    )

    bucket_capacity: int | None = Field(
        default=None,
        description="Bucket capacity (for token/leaky bucket)",
        ge=1,
        le=1000000,
    )

    leak_rate: float | None = Field(
        default=None,
        description="Leak rate per second (for leaky bucket)",
        ge=0.1,
        le=10000.0,
    )

    precision_seconds: int = Field(
        default=1,
        description="Precision for time-based calculations in seconds",
        ge=1,
        le=3600,
    )

    def get_effective_window_size(self) -> int:
        """Get effective window size including burst capacity"""
        if self.allow_burst_above_limit:
            return int(self.window_size * self.burst_multiplier)
        return self.window_size

    def get_sub_window_duration(self) -> float:
        """Get duration of each sub-window in seconds"""
        if self.sub_window_count and self.sub_window_count > 0:
            return self.window_duration_seconds / self.sub_window_count
        return self.window_duration_seconds

    def get_requests_per_second_limit(self) -> float:
        """Calculate requests per second limit"""
        return self.window_size / self.window_duration_seconds

    def get_burst_requests_per_second(self) -> float:
        """Calculate burst requests per second limit"""
        return self.get_effective_window_size() / self.window_duration_seconds

    def calculate_window_start(self, current_timestamp: float) -> float:
        """Calculate window start time for fixed windows"""
        if self.window_type == "fixed":
            # Align to window boundaries
            return (
                current_timestamp // self.window_duration_seconds
            ) * self.window_duration_seconds
        return current_timestamp - self.window_duration_seconds

    def is_within_current_window(self, timestamp: float, window_start: float) -> bool:
        """Check if timestamp is within the current window"""
        window_end = window_start + self.window_duration_seconds
        return window_start <= timestamp < window_end

    def should_reset_window(self, current_timestamp: float, last_reset: float) -> bool:
        """Check if window should be reset"""
        if not self.reset_on_window_boundary:
            return False

        if self.window_type == "fixed":
            current_window_start = self.calculate_window_start(current_timestamp)
            last_window_start = self.calculate_window_start(last_reset)
            return current_window_start > last_window_start

        return False

    def get_tokens_to_add(self, time_elapsed_seconds: float) -> float:
        """Calculate tokens to add for token bucket (if applicable)"""
        if self.window_type != "token_bucket" or not self.token_refill_rate:
            return 0.0

        return self.token_refill_rate * time_elapsed_seconds

    def get_requests_to_leak(self, time_elapsed_seconds: float) -> float:
        """Calculate requests to leak for leaky bucket (if applicable)"""
        if self.window_type != "leaky_bucket" or not self.leak_rate:
            return 0.0

        return self.leak_rate * time_elapsed_seconds

    @classmethod
    def create_fixed_window(
        cls,
        duration_seconds: int = 60,
        window_size: int = 100,
    ) -> "ModelRateLimitWindow":
        """Create fixed window rate limiting configuration"""
        return cls(
            window_type="fixed",
            window_duration_seconds=duration_seconds,
            window_size=window_size,
            reset_on_window_boundary=True,
        )

    @classmethod
    def create_sliding_window(
        cls,
        duration_seconds: int = 60,
        window_size: int = 100,
        sub_windows: int = 12,
    ) -> "ModelRateLimitWindow":
        """Create sliding window rate limiting configuration"""
        return cls(
            window_type="sliding",
            window_duration_seconds=duration_seconds,
            window_size=window_size,
            sub_window_count=sub_windows,
            precision_seconds=duration_seconds // sub_windows,
        )

    @classmethod
    def create_token_bucket(
        cls,
        bucket_capacity: int = 100,
        refill_rate: float = 10.0,
    ) -> "ModelRateLimitWindow":
        """Create token bucket rate limiting configuration"""
        return cls(
            window_type="token_bucket",
            window_size=bucket_capacity,
            bucket_capacity=bucket_capacity,
            token_refill_rate=refill_rate,
            allow_burst_above_limit=True,
            burst_multiplier=1.0,  # Burst is inherent in token bucket
        )

    @classmethod
    def create_leaky_bucket(
        cls,
        bucket_capacity: int = 100,
        leak_rate: float = 5.0,
    ) -> "ModelRateLimitWindow":
        """Create leaky bucket rate limiting configuration"""
        return cls(
            window_type="leaky_bucket",
            window_size=bucket_capacity,
            bucket_capacity=bucket_capacity,
            leak_rate=leak_rate,
            allow_burst_above_limit=False,
        )

    @classmethod
    def create_burst_friendly(
        cls,
        base_limit: int = 100,
        burst_multiplier: float = 2.0,
    ) -> "ModelRateLimitWindow":
        """Create burst-friendly rate limiting configuration"""
        return cls(
            window_type="sliding",
            window_duration_seconds=60,
            window_size=base_limit,
            sub_window_count=6,  # 10-second sub-windows
            allow_burst_above_limit=True,
            burst_multiplier=burst_multiplier,
        )
