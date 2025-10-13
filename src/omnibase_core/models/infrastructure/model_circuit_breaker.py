"""Circuit breaker model for handling external service failures."""

from datetime import datetime, timedelta

from omnibase_core.enums.enum_circuit_breaker_state import EnumCircuitBreakerState


class ModelCircuitBreaker:
    """
    Circuit breaker pattern for handling external service failures.

    Prevents cascading failures by temporarily disabling calls to failing services.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_seconds: int = 60,
        half_open_max_attempts: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self.half_open_max_attempts = half_open_max_attempts

        self.state = EnumCircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.half_open_attempts = 0

    def can_execute(self) -> bool:
        """Check if operation can be executed based on circuit breaker state."""
        now = datetime.now()

        if self.state == EnumCircuitBreakerState.CLOSED:
            return True
        if self.state == EnumCircuitBreakerState.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time and now - self.last_failure_time > timedelta(
                seconds=self.recovery_timeout_seconds,
            ):
                self.state = EnumCircuitBreakerState.HALF_OPEN
                self.half_open_attempts = 0
                return True
            return False
        # EnumCircuitBreakerState.HALF_OPEN
        return self.half_open_attempts < self.half_open_max_attempts

    def record_success(self) -> None:
        """Record successful operation."""
        if self.state == EnumCircuitBreakerState.HALF_OPEN:
            self.state = EnumCircuitBreakerState.CLOSED
            self.failure_count = 0
            self.half_open_attempts = 0
        elif self.state == EnumCircuitBreakerState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self) -> None:
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == EnumCircuitBreakerState.HALF_OPEN:
            self.state = EnumCircuitBreakerState.OPEN
            self.half_open_attempts = 0
        elif (
            self.state == EnumCircuitBreakerState.CLOSED
            and self.failure_count >= self.failure_threshold
        ):
            self.state = EnumCircuitBreakerState.OPEN
