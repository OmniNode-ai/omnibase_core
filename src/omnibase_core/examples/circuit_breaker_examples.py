#!/usr/bin/env python3
"""
Examples demonstrating circuit breaker pattern for external dependencies.

Shows various circuit breaker usage patterns, configurations, and integration
with external services for fault tolerance and graceful degradation.
"""

import asyncio
import logging
import random
import time
from datetime import datetime
from typing import Any, Dict, List

from omnibase_core.core.resilience import (
    CircuitBreakerEvent,
    CircuitBreakerException,
    CircuitBreakerFactory,
    CircuitBreakerOpenException,
    CircuitBreakerState,
    ExternalDependencyCircuitBreaker,
    ModelCircuitBreakerConfig,
    get_circuit_breaker,
    list_circuit_breakers,
    register_circuit_breaker,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MockExternalService:
    """Mock external service for demonstration."""

    def __init__(self, name: str, failure_rate: float = 0.0, slow_rate: float = 0.0):
        self.name = name
        self.failure_rate = failure_rate
        self.slow_rate = slow_rate
        self.call_count = 0

    async def call(self, data: Any = None) -> Dict[str, Any]:
        """Simulate API call with configurable failure and slowness."""
        self.call_count += 1

        # Simulate slow calls
        if random.random() < self.slow_rate:
            await asyncio.sleep(2.0)  # Slow response

        # Simulate failures
        if random.random() < self.failure_rate:
            raise Exception(f"{self.name} service temporarily unavailable")

        await asyncio.sleep(0.1)  # Normal response time

        return {
            "service": self.name,
            "status": "success",
            "data": data,
            "call_count": self.call_count,
            "timestamp": datetime.utcnow().isoformat(),
        }


async def example_basic_circuit_breaker():
    """Example: Basic circuit breaker usage."""
    print("\n=== Basic Circuit Breaker Example ===")

    # Create a service that fails 30% of the time
    service = MockExternalService("payment-api", failure_rate=0.3)

    # Create circuit breaker with default configuration
    circuit_breaker = ExternalDependencyCircuitBreaker("payment-api")

    print(f"Initial state: {circuit_breaker.get_state()}")

    # Make several calls to trigger state changes
    for i in range(15):
        try:
            result = await circuit_breaker.call(service.call, data=f"request-{i}")
            print(f"Call {i+1}: SUCCESS - {result['status']}")
        except CircuitBreakerException as e:
            print(f"Call {i+1}: CIRCUIT BREAKER - {e}")
        except Exception as e:
            print(f"Call {i+1}: FAILURE - {e}")

        # Brief pause between calls
        await asyncio.sleep(0.2)

    # Show final metrics
    metrics = circuit_breaker.get_metrics()
    print(f"\nFinal metrics:")
    print(f"  State: {metrics.current_state}")
    print(f"  Total requests: {metrics.total_requests}")
    print(f"  Success rate: {metrics.get_success_rate():.2%}")
    print(f"  State changes: {metrics.state_changes}")


async def example_circuit_breaker_with_fallback():
    """Example: Circuit breaker with fallback functionality."""
    print("\n=== Circuit Breaker with Fallback Example ===")

    # Create unreliable service
    service = MockExternalService("user-api", failure_rate=0.6)

    # Create fast-fail circuit breaker
    circuit_breaker = CircuitBreakerFactory.create_fast_fail("user-api")

    # Define fallback function
    async def fallback_get_user(user_id: str = "default") -> Dict[str, Any]:
        """Fallback that returns cached/default user data."""
        return {
            "service": "user-api-cache",
            "status": "fallback",
            "user_id": user_id,
            "name": "Default User",
            "cached": True,
            "timestamp": datetime.utcnow().isoformat(),
        }

    print(f"Initial state: {circuit_breaker.get_state()}")

    # Make calls with fallback
    for i in range(10):
        try:
            result = await circuit_breaker.call(
                lambda: service.call(f"user-{i}"),
                fallback=lambda: fallback_get_user(f"user-{i}"),
            )

            status = "FALLBACK" if result.get("cached") else "SUCCESS"
            print(f"Call {i+1}: {status} - {result.get('name', result.get('data'))}")

        except Exception as e:
            print(f"Call {i+1}: ERROR - {e}")

        await asyncio.sleep(0.1)

    # Show final state
    print(f"\nFinal state: {circuit_breaker.get_state()}")


async def example_circuit_breaker_context_manager():
    """Example: Using circuit breaker as context manager."""
    print("\n=== Circuit Breaker Context Manager Example ===")

    service = MockExternalService("notification-api", failure_rate=0.4)
    circuit_breaker = ExternalDependencyCircuitBreaker("notification-api")

    for i in range(8):
        try:
            async with circuit_breaker.protect(timeout=5.0) as cb:
                # Perform external operation
                result = await service.call(f"notification-{i}")
                cb.set_result(result)

            print(f"Notification {i+1}: SUCCESS")

        except CircuitBreakerException as e:
            print(f"Notification {i+1}: CIRCUIT OPEN - using default notification")
        except Exception as e:
            print(f"Notification {i+1}: FAILED - {e}")

        await asyncio.sleep(0.3)


async def example_environment_configured_circuit_breaker():
    """Example: Environment-configured circuit breaker."""
    print("\n=== Environment-Configured Circuit Breaker Example ===")

    import os

    # Set environment variables for circuit breaker configuration
    os.environ["CIRCUIT_BREAKER_EMAIL_SERVICE_FAILURE_THRESHOLD"] = "3"
    os.environ["CIRCUIT_BREAKER_EMAIL_SERVICE_FAILURE_RATE_THRESHOLD"] = "0.4"
    os.environ["CIRCUIT_BREAKER_EMAIL_SERVICE_RECOVERY_TIMEOUT_SECONDS"] = "30"
    os.environ["CIRCUIT_BREAKER_EMAIL_SERVICE_REQUEST_TIMEOUT_SECONDS"] = "5.0"
    os.environ["CIRCUIT_BREAKER_EMAIL_SERVICE_LOG_STATE_CHANGES"] = "true"

    # Create circuit breaker from environment
    circuit_breaker = CircuitBreakerFactory.create_from_environment("email-service")

    service = MockExternalService("email-service", failure_rate=0.5)

    print(f"Configuration loaded from environment:")
    print(f"  Failure threshold: {circuit_breaker.config.failure_threshold}")
    print(f"  Failure rate threshold: {circuit_breaker.config.failure_rate_threshold}")
    print(f"  Recovery timeout: {circuit_breaker.config.recovery_timeout_seconds}s")
    print(f"  Request timeout: {circuit_breaker.config.request_timeout_seconds}s")

    # Test the circuit breaker
    for i in range(8):
        try:
            result = await circuit_breaker.call(lambda: service.call(f"email-{i}"))
            print(f"Email {i+1}: SENT")
        except Exception as e:
            print(f"Email {i+1}: FAILED - {e}")

        await asyncio.sleep(0.2)


async def example_circuit_breaker_events():
    """Example: Circuit breaker event handling."""
    print("\n=== Circuit Breaker Events Example ===")

    events_log = []

    async def log_state_changes(cb, event, metrics):
        """Log state change events."""
        if event == CircuitBreakerEvent.STATE_CHANGE:
            events_log.append(f"State changed to: {metrics.current_state}")
            print(f"EVENT: State changed to {metrics.current_state}")

    async def log_failures(cb, event, metrics):
        """Log failure events."""
        if event == CircuitBreakerEvent.FAILURE:
            events_log.append(f"Failure recorded (total: {metrics.failed_requests})")
            print(f"EVENT: Failure recorded (total: {metrics.failed_requests})")

    async def log_fallbacks(cb, event, metrics):
        """Log fallback executions."""
        if event == CircuitBreakerEvent.FALLBACK_EXECUTED:
            events_log.append("Fallback executed")
            print("EVENT: Fallback executed")

    # Create circuit breaker and register event listeners
    circuit_breaker = CircuitBreakerFactory.create_fast_fail("analytics-api")
    circuit_breaker.add_event_listener(
        CircuitBreakerEvent.STATE_CHANGE, log_state_changes
    )
    circuit_breaker.add_event_listener(CircuitBreakerEvent.FAILURE, log_failures)
    circuit_breaker.add_event_listener(
        CircuitBreakerEvent.FALLBACK_EXECUTED, log_fallbacks
    )

    service = MockExternalService("analytics-api", failure_rate=0.7)

    # Fallback function
    async def analytics_fallback():
        return {"analytics": "cached", "status": "fallback"}

    # Make calls to trigger events
    for i in range(6):
        try:
            result = await circuit_breaker.call(
                lambda: service.call(f"analytics-{i}"), fallback=analytics_fallback
            )
            print(f"Analytics {i+1}: {result.get('status', 'success')}")
        except Exception as e:
            print(f"Analytics {i+1}: ERROR - {e}")

        await asyncio.sleep(0.1)

    print(f"\nEvents captured: {len(events_log)}")
    for event in events_log:
        print(f"  - {event}")


async def example_multiple_circuit_breakers():
    """Example: Managing multiple circuit breakers."""
    print("\n=== Multiple Circuit Breakers Example ===")

    # Create different services with different reliability
    services = {
        "database": MockExternalService("database", failure_rate=0.1),
        "cache": MockExternalService("cache", failure_rate=0.2),
        "search": MockExternalService("search", failure_rate=0.4),
        "recommendations": MockExternalService("recommendations", failure_rate=0.6),
    }

    # Create circuit breakers with different configurations
    cb_database = CircuitBreakerFactory.create_resilient("database")
    cb_cache = CircuitBreakerFactory.create_fast_fail("cache")
    cb_search = ExternalDependencyCircuitBreaker("search")
    cb_recommendations = CircuitBreakerFactory.create_fast_fail("recommendations")

    # Register in global registry
    register_circuit_breaker("database", cb_database)
    register_circuit_breaker("cache", cb_cache)
    register_circuit_breaker("search", cb_search)
    register_circuit_breaker("recommendations", cb_recommendations)

    circuit_breakers = {
        "database": cb_database,
        "cache": cb_cache,
        "search": cb_search,
        "recommendations": cb_recommendations,
    }

    print("Making requests to all services...")

    # Simulate requests to all services
    for round_num in range(5):
        print(f"\nRound {round_num + 1}:")

        for service_name, cb in circuit_breakers.items():
            try:
                result = await cb.call(
                    lambda sn=service_name: services[sn].call(f"request-{round_num}")
                )
                print(f"  {service_name}: SUCCESS")
            except CircuitBreakerException:
                print(f"  {service_name}: CIRCUIT OPEN")
            except Exception as e:
                print(f"  {service_name}: FAILED")

        await asyncio.sleep(0.5)

    # Show status of all circuit breakers
    print(f"\nFinal status of all circuit breakers:")
    status_summary = list_circuit_breakers()

    for name, status in status_summary.items():
        print(f"  {name}:")
        print(f"    State: {status['state']}")
        print(f"    Requests: {status['total_requests']}")
        print(f"    Failure rate: {status['failure_rate']:.2%}")


async def example_circuit_breaker_recovery():
    """Example: Circuit breaker recovery demonstration."""
    print("\n=== Circuit Breaker Recovery Example ===")

    # Create service that will recover over time
    class RecoveringService:
        def __init__(self):
            self.call_count = 0
            self.failure_rate = 0.8  # Start with high failure rate

        async def call(self, data=None):
            self.call_count += 1

            # Gradually improve failure rate (simulate service recovery)
            if self.call_count > 10:
                self.failure_rate = max(0.1, self.failure_rate - 0.05)

            if random.random() < self.failure_rate:
                raise Exception(f"Service failing (rate: {self.failure_rate:.1%})")

            return {"status": "success", "call_count": self.call_count}

    service = RecoveringService()
    circuit_breaker = CircuitBreakerFactory.create_fast_fail("recovering-api")

    print("Simulating service recovery over time...")

    for i in range(25):
        try:
            result = await circuit_breaker.call(service.call)
            metrics = circuit_breaker.get_metrics()
            print(
                f"Call {i+1}: SUCCESS (state: {metrics.current_state}, "
                f"failure rate: {service.failure_rate:.1%})"
            )
        except CircuitBreakerException as e:
            print(f"Call {i+1}: CIRCUIT OPEN")
        except Exception as e:
            print(f"Call {i+1}: SERVICE FAILED")

        # Show recovery progress every 5 calls
        if (i + 1) % 5 == 0:
            metrics = circuit_breaker.get_metrics()
            print(
                f"  Status after {i+1} calls: {metrics.current_state}, "
                f"success rate: {metrics.get_success_rate():.1%}"
            )

        await asyncio.sleep(0.2)

    # Final metrics
    final_metrics = circuit_breaker.get_metrics()
    print(f"\nFinal recovery status:")
    print(f"  Circuit breaker state: {final_metrics.current_state}")
    print(f"  Total requests: {final_metrics.total_requests}")
    print(f"  Success rate: {final_metrics.get_success_rate():.1%}")
    print(f"  State changes: {final_metrics.state_changes}")
    print(f"  Service failure rate: {service.failure_rate:.1%}")


async def example_circuit_breaker_manual_control():
    """Example: Manual circuit breaker control."""
    print("\n=== Manual Circuit Breaker Control Example ===")

    service = MockExternalService("manual-service", failure_rate=0.3)
    circuit_breaker = ExternalDependencyCircuitBreaker("manual-service")

    print(f"Initial state: {circuit_breaker.get_state()}")

    # Make some normal calls
    print("\n1. Normal operation:")
    for i in range(3):
        try:
            result = await circuit_breaker.call(service.call)
            print(f"  Call {i+1}: SUCCESS")
        except Exception as e:
            print(f"  Call {i+1}: FAILED - {e}")

    # Manually force circuit open
    print("\n2. Forcing circuit open:")
    await circuit_breaker.force_open()
    print(f"  State after force_open(): {circuit_breaker.get_state()}")

    try:
        await circuit_breaker.call(service.call)
        print("  Call: SUCCESS")
    except CircuitBreakerException as e:
        print(f"  Call: BLOCKED - {e}")

    # Wait a moment then force close
    await asyncio.sleep(1)
    print("\n3. Forcing circuit closed:")
    await circuit_breaker.force_close()
    print(f"  State after force_close(): {circuit_breaker.get_state()}")

    try:
        result = await circuit_breaker.call(service.call)
        print("  Call: SUCCESS")
    except Exception as e:
        print(f"  Call: FAILED - {e}")

    # Reset circuit breaker
    print("\n4. Resetting circuit breaker:")
    await circuit_breaker.reset()
    metrics = circuit_breaker.get_metrics()
    print(f"  State after reset(): {metrics.current_state}")
    print(f"  Total requests after reset: {metrics.total_requests}")


async def main():
    """Run all circuit breaker examples."""
    print("ONEX Circuit Breaker Examples")
    print("=" * 60)

    examples = [
        example_basic_circuit_breaker,
        example_circuit_breaker_with_fallback,
        example_circuit_breaker_context_manager,
        example_environment_configured_circuit_breaker,
        example_circuit_breaker_events,
        example_multiple_circuit_breakers,
        example_circuit_breaker_recovery,
        example_circuit_breaker_manual_control,
    ]

    for example in examples:
        try:
            await example()
        except Exception as e:
            print(f"Error in example {example.__name__}: {e}")

        print("-" * 40)

    print("\nAll circuit breaker examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
