#!/usr/bin/env python3
"""
Circuit breaker mixin utility for ONEX nodes.

This module provides the CircuitBreakerMixin class that integrates circuit breaker
functionality into ONEX nodes using composition patterns. This enables nodes to
add circuit breaker protection for external service calls with minimal boilerplate.

Author: ONEX Framework Team
"""

from typing import Any, Awaitable, Callable, Dict, Optional, TypeVar

from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.core.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerState,
)

T = TypeVar("T")


class CircuitBreakerMixin:
    """
    Mixin class that provides circuit breaker functionality to ONEX nodes.

    This mixin adds circuit breaker management capabilities to any class,
    allowing easy protection of external service calls with configurable
    failure thresholds and recovery timeouts.

    Usage:
        class MyNode(NodeCoreBase, CircuitBreakerMixin):
            def __init__(self, container):
                super().__init__(container)
                self._setup_circuit_breakers({
                    'external_api': CircuitBreakerConfig(
                        failure_threshold=5,
                        recovery_timeout=30
                    )
                })

            async def call_external_api(self, data):
                return await self._call_with_circuit_breaker(
                    'external_api',
                    self._make_api_call,
                    data
                )
    """

    def __init__(self, *args, **kwargs):
        """Initialize the mixin (called by multiple inheritance)."""
        super().__init__(*args, **kwargs)
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._circuit_breaker_configs: Dict[str, CircuitBreakerConfig] = {}

    def _setup_circuit_breakers(self, configs: Dict[str, CircuitBreakerConfig]) -> None:
        """
        Initialize circuit breakers with the provided configurations.

        Args:
            configs: Dictionary mapping service names to circuit breaker configs
        """
        self._circuit_breaker_configs = configs.copy()
        for service_name, config in configs.items():
            self._circuit_breakers[service_name] = CircuitBreaker(config)

    def _get_circuit_breaker(self, service_name: str) -> CircuitBreaker:
        """
        Get or create circuit breaker for a service.

        Args:
            service_name: Name of the service

        Returns:
            CircuitBreaker instance for the service

        Raises:
            OnexError: If service is not configured
        """
        if service_name not in self._circuit_breakers:
            # Check if we have a config for this service
            if service_name in self._circuit_breaker_configs:
                config = self._circuit_breaker_configs[service_name]
                self._circuit_breakers[service_name] = CircuitBreaker(config)
            else:
                # Use default configuration
                default_config = CircuitBreakerConfig()
                self._circuit_breakers[service_name] = CircuitBreaker(default_config)
                self._circuit_breaker_configs[service_name] = default_config

        return self._circuit_breakers[service_name]

    async def _call_with_circuit_breaker(
        self, service_name: str, func: Callable[..., Awaitable[T]], *args, **kwargs
    ) -> T:
        """
        Execute a function with circuit breaker protection.

        Args:
            service_name: Name of the service (for circuit breaker identification)
            func: Async function to execute
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            Result from the function call

        Raises:
            OnexError: If circuit breaker is open or function execution fails
        """
        circuit_breaker = self._get_circuit_breaker(service_name)

        try:
            # Check if circuit breaker allows the call
            async with circuit_breaker.call() as call_context:
                result = await func(*args, **kwargs)
                # If we get here, the call succeeded
                return result

        except Exception as e:
            # Circuit breaker will handle the failure recording
            if isinstance(e, OnexError):
                # Re-raise OnexErrors as-is
                raise
            else:
                # Wrap other exceptions in OnexError
                raise OnexError(
                    message=f"Service call failed: {service_name}",
                    error_code=CoreErrorCode.OPERATION_FAILED,
                    context={
                        "service_name": service_name,
                        "original_error": str(e),
                        "circuit_breaker_state": circuit_breaker.state.value,
                    },
                ) from e

    def _get_circuit_breaker_state(self, service_name: str) -> CircuitBreakerState:
        """
        Get the current state of a circuit breaker.

        Args:
            service_name: Name of the service

        Returns:
            Current circuit breaker state
        """
        if service_name not in self._circuit_breakers:
            return CircuitBreakerState.CLOSED  # Default state for non-existent breakers

        return self._circuit_breakers[service_name].state

    def _get_circuit_breaker_metrics(self, service_name: str) -> Dict[str, Any]:
        """
        Get metrics for a circuit breaker.

        Args:
            service_name: Name of the service

        Returns:
            Dictionary containing circuit breaker metrics
        """
        if service_name not in self._circuit_breakers:
            return {
                "state": "not_configured",
                "failure_count": 0,
                "success_count": 0,
                "last_failure_time": None,
            }

        circuit_breaker = self._circuit_breakers[service_name]

        return {
            "state": circuit_breaker.state.value,
            "failure_count": circuit_breaker.failure_count,
            "success_count": circuit_breaker.success_count,
            "last_failure_time": circuit_breaker.last_failure_time,
            "config": {
                "failure_threshold": circuit_breaker.config.failure_threshold,
                "recovery_timeout": circuit_breaker.config.recovery_timeout,
                "expected_recovery_time": circuit_breaker.config.expected_recovery_time,
            },
        }

    def _reset_circuit_breaker(self, service_name: str) -> None:
        """
        Reset a circuit breaker to closed state.

        Args:
            service_name: Name of the service
        """
        if service_name in self._circuit_breakers:
            self._circuit_breakers[service_name].reset()

    def _get_all_circuit_breaker_states(self) -> Dict[str, Dict[str, Any]]:
        """
        Get states and metrics for all configured circuit breakers.

        Returns:
            Dictionary mapping service names to their circuit breaker metrics
        """
        states = {}
        for service_name in self._circuit_breakers:
            states[service_name] = self._get_circuit_breaker_metrics(service_name)
        return states

    def _configure_circuit_breaker(
        self, service_name: str, config: CircuitBreakerConfig
    ) -> None:
        """
        Configure or update a circuit breaker for a service.

        Args:
            service_name: Name of the service
            config: Circuit breaker configuration
        """
        self._circuit_breaker_configs[service_name] = config
        self._circuit_breakers[service_name] = CircuitBreaker(config)

    def _remove_circuit_breaker(self, service_name: str) -> None:
        """
        Remove a circuit breaker for a service.

        Args:
            service_name: Name of the service
        """
        self._circuit_breakers.pop(service_name, None)
        self._circuit_breaker_configs.pop(service_name, None)

    def _health_check_with_circuit_breaker(self, service_name: str) -> Dict[str, Any]:
        """
        Perform health check including circuit breaker state.

        Args:
            service_name: Name of the service

        Returns:
            Health check results including circuit breaker status
        """
        circuit_state = self._get_circuit_breaker_state(service_name)
        metrics = self._get_circuit_breaker_metrics(service_name)

        # Determine overall health based on circuit breaker state
        if circuit_state == CircuitBreakerState.CLOSED:
            health_status = "healthy"
        elif circuit_state == CircuitBreakerState.HALF_OPEN:
            health_status = "recovering"
        else:  # OPEN
            health_status = "unhealthy"

        return {
            "service_name": service_name,
            "health_status": health_status,
            "circuit_breaker": {"state": circuit_state.value, "metrics": metrics},
        }


# Convenience function for creating default circuit breaker configs
def create_default_circuit_breaker_config(
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
    expected_recovery_time: float = 10.0,
) -> CircuitBreakerConfig:
    """
    Create a default circuit breaker configuration.

    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Timeout before attempting recovery (seconds)
        expected_recovery_time: Expected time for service recovery (seconds)

    Returns:
        CircuitBreakerConfig instance
    """
    return CircuitBreakerConfig(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        expected_recovery_time=expected_recovery_time,
    )


# Convenience function for creating strict circuit breaker configs
def create_strict_circuit_breaker_config() -> CircuitBreakerConfig:
    """
    Create a strict circuit breaker configuration with low failure tolerance.

    Returns:
        CircuitBreakerConfig instance with strict settings
    """
    return CircuitBreakerConfig(
        failure_threshold=2, recovery_timeout=60.0, expected_recovery_time=30.0
    )


# Convenience function for creating lenient circuit breaker configs
def create_lenient_circuit_breaker_config() -> CircuitBreakerConfig:
    """
    Create a lenient circuit breaker configuration with high failure tolerance.

    Returns:
        CircuitBreakerConfig instance with lenient settings
    """
    return CircuitBreakerConfig(
        failure_threshold=10, recovery_timeout=15.0, expected_recovery_time=5.0
    )
