#!/usr/bin/env python3
"""
Circuit breaker pattern implementation for canary nodes.

Provides fault tolerance and cascading failure prevention for external service calls
with configurable thresholds and recovery mechanisms.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Any, TypeVar

from pydantic import BaseModel, Field

# Remove canary config dependency - circuit breaker is self-contained

T = TypeVar("T")


class CircuitBreakerState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failures detected, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service recovered


class ModelCircuitBreakerConfig(BaseModel):
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = Field(
        default=5,
        description="Number of failures before opening",
    )
    recovery_timeout_seconds: int = Field(
        default=60,
        description="Time before trying recovery",
    )
    success_threshold: int = Field(
        default=3,
        description="Successes needed to close from half-open",
    )
    timeout_seconds: float = Field(default=10.0, description="Request timeout")


class ModelCircuitBreakerStats(BaseModel):
    """Circuit breaker statistics."""

    state: CircuitBreakerState
    failure_count: int = 0
    success_count: int = 0
    total_requests: int = 0
    last_failure_time: float | None = None
    last_success_time: float | None = None


class CircuitBreakerException(Exception):
    """Exception raised when circuit breaker is open."""

    def __init__(self, service_name: str, state: CircuitBreakerState):
        self.service_name = service_name
        self.state = state
        super().__init__(
            f"Circuit breaker is {state.value} for service: {service_name}",
        )


class CircuitBreaker:
    """
    Circuit breaker for external service calls.

    Implements the circuit breaker pattern to prevent cascading failures
    and provide graceful degradation when external services are unavailable.
    """

    def __init__(
        self,
        service_name: str,
        config: ModelCircuitBreakerConfig | None = None,
    ):
        self.service_name = service_name
        self.config = config or ModelCircuitBreakerConfig()
        self.stats = ModelCircuitBreakerStats(state=CircuitBreakerState.CLOSED)
        self._lock = asyncio.Lock()

    async def call(
        self,
        func: Callable[[], Awaitable[T]],
        fallback: Callable[[], Awaitable[T]] | None = None,
    ) -> T:
        """
        Execute a function through the circuit breaker.

        Args:
            func: The async function to execute
            fallback: Optional fallback function if circuit is open

        Returns:
            Result of the function call

        Raises:
            CircuitBreakerException: If circuit is open and no fallback provided
        """
        async with self._lock:
            self.stats.total_requests += 1

            # Check if circuit should transition states
            await self._check_state_transition()

            # If circuit is open, fail fast or use fallback
            if self.stats.state == CircuitBreakerState.OPEN:
                if fallback:
                    return await fallback()
                raise CircuitBreakerException(self.service_name, self.stats.state)

            # Execute the function
            try:
                # Apply timeout to the function call
                result = await asyncio.wait_for(
                    func(),
                    timeout=self.config.timeout_seconds,
                )

                await self._on_success()
                return result

            except TimeoutError as e:
                await self._on_failure()
                # For timeouts, try fallback if available
                if fallback:
                    return await fallback()
                raise e

            except Exception as e:
                await self._on_failure()
                # For other exceptions, try fallback if available
                if fallback:
                    return await fallback()
                raise e

    async def _check_state_transition(self) -> None:
        """Check if circuit breaker should transition states."""
        current_time = time.time()

        if self.stats.state == CircuitBreakerState.OPEN:
            # Check if we should try half-open
            if (
                self.stats.last_failure_time
                and current_time - self.stats.last_failure_time
                >= self.config.recovery_timeout_seconds
            ):
                self.stats.state = CircuitBreakerState.HALF_OPEN
                self.stats.success_count = 0  # Reset success count for half-open test

        elif self.stats.state == CircuitBreakerState.HALF_OPEN:
            # If we have enough successes, close the circuit
            if self.stats.success_count >= self.config.success_threshold:
                self.stats.state = CircuitBreakerState.CLOSED
                self.stats.failure_count = 0  # Reset failure count

        elif self.stats.state == CircuitBreakerState.CLOSED:
            # If we have too many failures, open the circuit
            if self.stats.failure_count >= self.config.failure_threshold:
                self.stats.state = CircuitBreakerState.OPEN

    async def _on_success(self) -> None:
        """Handle successful function execution."""
        self.stats.last_success_time = time.time()

        if self.stats.state == CircuitBreakerState.HALF_OPEN:
            self.stats.success_count += 1
        elif self.stats.state == CircuitBreakerState.CLOSED:
            # Reset failure count on success
            self.stats.failure_count = 0

    async def _on_failure(self) -> None:
        """Handle failed function execution."""
        self.stats.last_failure_time = time.time()
        self.stats.failure_count += 1

        # If in half-open state and we get a failure, go back to open
        if self.stats.state == CircuitBreakerState.HALF_OPEN:
            self.stats.state = CircuitBreakerState.OPEN

    def get_stats(self) -> dict[str, Any]:
        """Get current circuit breaker statistics."""
        return {
            "service_name": self.service_name,
            "state": self.stats.state.value,
            "failure_count": self.stats.failure_count,
            "success_count": self.stats.success_count,
            "total_requests": self.stats.total_requests,
            "failure_rate": (
                self.stats.failure_count / max(1, self.stats.total_requests) * 100
            ),
            "last_failure_time": self.stats.last_failure_time,
            "last_success_time": self.stats.last_success_time,
            "config": self.config.model_dump(),
        }

    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        self.stats = ModelCircuitBreakerStats(state=CircuitBreakerState.CLOSED)


class CircuitBreakerManager:
    """Manages multiple circuit breakers for different services."""

    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        self._default_config = ModelCircuitBreakerConfig()

    def get_breaker(
        self,
        service_name: str,
        config: ModelCircuitBreakerConfig | None = None,
    ) -> CircuitBreaker:
        """Get or create a circuit breaker for a service."""
        if service_name not in self._breakers:
            self._breakers[service_name] = CircuitBreaker(
                service_name=service_name,
                config=config or self._default_config,
            )
        return self._breakers[service_name]

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """Get statistics for all circuit breakers."""
        return {name: breaker.get_stats() for name, breaker in self._breakers.items()}

    def reset_breaker(self, service_name: str) -> bool:
        """Reset a specific circuit breaker."""
        if service_name in self._breakers:
            self._breakers[service_name].reset()
            return True
        return False

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            breaker.reset()


# Global circuit breaker manager
_breaker_manager: CircuitBreakerManager | None = None


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get the global circuit breaker manager instance."""
    global _breaker_manager
    if _breaker_manager is None:
        _breaker_manager = CircuitBreakerManager()
    return _breaker_manager


def get_circuit_breaker(
    service_name: str,
    config: ModelCircuitBreakerConfig | None = None,
) -> CircuitBreaker:
    """Get a circuit breaker for a specific service."""
    return get_circuit_breaker_manager().get_breaker(service_name, config)
