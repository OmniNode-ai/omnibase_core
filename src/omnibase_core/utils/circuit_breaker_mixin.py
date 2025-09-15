"""
Circuit breaker mixin utility for ONEX nodes.

This module provides the CircuitBreakerMixin class that integrates circuit breaker
functionality into ONEX nodes using composition patterns. This enables nodes to
add circuit breaker protection for external service calls with minimal boilerplate.

Author: ONEX Framework Team
"""

import threading
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.core.resilience.circuit_breaker import (
    CircuitBreakerState,
    ExternalDependencyCircuitBreaker,
    ModelCircuitBreakerConfig,
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
        self._circuit_breakers: dict[str, ExternalDependencyCircuitBreaker] = {}
        self._circuit_breaker_configs: dict[str, ModelCircuitBreakerConfig] = {}
        # Thread safety for circuit breaker management
        self._circuit_breaker_lock = threading.RLock()

    def _setup_circuit_breakers(
        self,
        configs: dict[str, ModelCircuitBreakerConfig],
    ) -> None:
        """
        Initialize circuit breakers with the provided configurations.

        Args:
            configs: Dictionary mapping service names to circuit breaker configs
        """
        with self._circuit_breaker_lock:
            self._circuit_breaker_configs = configs.copy()
            for service_name, config in configs.items():
                cb = ExternalDependencyCircuitBreaker(service_name, config)
                self._circuit_breakers[service_name] = cb

    def _get_circuit_breaker(
        self,
        service_name: str,
    ) -> ExternalDependencyCircuitBreaker:
        """
        Get or create circuit breaker for a service.

        Args:
            service_name: Name of the service

        Returns:
            ExternalDependencyCircuitBreaker instance for the service

        Raises:
            OnexError: If service is not configured
        """
        with self._circuit_breaker_lock:
            if service_name not in self._circuit_breakers:
                # Check if we have a config for this service
                if service_name in self._circuit_breaker_configs:
                    config = self._circuit_breaker_configs[service_name]
                    cb = ExternalDependencyCircuitBreaker(service_name, config)
                    self._circuit_breakers[service_name] = cb
                else:
                    # Use default configuration
                    default_config = ModelCircuitBreakerConfig()
                    cb = ExternalDependencyCircuitBreaker(service_name, default_config)
                    self._circuit_breakers[service_name] = cb
                    self._circuit_breaker_configs[service_name] = default_config

            return self._circuit_breakers[service_name]

    async def _call_with_circuit_breaker(
        self,
        service_name: str,
        func: Callable[..., Awaitable[T]],
        *args,
        **kwargs,
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
            # Use the circuit breaker's call method
            return await circuit_breaker.call(
                lambda: func(*args, **kwargs),
            )

        except Exception as e:
            # Circuit breaker will handle the failure recording
            if isinstance(e, OnexError):
                # Re-raise OnexErrors as-is
                raise
            # Wrap other exceptions in OnexError
            raise OnexError(
                message=f"Service call failed: {service_name}",
                error_code=CoreErrorCode.OPERATION_FAILED,
                context={
                    "service_name": service_name,
                    "original_error": str(e),
                    "circuit_breaker_state": circuit_breaker.get_state().value,
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

        return self._circuit_breakers[service_name].get_state()

    def _get_circuit_breaker_metrics(self, service_name: str) -> dict[str, Any]:
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
        metrics = circuit_breaker.get_metrics()

        return {
            "state": metrics.current_state.value,
            "failure_count": metrics.failed_requests,
            "success_count": metrics.successful_requests,
            "total_requests": metrics.total_requests,
            "last_failure_time": metrics.last_failure_time,
            "last_success_time": metrics.last_success_time,
            "failure_rate": metrics.get_failure_rate(),
            "config": {
                "failure_threshold": circuit_breaker.config.failure_threshold,
                "recovery_timeout_seconds": (
                    circuit_breaker.config.recovery_timeout_seconds
                ),
                "request_timeout_seconds": (
                    circuit_breaker.config.request_timeout_seconds
                ),
            },
        }

    async def _reset_circuit_breaker(self, service_name: str) -> None:
        """
        Reset a circuit breaker to closed state.

        Args:
            service_name: Name of the service
        """
        if service_name in self._circuit_breakers:
            await self._circuit_breakers[service_name].reset()

    def _get_all_circuit_breaker_states(self) -> dict[str, dict[str, Any]]:
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
        self,
        service_name: str,
        config: ModelCircuitBreakerConfig,
    ) -> None:
        """
        Configure or update a circuit breaker for a service.

        Args:
            service_name: Name of the service
            config: Circuit breaker configuration
        """
        self._circuit_breaker_configs[service_name] = config
        self._circuit_breakers[service_name] = ExternalDependencyCircuitBreaker(
            service_name,
            config,
        )

    def _remove_circuit_breaker(self, service_name: str) -> None:
        """
        Remove a circuit breaker for a service.

        Args:
            service_name: Name of the service
        """
        self._circuit_breakers.pop(service_name, None)
        self._circuit_breaker_configs.pop(service_name, None)

    def _health_check_with_circuit_breaker(self, service_name: str) -> dict[str, Any]:
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
    recovery_timeout_seconds: int = 30,
    request_timeout_seconds: float = 10.0,
) -> ModelCircuitBreakerConfig:
    """
    Create a default circuit breaker configuration.

    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout_seconds: Timeout before attempting recovery (seconds)
        request_timeout_seconds: Timeout for individual requests (seconds)

    Returns:
        ModelCircuitBreakerConfig instance
    """
    return ModelCircuitBreakerConfig(
        failure_threshold=failure_threshold,
        recovery_timeout_seconds=recovery_timeout_seconds,
        request_timeout_seconds=request_timeout_seconds,
    )


# Convenience function for creating strict circuit breaker configs
def create_strict_circuit_breaker_config() -> ModelCircuitBreakerConfig:
    """
    Create a strict circuit breaker configuration with low failure tolerance.

    Returns:
        ModelCircuitBreakerConfig instance with strict settings
    """
    return ModelCircuitBreakerConfig(
        failure_threshold=2,
        recovery_timeout_seconds=60,
        request_timeout_seconds=5.0,
        failure_rate_threshold=0.3,
    )


# Convenience function for creating lenient circuit breaker configs
def create_lenient_circuit_breaker_config() -> ModelCircuitBreakerConfig:
    """
    Create a lenient circuit breaker configuration with high failure tolerance.

    Returns:
        ModelCircuitBreakerConfig instance with lenient settings
    """
    return ModelCircuitBreakerConfig(
        failure_threshold=10,
        recovery_timeout_seconds=15,
        request_timeout_seconds=30.0,
        failure_rate_threshold=0.8,
    )
