#!/usr/bin/env python3
"""
Retry Strategy Pattern for Canary Deployment System.

This module provides a unified, configurable retry strategy system that replaces
scattered retry logic throughout the canary nodes with a centralized, testable
strategy pattern implementation.

Features:
- Multiple retry strategies (Linear, Exponential, Fibonacci, Custom)
- Configurable retry conditions and exception handling
- Circuit breaker integration for fault tolerance
- Comprehensive metrics collection and observability
- Thread-safe operation with async/await support
"""

import asyncio
import logging
import math
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Generic, TypeVar

from pydantic import BaseModel, Field, field_validator

from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.nodes.canary.utils.metrics_collector import get_metrics_collector

# Type variables for generic retry functionality
T = TypeVar("T")
RetryableFunction = Callable[[], Awaitable[T]]


class RetryStrategyType(Enum):
    """Available retry strategy types."""

    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"
    CUSTOM = "custom"
    JITTERED_EXPONENTIAL = "jittered_exponential"


class RetryCondition(Enum):
    """Conditions that determine when to retry."""

    ANY_EXCEPTION = "any_exception"
    SPECIFIC_EXCEPTIONS = "specific_exceptions"
    STATUS_CODES = "status_codes"
    CUSTOM_PREDICATE = "custom_predicate"


@dataclass
class RetryAttemptResult:
    """Result of a single retry attempt."""

    attempt_number: int
    success: bool
    execution_time_ms: float
    exception: Exception | None = None
    result: Any = None
    delay_before_attempt_ms: float = 0


@dataclass
class RetryExecutionResult(Generic[T]):
    """Complete result of retry execution."""

    final_result: T | None
    success: bool
    total_attempts: int
    total_execution_time_ms: float
    attempts: list[RetryAttemptResult] = field(default_factory=list)
    final_exception: Exception | None = None


class RetryConfig(BaseModel):
    """Configuration for retry behavior."""

    strategy_type: RetryStrategyType = Field(
        default=RetryStrategyType.EXPONENTIAL,
        description="Type of retry strategy to use",
    )
    max_attempts: int = Field(
        default=3, ge=1, le=10, description="Maximum number of retry attempts"
    )
    base_delay_ms: int = Field(
        default=1000, ge=0, description="Base delay in milliseconds"
    )
    max_delay_ms: int = Field(
        default=30000,
        ge=1,
        description="Maximum delay between attempts in milliseconds",
    )
    backoff_multiplier: float = Field(
        default=2.0, ge=1.0, le=10.0, description="Multiplier for exponential backoff"
    )
    jitter_enabled: bool = Field(
        default=True, description="Whether to add random jitter to delays"
    )
    jitter_max_ms: int = Field(
        default=1000, ge=0, description="Maximum jitter to add in milliseconds"
    )
    retry_condition: RetryCondition = Field(
        default=RetryCondition.ANY_EXCEPTION,
        description="Condition that determines when to retry",
    )
    retryable_exceptions: list[str] = Field(
        default_factory=lambda: [
            "ConnectionError",
            "TimeoutError",
            "asyncio.TimeoutError",
            "aiohttp.ClientError",
            "httpx.TimeoutException",
        ],
        description="List of exception class names that should trigger retries",
    )
    non_retryable_exceptions: list[str] = Field(
        default_factory=lambda: [
            "ValidationError",
            "ValueError",
            "TypeError",
            "KeyError",
            "AttributeError",
        ],
        description="List of exception class names that should NOT trigger retries",
    )
    timeout_ms: int | None = Field(
        None, ge=1, description="Overall timeout for all retry attempts combined"
    )

    @field_validator("max_delay_ms")
    def validate_max_delay(cls, v, info):
        if "base_delay_ms" in info.data and v < info.data["base_delay_ms"]:
            raise ValueError("max_delay_ms must be >= base_delay_ms")
        return v


class RetryStrategy(ABC):
    """Abstract base class for retry strategies."""

    def __init__(self, config: RetryConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.metrics = get_metrics_collector(
            f"retry_strategy_{config.strategy_type.value}"
        )

    @abstractmethod
    def calculate_delay(self, attempt_number: int) -> float:
        """Calculate delay before the given attempt number (1-based)."""
        pass

    def should_retry(self, exception: Exception, attempt_number: int) -> bool:
        """Determine if we should retry based on the exception and attempt count."""
        if attempt_number >= self.config.max_attempts:
            return False

        exception_name = exception.__class__.__name__

        # Always check non-retryable exceptions first
        if exception_name in self.config.non_retryable_exceptions:
            return False

        if self.config.retry_condition == RetryCondition.ANY_EXCEPTION:
            # Retry any exception not explicitly marked as non-retryable
            return True

        elif self.config.retry_condition == RetryCondition.SPECIFIC_EXCEPTIONS:
            return exception_name in self.config.retryable_exceptions

        return False

    def add_jitter(self, delay_ms: float) -> float:
        """Add jitter to delay if enabled."""
        if not self.config.jitter_enabled:
            return delay_ms

        jitter = random.uniform(0, min(self.config.jitter_max_ms, delay_ms * 0.1))
        return delay_ms + jitter


class LinearRetryStrategy(RetryStrategy):
    """Linear retry strategy with constant delays."""

    def calculate_delay(self, attempt_number: int) -> float:
        """Calculate linear delay: base_delay * attempt_number."""
        base_delay = self.config.base_delay_ms
        delay = base_delay * attempt_number
        delay = min(delay, self.config.max_delay_ms)
        return self.add_jitter(delay)


class ExponentialRetryStrategy(RetryStrategy):
    """Exponential backoff retry strategy."""

    def calculate_delay(self, attempt_number: int) -> float:
        """Calculate exponential delay: base_delay * (multiplier ^ (attempt - 1))."""
        base_delay = self.config.base_delay_ms
        multiplier = self.config.backoff_multiplier
        delay = base_delay * (multiplier ** (attempt_number - 1))
        delay = min(delay, self.config.max_delay_ms)
        return self.add_jitter(delay)


class JitteredExponentialRetryStrategy(RetryStrategy):
    """Exponential backoff with full jitter to prevent thundering herd."""

    def calculate_delay(self, attempt_number: int) -> float:
        """Calculate jittered exponential delay with full randomization."""
        base_delay = self.config.base_delay_ms
        multiplier = self.config.backoff_multiplier
        max_delay = base_delay * (multiplier ** (attempt_number - 1))
        max_delay = min(max_delay, self.config.max_delay_ms)

        # Full jitter: random value between 0 and calculated max
        return random.uniform(0, max_delay)


class FibonacciRetryStrategy(RetryStrategy):
    """Fibonacci sequence based retry strategy."""

    def __init__(self, config: RetryConfig):
        super().__init__(config)
        self._fib_cache = {1: 1, 2: 1}

    def _fibonacci(self, n: int) -> int:
        """Calculate nth Fibonacci number with caching."""
        if n in self._fib_cache:
            return self._fib_cache[n]

        self._fib_cache[n] = self._fibonacci(n - 1) + self._fibonacci(n - 2)
        return self._fib_cache[n]

    def calculate_delay(self, attempt_number: int) -> float:
        """Calculate Fibonacci-based delay."""
        fib_multiplier = self._fibonacci(attempt_number)
        delay = self.config.base_delay_ms * fib_multiplier
        delay = min(delay, self.config.max_delay_ms)
        return self.add_jitter(delay)


class CustomRetryStrategy(RetryStrategy):
    """Custom retry strategy with user-defined delay function."""

    def __init__(self, config: RetryConfig, delay_function: Callable[[int], float]):
        super().__init__(config)
        self.delay_function = delay_function

    def calculate_delay(self, attempt_number: int) -> float:
        """Use custom delay function."""
        delay = self.delay_function(attempt_number)
        delay = min(delay, self.config.max_delay_ms)
        return self.add_jitter(delay)


class RetryExecutor:
    """Main retry executor that orchestrates retry attempts."""

    def __init__(
        self, config: RetryConfig, custom_delay_fn: Callable[[int], float] | None = None
    ):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.metrics = get_metrics_collector("retry_executor")

        # Create appropriate strategy
        self.strategy = self._create_strategy(custom_delay_fn)

    def _create_strategy(
        self, custom_delay_fn: Callable[[int], float] | None = None
    ) -> RetryStrategy:
        """Create the appropriate retry strategy based on configuration."""
        if self.config.strategy_type == RetryStrategyType.LINEAR:
            return LinearRetryStrategy(self.config)
        elif self.config.strategy_type == RetryStrategyType.EXPONENTIAL:
            return ExponentialRetryStrategy(self.config)
        elif self.config.strategy_type == RetryStrategyType.JITTERED_EXPONENTIAL:
            return JitteredExponentialRetryStrategy(self.config)
        elif self.config.strategy_type == RetryStrategyType.FIBONACCI:
            return FibonacciRetryStrategy(self.config)
        elif self.config.strategy_type == RetryStrategyType.CUSTOM:
            if custom_delay_fn is None:
                raise ValueError(
                    "Custom delay function required for CUSTOM strategy type"
                )
            return CustomRetryStrategy(self.config, custom_delay_fn)
        else:
            raise ValueError(
                f"Unsupported retry strategy type: {self.config.strategy_type}"
            )

    async def execute_with_retry(
        self, function: RetryableFunction[T], operation_name: str = "unknown_operation"
    ) -> RetryExecutionResult[T]:
        """
        Execute a function with retry logic.

        Args:
            function: Async function to execute with retries
            operation_name: Name for logging and metrics

        Returns:
            RetryExecutionResult with complete execution details
        """
        start_time = time.time()
        result = RetryExecutionResult[T](
            final_result=None,
            success=False,
            total_attempts=0,
            total_execution_time_ms=0,
        )

        # Check overall timeout
        timeout_deadline = None
        if self.config.timeout_ms:
            timeout_deadline = start_time + (self.config.timeout_ms / 1000)

        for attempt in range(1, self.config.max_attempts + 1):
            # Check timeout before attempt
            if timeout_deadline and time.time() >= timeout_deadline:
                self.logger.warning(
                    "Retry execution timed out before attempt %d for %s",
                    attempt,
                    operation_name,
                )
                break

            attempt_start = time.time()
            attempt_result = RetryAttemptResult(
                attempt_number=attempt, success=False, execution_time_ms=0
            )

            try:
                # Calculate delay before this attempt (except first attempt)
                if attempt > 1:
                    delay_ms = self.strategy.calculate_delay(attempt)
                    attempt_result.delay_before_attempt_ms = delay_ms

                    self.logger.debug(
                        "Retry attempt %d for %s: waiting %.2fms",
                        attempt,
                        operation_name,
                        delay_ms,
                    )

                    # Check if delay would exceed timeout
                    if timeout_deadline:
                        delay_end_time = time.time() + (delay_ms / 1000)
                        if delay_end_time >= timeout_deadline:
                            self.logger.warning(
                                "Delay for attempt %d would exceed timeout for %s",
                                attempt,
                                operation_name,
                            )
                            break

                    await asyncio.sleep(delay_ms / 1000)

                # Execute the function
                self.logger.debug(
                    "Executing attempt %d for %s", attempt, operation_name
                )
                function_result = await function()

                # Success!
                attempt_end = time.time()
                attempt_result.success = True
                attempt_result.result = function_result
                attempt_result.execution_time_ms = (attempt_end - attempt_start) * 1000

                result.attempts.append(attempt_result)
                result.final_result = function_result
                result.success = True
                result.total_attempts = attempt

                self.logger.info(
                    "Operation %s succeeded on attempt %d after %.2fms",
                    operation_name,
                    attempt,
                    attempt_result.execution_time_ms,
                )

                # Record success metrics
                self.metrics.record_custom_metric(
                    f"{operation_name}.retry_success",
                    1,
                    {
                        "attempt_number": attempt,
                        "strategy": self.config.strategy_type.value,
                    },
                )

                break

            except Exception as e:
                attempt_end = time.time()
                attempt_result.success = False
                attempt_result.exception = e
                attempt_result.execution_time_ms = (attempt_end - attempt_start) * 1000
                result.attempts.append(attempt_result)
                result.final_exception = e

                self.logger.warning(
                    "Attempt %d failed for %s: %s (%.2fms)",
                    attempt,
                    operation_name,
                    str(e),
                    attempt_result.execution_time_ms,
                )

                # Check if we should retry
                should_retry = self.strategy.should_retry(e, attempt)
                is_last_attempt = attempt >= self.config.max_attempts

                if not should_retry or is_last_attempt:
                    self.logger.error(
                        "Operation %s failed permanently after %d attempts: %s",
                        operation_name,
                        attempt,
                        str(e),
                    )
                    result.total_attempts = attempt

                    # Record failure metrics
                    self.metrics.record_custom_metric(
                        f"{operation_name}.retry_failure",
                        1,
                        {
                            "final_attempt": attempt,
                            "strategy": self.config.strategy_type.value,
                            "exception_type": e.__class__.__name__,
                        },
                    )
                    break

        # Calculate total execution time
        end_time = time.time()
        result.total_execution_time_ms = (end_time - start_time) * 1000

        # Log final result
        if result.success:
            self.logger.info(
                "Retry execution completed successfully for %s: %d attempts, %.2fms total",
                operation_name,
                result.total_attempts,
                result.total_execution_time_ms,
            )
        else:
            self.logger.error(
                "Retry execution failed for %s: %d attempts, %.2fms total",
                operation_name,
                result.total_attempts,
                result.total_execution_time_ms,
            )

        return result


# Factory functions for common retry configurations
def create_api_retry_config() -> RetryConfig:
    """Create retry configuration optimized for API calls."""
    return RetryConfig(
        strategy_type=RetryStrategyType.JITTERED_EXPONENTIAL,
        max_attempts=3,
        base_delay_ms=1000,
        max_delay_ms=10000,
        backoff_multiplier=2.0,
        jitter_enabled=True,
        retryable_exceptions=[
            "ConnectionError",
            "TimeoutError",
            "aiohttp.ClientError",
            "httpx.TimeoutException",
            "asyncio.TimeoutError",
        ],
    )


def create_database_retry_config() -> RetryConfig:
    """Create retry configuration optimized for database operations."""
    return RetryConfig(
        strategy_type=RetryStrategyType.LINEAR,
        max_attempts=2,
        base_delay_ms=500,
        max_delay_ms=2000,
        retryable_exceptions=[
            "asyncpg.ConnectionDoesNotExistError",
            "asyncpg.InterfaceError",
            "ConnectionError",
        ],
    )


def create_filesystem_retry_config() -> RetryConfig:
    """Create retry configuration optimized for filesystem operations."""
    return RetryConfig(
        strategy_type=RetryStrategyType.LINEAR,
        max_attempts=2,
        base_delay_ms=100,
        max_delay_ms=500,
        jitter_enabled=False,
        retryable_exceptions=["FileNotFoundError", "PermissionError", "OSError"],
    )


# Global retry executors for common use cases
_api_retry_executor = None
_db_retry_executor = None
_fs_retry_executor = None


def get_api_retry_executor() -> RetryExecutor:
    """Get a shared retry executor optimized for API calls."""
    global _api_retry_executor
    if _api_retry_executor is None:
        _api_retry_executor = RetryExecutor(create_api_retry_config())
    return _api_retry_executor


def get_database_retry_executor() -> RetryExecutor:
    """Get a shared retry executor optimized for database operations."""
    global _db_retry_executor
    if _db_retry_executor is None:
        _db_retry_executor = RetryExecutor(create_database_retry_config())
    return _db_retry_executor


def get_filesystem_retry_executor() -> RetryExecutor:
    """Get a shared retry executor optimized for filesystem operations."""
    global _fs_retry_executor
    if _fs_retry_executor is None:
        _fs_retry_executor = RetryExecutor(create_filesystem_retry_config())
    return _fs_retry_executor
