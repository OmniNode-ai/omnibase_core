"""
ModelBurstConfig - Burst handling configuration for rate limiting

Burst configuration model for managing traffic spikes and burst scenarios
in rate limiting systems with intelligent burst detection and handling.
"""

from pydantic import BaseModel, Field


class ModelBurstConfig(BaseModel):
    """
    Burst handling configuration for rate limiting

    This model defines how traffic bursts should be detected and handled
    within rate limiting systems, including burst capacity, detection, and recovery.
    """

    burst_detection_enabled: bool = Field(
        default=True,
        description="Whether burst detection is enabled",
    )

    burst_capacity_multiplier: float = Field(
        default=2.0,
        description="Multiplier for additional capacity during bursts",
        ge=1.0,
        le=10.0,
    )

    burst_duration_seconds: int = Field(
        default=30,
        description="Maximum duration to allow burst traffic",
        ge=1,
        le=300,
    )

    burst_threshold_multiplier: float = Field(
        default=1.5,
        description="Multiplier of normal rate to trigger burst detection",
        ge=1.0,
        le=5.0,
    )

    burst_cooldown_seconds: int = Field(
        default=60,
        description="Cooldown period after burst before allowing another",
        ge=10,
        le=3600,
    )

    burst_grace_period_seconds: int = Field(
        default=5,
        description="Grace period at start of burst before strict enforcement",
        ge=1,
        le=60,
    )

    max_burst_capacity: int | None = Field(
        default=None,
        description="Absolute maximum burst capacity regardless of multiplier",
        ge=1,
        le=1000000,
    )

    burst_degradation_rate: float = Field(
        default=0.1,
        description="Rate at which burst capacity degrades over time (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    adaptive_burst_sizing: bool = Field(
        default=True,
        description="Whether burst size adapts to historical traffic patterns",
    )

    burst_prediction_enabled: bool = Field(
        default=False,
        description="Whether to predict bursts based on patterns",
    )

    burst_warning_threshold: float = Field(
        default=0.8,
        description="Threshold to warn about approaching burst limits",
        ge=0.0,
        le=1.0,
    )

    allow_burst_overflow: bool = Field(
        default=False,
        description="Whether to allow temporary overflow beyond burst capacity",
    )

    overflow_penalty_multiplier: float = Field(
        default=2.0,
        description="Penalty multiplier for requests during overflow",
        ge=1.0,
        le=10.0,
    )

    def get_burst_capacity(self, base_limit: int) -> int:
        """Calculate burst capacity based on base limit"""
        burst_capacity = int(base_limit * self.burst_capacity_multiplier)

        if self.max_burst_capacity:
            burst_capacity = min(burst_capacity, self.max_burst_capacity)

        return burst_capacity

    def get_burst_threshold(self, base_limit: int) -> int:
        """Calculate threshold to trigger burst detection"""
        return int(base_limit * self.burst_threshold_multiplier)

    def is_burst_triggered(self, current_rate: float, base_limit: int) -> bool:
        """Check if current rate triggers burst mode"""
        if not self.burst_detection_enabled:
            return False

        return current_rate >= self.get_burst_threshold(base_limit)

    def calculate_degraded_capacity(
        self,
        original_capacity: int,
        time_elapsed: float,
    ) -> int:
        """Calculate burst capacity after degradation over time"""
        if time_elapsed <= 0:
            return original_capacity

        # Exponential decay of burst capacity over time
        decay_factor = max(0.0, 1.0 - (self.burst_degradation_rate * time_elapsed))
        return int(original_capacity * decay_factor)

    def should_warn_about_burst(self, current_usage: int, burst_capacity: int) -> bool:
        """Check if should warn about approaching burst limits"""
        if burst_capacity == 0:
            return False

        usage_ratio = current_usage / burst_capacity
        return usage_ratio >= self.burst_warning_threshold

    def can_allow_overflow(self, current_usage: int, burst_capacity: int) -> bool:
        """Check if overflow beyond burst capacity is allowed"""
        return self.allow_burst_overflow and current_usage > burst_capacity

    def calculate_overflow_penalty(self, overflow_amount: int) -> float:
        """Calculate penalty factor for overflow requests"""
        if overflow_amount <= 0:
            return 1.0

        return self.overflow_penalty_multiplier

    def is_in_cooldown(self, last_burst_end: float, current_time: float) -> bool:
        """Check if still in cooldown period after last burst"""
        return (current_time - last_burst_end) < self.burst_cooldown_seconds

    def is_in_grace_period(self, burst_start_time: float, current_time: float) -> bool:
        """Check if still in grace period at start of burst"""
        return (current_time - burst_start_time) < self.burst_grace_period_seconds

    def get_adaptive_burst_size(
        self, historical_peaks: list[float], base_limit: int
    ) -> int:
        """Calculate adaptive burst size based on historical traffic patterns"""
        if not self.adaptive_burst_sizing or not historical_peaks:
            return self.get_burst_capacity(base_limit)

        # Use 95th percentile of historical peaks
        sorted_peaks = sorted(historical_peaks)
        percentile_95_index = int(len(sorted_peaks) * 0.95)
        peak_95 = sorted_peaks[min(percentile_95_index, len(sorted_peaks) - 1)]

        # Adaptive burst size is higher of calculated burst or historical peak
        calculated_burst = self.get_burst_capacity(base_limit)
        adaptive_burst = max(calculated_burst, int(peak_95 * 1.2))

        if self.max_burst_capacity:
            adaptive_burst = min(adaptive_burst, self.max_burst_capacity)

        return adaptive_burst
