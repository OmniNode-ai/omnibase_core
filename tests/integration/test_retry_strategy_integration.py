#!/usr/bin/env python3
"""
Integration tests for the Retry Strategy Pattern implementation.

Tests comprehensive retry behavior across different strategies, configurations,
and failure scenarios to ensure robust fault tolerance in production.
"""

import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from omnibase_core.nodes.canary.utils.retry_strategy import (
    CustomRetryStrategy,
    ExponentialRetryStrategy,
    FibonacciRetryStrategy,
    JitteredExponentialRetryStrategy,
    LinearRetryStrategy,
    ModelRetryConfig,
    RetryCondition,
    RetryExecutor,
    RetryStrategyType,
    create_api_retry_config,
    create_database_retry_config,
    create_filesystem_retry_config,
    get_api_retry_executor,
    get_database_retry_executor,
    get_filesystem_retry_executor,
)


class TestRetryStrategies:
    """Test different retry strategy implementations."""

    def test_linear_retry_strategy_delay_calculation(self):
        """Test linear strategy delay calculation."""
        config = ModelRetryConfig(
            strategy_type=RetryStrategyType.LINEAR,
            base_delay_ms=1000,
            max_delay_ms=5000,
            jitter_enabled=False,
        )
        strategy = LinearRetryStrategy(config)

        assert strategy.calculate_delay(1) == 1000  # 1000 * 1
        assert strategy.calculate_delay(2) == 2000  # 1000 * 2
        assert strategy.calculate_delay(3) == 3000  # 1000 * 3
        assert strategy.calculate_delay(6) == 5000  # Capped at max_delay_ms

    def test_exponential_retry_strategy_delay_calculation(self):
        """Test exponential strategy delay calculation."""
        config = ModelRetryConfig(
            strategy_type=RetryStrategyType.EXPONENTIAL,
            base_delay_ms=1000,
            max_delay_ms=10000,
            backoff_multiplier=2.0,
            jitter_enabled=False,
        )
        strategy = ExponentialRetryStrategy(config)

        assert strategy.calculate_delay(1) == 1000  # 1000 * (2^0)
        assert strategy.calculate_delay(2) == 2000  # 1000 * (2^1)
        assert strategy.calculate_delay(3) == 4000  # 1000 * (2^2)
        assert strategy.calculate_delay(4) == 8000  # 1000 * (2^3)
        assert strategy.calculate_delay(5) == 10000  # Capped at max_delay_ms

    def test_fibonacci_retry_strategy_delay_calculation(self):
        """Test Fibonacci strategy delay calculation."""
        config = ModelRetryConfig(
            strategy_type=RetryStrategyType.FIBONACCI,
            base_delay_ms=1000,
            max_delay_ms=20000,
            jitter_enabled=False,
        )
        strategy = FibonacciRetryStrategy(config)

        assert strategy.calculate_delay(1) == 1000  # 1000 * fib(1) = 1000 * 1
        assert strategy.calculate_delay(2) == 1000  # 1000 * fib(2) = 1000 * 1
        assert strategy.calculate_delay(3) == 2000  # 1000 * fib(3) = 1000 * 2
        assert strategy.calculate_delay(4) == 3000  # 1000 * fib(4) = 1000 * 3
        assert strategy.calculate_delay(5) == 5000  # 1000 * fib(5) = 1000 * 5

    def test_jittered_exponential_adds_randomness(self):
        """Test that jittered exponential adds appropriate randomness."""
        config = ModelRetryConfig(
            strategy_type=RetryStrategyType.JITTERED_EXPONENTIAL,
            base_delay_ms=1000,
            max_delay_ms=10000,
            backoff_multiplier=2.0,
        )
        strategy = JitteredExponentialRetryStrategy(config)

        # Generate multiple delays for same attempt and verify they differ
        delays = [strategy.calculate_delay(3) for _ in range(10)]
        assert len(set(delays)) > 1, "Jittered delays should vary"
        assert all(
            0 <= delay <= 4000 for delay in delays
        ), "All delays should be in expected range"

    def test_custom_retry_strategy(self):
        """Test custom retry strategy with user-defined function."""

        def custom_delay_fn(attempt: int) -> float:
            return 500 * attempt  # Linear with different base

        config = ModelRetryConfig(
            strategy_type=RetryStrategyType.CUSTOM,
            base_delay_ms=1000,  # Ignored for custom
            max_delay_ms=3000,
            jitter_enabled=False,
        )
        strategy = CustomRetryStrategy(config, custom_delay_fn)

        assert strategy.calculate_delay(1) == 500  # 500 * 1
        assert strategy.calculate_delay(2) == 1000  # 500 * 2
        assert strategy.calculate_delay(3) == 1500  # 500 * 3
        assert strategy.calculate_delay(7) == 3000  # Capped at max_delay_ms

    def test_retry_condition_evaluation(self):
        """Test retry condition evaluation logic."""
        config = ModelRetryConfig(
            retry_condition=RetryCondition.SPECIFIC_EXCEPTIONS,
            retryable_exceptions=["ConnectionError", "TimeoutError"],
            non_retryable_exceptions=["ValueError"],
        )
        strategy = LinearRetryStrategy(config)

        # Should retry these
        assert strategy.should_retry(ConnectionError("test"), 1)
        assert strategy.should_retry(TimeoutError("test"), 1)

        # Should not retry these
        assert not strategy.should_retry(ValueError("test"), 1)
        assert not strategy.should_retry(
            ConnectionError("test"), 5
        )  # Max attempts exceeded


class TestRetryExecutor:
    """Test the main retry executor functionality."""

    @pytest.mark.asyncio
    async def test_successful_execution_no_retries_needed(self):
        """Test successful execution on first attempt."""
        config = ModelRetryConfig(max_attempts=3, base_delay_ms=100)
        executor = RetryExecutor(config)

        async def always_succeed():
            return "success"

        result = await executor.execute_with_retry(always_succeed, "test_op")

        assert result.success is True
        assert result.final_result == "success"
        assert result.total_attempts == 1
        assert len(result.attempts) == 1
        assert result.attempts[0].success is True
        assert result.final_exception is None

    @pytest.mark.asyncio
    async def test_retry_until_success(self):
        """Test retrying until operation succeeds."""
        config = ModelRetryConfig(
            max_attempts=3,
            base_delay_ms=10,  # Small delay for test speed
            jitter_enabled=False,
        )
        executor = RetryExecutor(config)

        call_count = 0

        async def fail_twice_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError(f"Attempt {call_count} failed")
            return f"success_on_attempt_{call_count}"

        result = await executor.execute_with_retry(fail_twice_then_succeed, "test_op")

        assert result.success is True
        assert result.final_result == "success_on_attempt_3"
        assert result.total_attempts == 3
        assert len(result.attempts) == 3
        assert not result.attempts[0].success
        assert not result.attempts[1].success
        assert result.attempts[2].success

    @pytest.mark.asyncio
    async def test_max_attempts_reached_failure(self):
        """Test failure when max attempts are reached."""
        config = ModelRetryConfig(
            max_attempts=2, base_delay_ms=10, jitter_enabled=False
        )
        executor = RetryExecutor(config)

        async def always_fail():
            raise ConnectionError("Always fails")

        result = await executor.execute_with_retry(always_fail, "test_op")

        assert result.success is False
        assert result.final_result is None
        assert result.total_attempts == 2
        assert len(result.attempts) == 2
        assert all(not attempt.success for attempt in result.attempts)
        assert isinstance(result.final_exception, ConnectionError)

    @pytest.mark.asyncio
    async def test_non_retryable_exception_stops_immediately(self):
        """Test that non-retryable exceptions stop retry immediately."""
        config = ModelRetryConfig(
            max_attempts=3,
            retry_condition=RetryCondition.SPECIFIC_EXCEPTIONS,
            retryable_exceptions=["ConnectionError"],
            non_retryable_exceptions=["ValueError"],
        )
        executor = RetryExecutor(config)

        async def fail_with_non_retryable():
            raise ValueError("This should not be retried")

        result = await executor.execute_with_retry(fail_with_non_retryable, "test_op")

        assert result.success is False
        assert result.total_attempts == 1
        assert len(result.attempts) == 1
        assert isinstance(result.final_exception, ValueError)

    @pytest.mark.asyncio
    async def test_timeout_functionality(self):
        """Test overall timeout functionality."""
        config = ModelRetryConfig(
            max_attempts=5,
            base_delay_ms=20,  # Small delays
            timeout_ms=50,  # Very short timeout - smaller than operation time
            jitter_enabled=False,
        )
        executor = RetryExecutor(config)

        call_count = 0

        async def operation_that_times_out():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First attempt should succeed to ensure we get to retry logic
                await asyncio.sleep(0.01)  # 10ms
                raise ConnectionError("Fail first attempt")
            else:
                # Subsequent attempts will hit timeout during delay
                await asyncio.sleep(0.1)  # 100ms - longer than remaining timeout
                return "should_not_reach"

        start_time = time.time()
        result = await executor.execute_with_retry(operation_that_times_out, "test_op")
        end_time = time.time()

        # Should fail due to timeout, not complete all attempts
        assert result.success is False
        assert (end_time - start_time) < 0.15  # Should timeout quickly
        assert result.total_attempts < 5  # Should not reach max attempts

    @pytest.mark.asyncio
    async def test_delay_calculation_integration(self):
        """Test that delays are actually applied during retries."""
        config = ModelRetryConfig(
            strategy_type=RetryStrategyType.LINEAR,
            max_attempts=3,
            base_delay_ms=50,
            jitter_enabled=False,
        )
        executor = RetryExecutor(config)

        call_times = []

        async def record_timing():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ConnectionError("Fail for timing test")
            return "success"

        start_time = time.time()
        result = await executor.execute_with_retry(record_timing, "test_op")

        assert result.success is True
        assert len(call_times) == 3

        # Verify delays were applied (approximately)
        delay1 = (call_times[1] - call_times[0]) * 1000  # ms
        delay2 = (call_times[2] - call_times[1]) * 1000  # ms

        # Linear strategy: attempt 2 should have delay ~50ms, attempt 3 should have delay ~100ms
        # With some tolerance for timing variations
        assert 40 <= delay1 <= 120  # More tolerance for first delay
        assert 80 <= delay2 <= 180  # More tolerance for second delay


class TestPreConfiguredRetryExecutors:
    """Test the pre-configured retry executors for common use cases."""

    def test_api_retry_config(self):
        """Test API retry configuration is appropriate."""
        config = create_api_retry_config()

        assert config.strategy_type == RetryStrategyType.JITTERED_EXPONENTIAL
        assert config.max_attempts == 3
        assert config.base_delay_ms == 1000
        assert config.max_delay_ms == 10000
        assert config.jitter_enabled is True
        assert "ConnectionError" in config.retryable_exceptions
        assert "TimeoutError" in config.retryable_exceptions

    def test_database_retry_config(self):
        """Test database retry configuration is appropriate."""
        config = create_database_retry_config()

        assert config.strategy_type == RetryStrategyType.LINEAR
        assert config.max_attempts == 2  # Conservative for DB operations
        assert config.base_delay_ms == 500
        assert config.max_delay_ms == 2000

    def test_filesystem_retry_config(self):
        """Test filesystem retry configuration is appropriate."""
        config = create_filesystem_retry_config()

        assert config.strategy_type == RetryStrategyType.LINEAR
        assert config.max_attempts == 2
        assert config.base_delay_ms == 100  # Fast for filesystem
        assert config.max_delay_ms == 500
        assert config.jitter_enabled is False  # No jitter needed for FS

    @pytest.mark.asyncio
    async def test_global_executors_are_singletons(self):
        """Test that global executors return the same instances."""
        api_executor1 = get_api_retry_executor()
        api_executor2 = get_api_retry_executor()

        assert api_executor1 is api_executor2

        db_executor1 = get_database_retry_executor()
        db_executor2 = get_database_retry_executor()

        assert db_executor1 is db_executor2

        fs_executor1 = get_filesystem_retry_executor()
        fs_executor2 = get_filesystem_retry_executor()

        assert fs_executor1 is fs_executor2

    @pytest.mark.asyncio
    async def test_api_executor_with_connection_errors(self):
        """Test API executor handles connection errors appropriately."""
        executor = get_api_retry_executor()

        call_count = 0

        async def flaky_api_call():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network issue")
            return {"status": "success", "data": "api_response"}

        result = await executor.execute_with_retry(flaky_api_call, "api_call")

        assert result.success is True
        assert result.total_attempts == 3
        assert result.final_result["status"] == "success"

    @pytest.mark.asyncio
    async def test_database_executor_with_connection_failure(self):
        """Test database executor handles connection failures appropriately."""
        executor = get_database_retry_executor()

        call_count = 0

        async def flaky_db_query():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("DB connection lost")
            return [{"id": 1, "name": "test"}]

        result = await executor.execute_with_retry(flaky_db_query, "db_query")

        assert result.success is True
        assert result.total_attempts == 2
        assert len(result.final_result) == 1


class TestRetryStrategyMetrics:
    """Test retry strategy metrics collection."""

    @pytest.mark.asyncio
    async def test_metrics_collection_on_success(self):
        """Test that success metrics are recorded properly."""
        config = ModelRetryConfig(max_attempts=2, base_delay_ms=10)

        with patch(
            "omnibase_core.nodes.canary.utils.retry_strategy.get_metrics_collector"
        ) as mock_metrics:
            mock_collector = MagicMock()
            mock_metrics.return_value = mock_collector

            executor = RetryExecutor(config)

            call_count = 0

            async def succeed_on_second_try():
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise ConnectionError("First attempt fails")
                return "success"

            result = await executor.execute_with_retry(succeed_on_second_try, "test_op")

            assert result.success is True

            # Verify success metric was recorded
            mock_collector.record_custom_metric.assert_called_with(
                "test_op.retry_success",
                1,
                {"attempt_number": 2, "strategy": "exponential"},
            )

    @pytest.mark.asyncio
    async def test_metrics_collection_on_failure(self):
        """Test that failure metrics are recorded properly."""
        config = ModelRetryConfig(
            max_attempts=2,
            base_delay_ms=10,
            retry_condition=RetryCondition.ANY_EXCEPTION,
            non_retryable_exceptions=[],  # Make ValueError retryable for this test
        )

        with patch(
            "omnibase_core.nodes.canary.utils.retry_strategy.get_metrics_collector"
        ) as mock_metrics:
            mock_collector = MagicMock()
            mock_metrics.return_value = mock_collector

            executor = RetryExecutor(config)

            async def always_fail():
                raise ValueError("Always fails")

            result = await executor.execute_with_retry(always_fail, "test_op")

            assert result.success is False

            # Verify failure metric was recorded with correct attempt count
            mock_collector.record_custom_metric.assert_called_with(
                "test_op.retry_failure",
                1,
                {
                    "final_attempt": 2,  # Should reach max attempts since ValueError is now retryable
                    "strategy": "exponential",
                    "exception_type": "ValueError",
                },
            )


class TestRetryStrategyEdgeCases:
    """Test edge cases and error conditions."""

    def test_invalid_retry_config_validation(self):
        """Test validation of retry configuration."""
        # Test max_delay_ms < base_delay_ms
        with pytest.raises(ValueError, match="max_delay_ms must be >= base_delay_ms"):
            ModelRetryConfig(base_delay_ms=1000, max_delay_ms=500)

        # Test invalid max_attempts
        with pytest.raises(ValueError):
            ModelRetryConfig(max_attempts=0)

        # Test invalid backoff_multiplier
        with pytest.raises(ValueError):
            ModelRetryConfig(backoff_multiplier=0.5)

    def test_custom_strategy_without_delay_function(self):
        """Test custom strategy requires delay function."""
        config = ModelRetryConfig(strategy_type=RetryStrategyType.CUSTOM)

        with pytest.raises(ValueError, match="Custom delay function required"):
            RetryExecutor(config)

    @pytest.mark.asyncio
    async def test_zero_delay_configuration(self):
        """Test retry with zero base delay."""
        config = ModelRetryConfig(max_attempts=3, base_delay_ms=0, jitter_enabled=False)
        executor = RetryExecutor(config)

        call_count = 0
        start_time = time.time()

        async def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Fail")
            return "success"

        result = await executor.execute_with_retry(fail_twice, "test_op")
        end_time = time.time()

        assert result.success is True
        assert result.total_attempts == 3
        # Should complete very quickly with zero delays
        assert (end_time - start_time) < 0.1

    @pytest.mark.asyncio
    async def test_very_short_timeout(self):
        """Test behavior with extremely short timeout."""
        config = ModelRetryConfig(
            max_attempts=10,
            base_delay_ms=50,
            timeout_ms=20,  # 20ms timeout - very short but allows first attempt
        )
        executor = RetryExecutor(config)

        call_count = 0

        async def operation_with_retry_needed():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First attempt fails quickly
                await asyncio.sleep(0.005)  # 5ms
                raise ConnectionError("First attempt fails")
            else:
                # This should not execute due to timeout during delay
                await asyncio.sleep(0.01)  # 10ms
                return "result"

        result = await executor.execute_with_retry(
            operation_with_retry_needed, "test_op"
        )

        # Should fail due to timeout before reaching max attempts
        # The timeout should prevent retry attempts
        assert result.success is False
        assert result.total_attempts < 10


if __name__ == "__main__":
    """Run integration tests directly."""
    pytest.main([__file__, "-v", "--tb=short"])
