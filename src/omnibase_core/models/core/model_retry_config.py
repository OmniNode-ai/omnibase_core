import time

from pydantic import BaseModel, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.core.model_retry_performance import (
    ModelCircuitBreakerRecommendation,
    ModelRetryPerformanceImpact,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.utils.util_hash import deterministic_jitter


class ModelRetryConfig(BaseModel):
    """
    Enterprise-grade retry configuration with comprehensive validation,
    business logic, and intelligent retry strategy management.

    Features:
    - Strong typing with comprehensive validation
    - Exponential and linear backoff strategies
    - Jitter support for distributed systems
    - Circuit breaker integration patterns
    - Retry budget calculations
    - Performance impact assessment
    - Timeout escalation support
    """

    max_attempts: int = Field(
        default=3,
        description="Maximum number of retry attempts",
        ge=1,
        le=10,
    )
    backoff_seconds: float = Field(
        default=1.0,
        description="Base backoff time between retries",
        ge=0.1,
        le=60.0,
    )
    exponential_backoff: bool = Field(
        default=True,
        description="Whether to use exponential backoff",
    )

    @field_validator("max_attempts", mode="before")
    @classmethod
    def validate_max_attempts(cls, v: int) -> int:
        """Validate retry attempts with reasonable limits."""
        if v < 1:
            msg = "Must have at least 1 attempt"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        if v > 10:
            msg = "Too many retry attempts (max 10) - consider circuit breaker instead"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        return v

    @field_validator("backoff_seconds", mode="before")
    @classmethod
    def validate_backoff_seconds(cls, v: float) -> float:
        """Validate backoff timing for practical use."""
        if v < 0.1:
            msg = "Backoff too short (min 0.1 seconds)"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        if v > 60.0:
            msg = "Backoff too long (max 60 seconds) - consider reducing retry attempts"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        return v

    # === Retry Strategy Calculations ===

    def calculate_delay(
        self,
        attempt_number: int,
        include_jitter: bool = True,
    ) -> float:
        """Calculate delay for a specific retry attempt."""
        if attempt_number < 1:
            return 0.0

        if attempt_number > self.max_attempts:
            msg = f"Attempt {attempt_number} exceeds max attempts {self.max_attempts}"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )

        if self.exponential_backoff:
            # Exponential backoff: base * (2 ^ (attempt - 1))
            delay = self.backoff_seconds * (2 ** (attempt_number - 1))
        else:
            # Linear backoff: base * attempt
            delay = self.backoff_seconds * attempt_number

        # Add jitter to prevent thundering herd
        # Uses hash-based jitter seeded by current time - deterministic per seed
        # but not reproducible across calls since time.time() changes each call
        if include_jitter:
            jitter = deterministic_jitter(str(time.time()), delay, jitter_factor=0.1)
            delay += jitter

        # Type narrowing: ensure float return
        result: float = max(0.1, delay)  # Minimum 0.1 second delay
        return result

    def get_all_delays(self, include_jitter: bool = True) -> list[float]:
        """Get all delay times for the retry sequence."""
        return [
            self.calculate_delay(i, include_jitter)
            for i in range(1, self.max_attempts + 1)
        ]

    def get_total_retry_time(self, include_jitter: bool = False) -> float:
        """Get total time that retries will take."""
        return sum(self.get_all_delays(include_jitter))

    def get_retry_budget_seconds(self) -> float:
        """Get the total time budget for all retries."""
        # Conservative estimate without jitter
        return self.get_total_retry_time(include_jitter=False)

    # === Strategy Assessment ===

    def get_retry_strategy_type(self) -> str:
        """Get the retry strategy classification."""
        if self.exponential_backoff:
            if self.max_attempts <= 3:
                return "conservative_exponential"
            if self.max_attempts <= 5:
                return "moderate_exponential"
            return "aggressive_exponential"
        if self.max_attempts <= 3:
            return "conservative_linear"
        if self.max_attempts <= 5:
            return "moderate_linear"
        return "aggressive_linear"

    def is_aggressive_strategy(self) -> bool:
        """Check if this is an aggressive retry strategy."""
        total_time = self.get_total_retry_time()
        return self.max_attempts > 5 or total_time > 30.0

    def is_conservative_strategy(self) -> bool:
        """Check if this is a conservative retry strategy."""
        total_time = self.get_total_retry_time()
        return self.max_attempts <= 3 and total_time <= 10.0

    # === Performance Assessment ===

    def get_performance_impact(self) -> ModelRetryPerformanceImpact:
        """Assess the performance impact of this retry configuration."""
        total_time = self.get_total_retry_time()

        if total_time <= 5.0:
            latency_impact = "minimal"
        elif total_time <= 15.0:
            latency_impact = "moderate"
        else:
            latency_impact = "high"

        if self.max_attempts <= 3:
            resource_impact = "low"
        elif self.max_attempts <= 5:
            resource_impact = "moderate"
        else:
            resource_impact = "high"

        backoff_efficiency = "high" if self.exponential_backoff else "moderate"

        return ModelRetryPerformanceImpact(
            latency_impact=latency_impact,
            resource_impact=resource_impact,
            backoff_efficiency=backoff_efficiency,
            total_retry_time=f"{total_time:.1f}s",
            strategy_type=self.get_retry_strategy_type(),
        )

    def get_performance_recommendations(self) -> list[str]:
        """Get performance tuning recommendations."""
        recommendations = []

        total_time = self.get_total_retry_time()
        if total_time > 30.0:
            recommendations.append(
                "Total retry time is very high - consider reducing attempts or backoff",
            )

        if not self.exponential_backoff and self.max_attempts > 3:
            recommendations.append(
                "Consider exponential backoff for better resource utilization",
            )

        if self.backoff_seconds > 10.0:
            recommendations.append("High base backoff may cause unnecessary delays")

        if self.max_attempts > 5:
            recommendations.append(
                "High retry count may indicate need for circuit breaker pattern",
            )

        if self.exponential_backoff and self.backoff_seconds > 2.0:
            recommendations.append(
                "High base backoff with exponential growth may cause very long delays",
            )

        return recommendations

    # === Circuit Breaker Integration ===

    def should_use_circuit_breaker(self) -> bool:
        """Determine if a circuit breaker should be used with this configuration."""
        return self.max_attempts > 3 or self.get_total_retry_time() > 15.0

    def get_circuit_breaker_recommendations(self) -> ModelCircuitBreakerRecommendation:
        """Get circuit breaker configuration recommendations."""
        if not self.should_use_circuit_breaker():
            return ModelCircuitBreakerRecommendation(
                recommended=False,
                reason="Retry configuration is conservative enough",
            )

        # Calculate failure threshold based on retry attempts
        failure_threshold = max(5, self.max_attempts * 2)

        # Calculate timeout based on retry budget
        timeout_seconds = max(30, int(self.get_total_retry_time() * 2))

        return ModelCircuitBreakerRecommendation(
            recommended=True,
            failure_threshold=failure_threshold,
            timeout_seconds=timeout_seconds,
            half_open_max_calls=max(3, self.max_attempts),
            reason=f"High retry count ({self.max_attempts}) or long retry time ({self.get_total_retry_time():.1f}s)",
        )

    # === Timeout Integration ===

    def get_recommended_timeout(self, base_operation_timeout: float) -> float:
        """Get recommended total timeout including retries."""
        retry_budget = self.get_retry_budget_seconds()

        # Total timeout should be: base operation timeout * attempts + retry delays
        total_timeout = (base_operation_timeout * self.max_attempts) + retry_budget

        # Add 20% buffer for network variability
        return total_timeout * 1.2

    def validate_timeout_compatibility(self, total_timeout: float) -> tuple[bool, str]:
        """Validate if the retry config is compatible with a given timeout."""
        min_required = self.get_recommended_timeout(1.0)  # Assume 1s base operation

        if total_timeout < min_required:
            return (
                False,
                f"Timeout {total_timeout}s too short for retry config (need {min_required:.1f}s)",
            )

        if total_timeout > min_required * 3:
            return (
                True,
                f"Timeout {total_timeout}s is very generous (minimum {min_required:.1f}s)",
            )

        return True, "Timeout is compatible with retry configuration"

    # === Error Classification Support ===

    def should_retry_error(
        self,
        error_code: int | None = None,
        error_type: str | None = None,
    ) -> bool:
        """Determine if an error should be retried based on classification."""
        # Non-retryable HTTP status codes
        if error_code:
            non_retryable_codes = {400, 401, 403, 404, 405, 409, 410, 422}
            if error_code in non_retryable_codes:
                return False

            # Retryable codes
            retryable_codes = {429, 500, 502, 503, 504, 507, 508}
            if error_code in retryable_codes:
                return True

        # Error type based decisions
        if error_type:
            non_retryable_types = {
                "ValidationError",
                "AuthenticationError",
                "AuthorizationError",
                "NotFoundError",
                "ConflictError",
            }
            if error_type in non_retryable_types:
                return False

            retryable_types = {
                "TimeoutError",
                "ConnectionError",
                "ServerError",
                "RateLimitError",
                "TemporaryError",
            }
            if error_type in retryable_types:
                return True

        # Default: retry if we have attempts left
        return True

    def get_retry_error_categories(self) -> dict[str, list[str]]:
        """Get categorized list of retryable and non-retryable errors."""
        return {
            "always_retry": [
                "Network timeout",
                "Connection reset",
                "Server temporarily unavailable",
                "Rate limit exceeded",
                "Internal server error",
                "Bad gateway",
                "Service unavailable",
                "Gateway timeout",
            ],
            "never_retry": [
                "Invalid request format",
                "Authentication failed",
                "Authorization denied",
                "Resource not found",
                "Method not allowed",
                "Resource conflict",
                "Validation failed",
                "Malformed request",
            ],
            "conditional_retry": [
                "Database connection failed",
                "External service timeout",
                "Partial failure",
                "Dependency unavailable",
            ],
        }

    # === Factory Methods ===

    @classmethod
    def create_conservative(cls) -> "ModelRetryConfig":
        """Create conservative retry configuration for critical operations."""
        return cls(max_attempts=2, backoff_seconds=1.0, exponential_backoff=True)

    @classmethod
    def create_standard(cls) -> "ModelRetryConfig":
        """Create standard retry configuration for typical operations."""
        return cls(max_attempts=3, backoff_seconds=1.0, exponential_backoff=True)

    @classmethod
    def create_aggressive(cls) -> "ModelRetryConfig":
        """Create aggressive retry configuration for resilient operations."""
        return cls(max_attempts=5, backoff_seconds=0.5, exponential_backoff=True)

    @classmethod
    def create_linear(
        cls,
        max_attempts: int = 3,
        backoff_seconds: float = 2.0,
    ) -> "ModelRetryConfig":
        """Create linear backoff retry configuration."""
        return cls(
            max_attempts=max_attempts,
            backoff_seconds=backoff_seconds,
            exponential_backoff=False,
        )

    @classmethod
    def create_fast_fail(cls) -> "ModelRetryConfig":
        """Create fast-fail configuration for quick feedback."""
        return cls(max_attempts=1, backoff_seconds=0.1, exponential_backoff=False)

    @classmethod
    def create_for_timeout(
        cls,
        total_timeout: float,
        base_operation_time: float = 1.0,
    ) -> "ModelRetryConfig":
        """Create retry configuration that fits within a total timeout."""
        # Calculate how many attempts we can fit
        max_possible_attempts = int(total_timeout / base_operation_time)
        max_attempts = min(max_possible_attempts, 5)  # Cap at 5 attempts

        # Calculate backoff that uses remaining time efficiently
        retry_time_budget = total_timeout - (base_operation_time * max_attempts)
        backoff_seconds = (
            min(retry_time_budget / max_attempts, 5.0) if max_attempts > 1 else 1.0
        )

        return cls(
            max_attempts=max(1, max_attempts),
            backoff_seconds=max(0.1, backoff_seconds),
            exponential_backoff=True,
        )
