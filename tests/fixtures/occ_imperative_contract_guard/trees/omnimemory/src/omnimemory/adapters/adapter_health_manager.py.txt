# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Comprehensive health check manager for OmniMemory ONEX architecture.

- Aggregated health checks from all dependencies
- Async gathering with failure isolation
- Circuit breaker integration for health checks
- Performance monitoring and alerting
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Literal, cast

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

# Optional psutil import for resource metrics - gracefully degrade if unavailable
_psutil_available = False
psutil = None
try:
    import psutil  # type: ignore[import-untyped,no-redef]  # Why: psutil ships without type stubs; redef because module-level psutil=None is overwritten

    _psutil_available = True
except ImportError:
    pass

import structlog

from ..models.foundation.model_health_metadata import HealthCheckMetadata
from ..models.foundation.model_health_response import (
    ModelCircuitBreakerStats,
    ModelCircuitBreakerStatsCollection,
    ModelRateLimitedHealthCheckResponse,
)
from ..models.foundation.model_semver import ModelSemVer
from ..models.utils import (
    DependencyType,
    HealthStatus,
    ModelHealthCheckConfig,
    ModelHealthCheckDetails,
    ModelHealthCheckResult,
    ModelResourceHealthCheck,
    ModelSystemHealth,
)

# Internal aliases for code compatibility
HealthCheckConfig = ModelHealthCheckConfig
HealthCheckDetails = ModelHealthCheckDetails
HealthCheckResult = ModelHealthCheckResult
ResourceHealthCheck = ModelResourceHealthCheck
SystemHealth = ModelSystemHealth
from .adapter_error_sanitizer import SanitizationLevel, sanitize_error

# === RATE LIMITING ===


class RateLimiter:
    """Simple rate limiter for API endpoints."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in the time window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    async def is_allowed(self, identifier: str) -> bool:
        """
        Check if request is allowed for the given identifier.

        Args:
            identifier: Client identifier (IP, user ID, etc.)

        Returns:
            bool: True if request is allowed, False if rate limited
        """
        async with self._lock:
            current_time = time.time()

            # Initialize or get existing requests list
            if identifier not in self._requests:
                self._requests[identifier] = []

            requests = self._requests[identifier]

            # Remove old requests outside the window
            cutoff_time = current_time - self.window_seconds
            self._requests[identifier] = [
                req_time for req_time in requests if req_time > cutoff_time
            ]

            # Check if we can accept this request
            if len(self._requests[identifier]) >= self.max_requests:
                return False

            # Add current request
            self._requests[identifier].append(current_time)
            return True


def _sanitize_error(error: Exception) -> str:
    """
    Sanitize error messages to prevent information disclosure in logs.

    Uses the enhanced centralized error sanitizer for improved security.
    """
    return sanitize_error(
        error, context="health_check", level=SanitizationLevel.STANDARD
    )


def _get_package_version() -> ModelSemVer:
    """Get package version from metadata or fallback to default.

    Returns:
        ModelSemVer: Package version as strongly-typed semver model.
    """
    from importlib.metadata import PackageNotFoundError, version

    fallback_version = ModelSemVer(major=0, minor=1, patch=0)
    try:
        # Try to get version from package metadata
        version_str = version("omnimemory")
        return ModelSemVer.parse(version_str)
    except PackageNotFoundError:
        return fallback_version
    except Exception:
        return fallback_version


def _get_environment() -> str:
    """Detect current environment from environment variables."""
    # Check common environment variables
    env = os.getenv(
        "ENVIRONMENT", os.getenv("ENV", os.getenv("NODE_ENV", "development"))
    )

    # Normalize environment names
    if env.lower() in ("prod", "production"):
        return "production"
    elif env.lower() in ("stage", "staging"):
        return "staging"
    elif env.lower() in ("test", "testing"):
        return "testing"
    else:
        return "development"


from ..models.foundation.model_health_response import (
    ModelHealthResponse,
    ModelResourceMetrics,
)
from .adapter_concurrency import CircuitBreaker, CircuitBreakerOpenError
from .adapter_correlation_context import (
    OperationType,
    correlation_context,
    trace_operation,
)
from .adapter_resource_manager import AsyncCircuitBreaker

logger = structlog.get_logger(__name__)

# Re-export circuit breaker classes for convenient imports from health_manager
__all__ = [
    "CircuitBreaker",
    "CircuitBreakerOpenError",
    "DependencyType",
    "HealthCheckConfig",
    "HealthCheckDetails",
    "HealthCheckManager",
    "HealthCheckResult",
    "HealthManager",
    "HealthStatus",
    "RateLimiter",
    "ResourceHealthCheck",
    "SystemHealth",
    "create_pinecone_health_check",
    "create_postgresql_health_check",
    "create_redis_health_check",
    "health_manager",
]


# HealthStatus, DependencyType, HealthCheckConfig, HealthCheckResult
# are imported from ..models.utils.model_health


class HealthCheckManager:
    """
    Comprehensive health check manager for OmniMemory.

    Provides:
    - Aggregated health checks from all dependencies
    - Circuit breaker integration for resilient health checking
    - Resource monitoring and performance tracking
    - Failure isolation to prevent cascade failures
    """

    def __init__(self) -> None:
        self._health_checks: dict[str, Callable[[], Awaitable[HealthCheckResult]]] = {}
        self._configs: dict[str, HealthCheckConfig] = {}
        self._circuit_breakers: dict[str, AsyncCircuitBreaker] = {}
        self._last_results: dict[str, HealthCheckResult] = {}
        self._results_lock = asyncio.Lock()  # Prevent race conditions on metric updates
        self._rate_limiter = RateLimiter(
            max_requests=30, window_seconds=60
        )  # Rate limit health checks
        self._system_start_time = time.time()

    def register_health_check(
        self,
        config: HealthCheckConfig,
        check_func: Callable[[], Awaitable[HealthCheckResult]],
    ) -> None:
        """
        Register a health check function with configuration.

        Args:
            config: Health check configuration
            check_func: Async function that performs the health check
        """
        self._configs[config.name] = config
        self._health_checks[config.name] = check_func

        # Create circuit breaker if configured
        if config.circuit_breaker_config:
            self._circuit_breakers[config.name] = AsyncCircuitBreaker(
                config.name, config.circuit_breaker_config
            )

        logger.info(
            "health_check_registered",
            dependency_name=config.name,
            dependency_type=config.dependency_type.value,
            critical=config.critical,
        )

    async def check_single_dependency(self, name: str) -> HealthCheckResult:
        """
        Perform health check for a single dependency.

        Args:
            name: Name of the dependency to check

        Returns:
            HealthCheckResult: Result of the health check
        """
        if name not in self._health_checks:
            return HealthCheckResult(
                config=HealthCheckConfig(
                    name=name, dependency_type=DependencyType.EXTERNAL_API
                ),
                status=HealthStatus.UNKNOWN,
                latency_ms=0.0,
                error_message="Health check not registered",
            )

        config = self._configs[name]
        check_func = self._health_checks[name]

        async with correlation_context(operation=f"health_check_{name}"):
            async with trace_operation(
                f"health_check_{name}",
                OperationType.HEALTH_CHECK,
                dependency=name,
                dependency_type=config.dependency_type.value,
            ):
                start_time = time.time()

                try:
                    # Use circuit breaker if configured
                    result: HealthCheckResult
                    if name in self._circuit_breakers:
                        circuit_breaker = self._circuit_breakers[name]
                        result = cast(
                            "HealthCheckResult", await circuit_breaker.call(check_func)
                        )
                    else:
                        # Apply timeout directly
                        result = await asyncio.wait_for(
                            check_func(), timeout=config.timeout
                        )

                    # Ensure result has correct latency
                    result.latency_ms = (time.time() - start_time) * 1000

                    # Thread-safe update of results to prevent race conditions
                    async with self._results_lock:
                        self._last_results[name] = result

                    logger.debug(
                        "health_check_completed",
                        dependency_name=name,
                        status=result.status.value,
                        latency_ms=result.latency_ms,
                    )

                    return result

                except TimeoutError:
                    latency_ms = (time.time() - start_time) * 1000
                    result = HealthCheckResult(
                        config=config,
                        status=HealthStatus.TIMEOUT,
                        latency_ms=latency_ms,
                        error_message=f"Health check timeout after {config.timeout}s",
                    )

                    # Thread-safe update of results to prevent race conditions
                    async with self._results_lock:
                        self._last_results[name] = result
                    logger.warning(
                        "health_check_timeout",
                        dependency_name=name,
                        timeout=config.timeout,
                        latency_ms=latency_ms,
                    )

                    return result

                except Exception as e:
                    latency_ms = (time.time() - start_time) * 1000
                    result = HealthCheckResult(
                        config=config,
                        status=HealthStatus.UNHEALTHY,
                        latency_ms=latency_ms,
                        error_message=_sanitize_error(e),
                    )

                    # Thread-safe update of results to prevent race conditions
                    async with self._results_lock:
                        self._last_results[name] = result
                    logger.error(
                        "health_check_failed",
                        dependency_name=name,
                        error=_sanitize_error(e),
                        error_type=type(e).__name__,
                        latency_ms=latency_ms,
                    )

                    return result

    async def check_all_dependencies(self) -> list[HealthCheckResult]:
        """
        Perform health checks for all registered dependencies.

        Uses asyncio.gather with return_exceptions=True to ensure
        individual dependency failures don't crash the overall health check.

        Returns:
            list[HealthCheckResult]: Results for all dependencies
        """
        if not self._health_checks:
            return []

        async with correlation_context(operation="health_check_all"):
            async with trace_operation(
                "health_check_all",
                OperationType.HEALTH_CHECK,
                dependency_count=len(self._health_checks),
            ):
                # Use asyncio.gather with return_exceptions=True for failure isolation
                tasks = [
                    self.check_single_dependency(name)
                    for name in self._health_checks.keys()
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results and handle exceptions
                health_results: list[HealthCheckResult] = []
                for i, result in enumerate(results):
                    dependency_name = list(self._health_checks.keys())[i]

                    if isinstance(result, BaseException):
                        # Create error result for exceptions
                        config = self._configs[dependency_name]

                        # Sanitize exception before including in result to prevent
                        # sensitive data leakage (connection strings, credentials, etc.)
                        error_to_sanitize = (
                            result
                            if isinstance(result, Exception)
                            else Exception(str(result))
                        )
                        sanitized_error = _sanitize_error(error_to_sanitize)

                        error_result = HealthCheckResult(
                            config=config,
                            status=HealthStatus.UNHEALTHY,
                            latency_ms=0.0,
                            error_message=f"Health check exception: {sanitized_error}",
                        )
                        health_results.append(error_result)

                        logger.error(
                            "health_check_gather_exception",
                            dependency_name=dependency_name,
                            error=sanitized_error,
                            error_type=type(result).__name__,
                        )
                    else:
                        # Result is HealthCheckResult (type narrowed by isinstance check)
                        health_results.append(result)

                logger.info(
                    "health_check_all_completed",
                    total_dependencies=len(health_results),
                    healthy_count=len(
                        [r for r in health_results if r.status == HealthStatus.HEALTHY]
                    ),
                    degraded_count=len(
                        [r for r in health_results if r.status == HealthStatus.DEGRADED]
                    ),
                    unhealthy_count=len(
                        [
                            r
                            for r in health_results
                            if r.status == HealthStatus.UNHEALTHY
                        ]
                    ),
                )

                return health_results

    def get_resource_metrics(self) -> ModelResourceMetrics:
        """Get current system resource metrics.

        Returns default metrics if psutil is unavailable or any error occurs.
        """
        # Check if psutil is available
        if not _psutil_available or psutil is None:
            logger.debug(
                "resource_metrics_unavailable",
                reason="psutil_not_installed",
            )
            return ModelResourceMetrics(
                cpu_usage_percent=0.0,
                memory_usage_mb=0.0,
                memory_usage_percent=0.0,
                disk_usage_percent=0.0,
                network_throughput_mbps=0.0,
            )

        try:
            # Get CPU usage (use interval=None for non-blocking call that returns
            # cached value since last call - acceptable for health checks)
            cpu_percent = psutil.cpu_percent(interval=None)

            # Get memory usage
            memory = psutil.virtual_memory()
            memory_mb = memory.used / 1024 / 1024

            # Get disk usage for root/system partition (platform-agnostic)
            disk_path = "/" if sys.platform != "win32" else "C:\\"
            disk = psutil.disk_usage(disk_path)
            disk_percent = disk.percent

            # Get network stats (simplified)
            network_stats = psutil.net_io_counters()
            # Simple approximation of throughput (bytes per second converted to Mbps)
            network_mbps = (
                (network_stats.bytes_sent + network_stats.bytes_recv) / 1024 / 1024 * 8
            )

            return ModelResourceMetrics(
                cpu_usage_percent=cpu_percent,
                memory_usage_mb=memory_mb,
                memory_usage_percent=memory.percent,
                disk_usage_percent=disk_percent,
                network_throughput_mbps=network_mbps,
            )

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
            psutil.Error,
            OSError,
            AttributeError,
        ) as e:
            # Handle specific psutil exceptions gracefully:
            # - NoSuchProcess: process terminated
            # - AccessDenied: insufficient permissions
            # - ZombieProcess: process is zombie state
            # - Error: base psutil exception
            # - OSError: OS-level errors
            # - AttributeError: corrupted psutil module
            logger.warning(
                "resource_metrics_psutil_error",
                error=_sanitize_error(e),
                error_type=type(e).__name__,
            )
            return ModelResourceMetrics(
                cpu_usage_percent=0.0,
                memory_usage_mb=0.0,
                memory_usage_percent=0.0,
                disk_usage_percent=0.0,
                network_throughput_mbps=0.0,
            )
        except Exception as e:
            logger.error(
                "resource_metrics_error",
                error=_sanitize_error(e),
                error_type=type(e).__name__,
            )
            # Return default metrics on error
            return ModelResourceMetrics(
                cpu_usage_percent=0.0,
                memory_usage_mb=0.0,
                memory_usage_percent=0.0,
                disk_usage_percent=0.0,
                network_throughput_mbps=0.0,
            )

    def calculate_overall_status(
        self, results: list[HealthCheckResult]
    ) -> HealthStatus:
        """
        Calculate overall system health based on dependency results.

        Properly categorizes all HealthStatus values:
        - Unhealthy: UNHEALTHY, TIMEOUT, CIRCUIT_OPEN, UNKNOWN
        - Degraded: DEGRADED, RATE_LIMITED

        Args:
            results: List of health check results

        Returns:
            HealthStatus: Overall system health status
        """
        if not results:
            return HealthStatus.UNKNOWN

        critical_results = [r for r in results if r.config.critical]
        non_critical_results = [r for r in results if not r.config.critical]

        # Define status categories - properly map all HealthStatus values
        unhealthy_statuses = {
            HealthStatus.UNHEALTHY,
            HealthStatus.TIMEOUT,
            HealthStatus.CIRCUIT_OPEN,
            HealthStatus.UNKNOWN,
        }
        degraded_statuses = {
            HealthStatus.DEGRADED,
            HealthStatus.RATE_LIMITED,
        }

        # Check critical dependencies
        critical_unhealthy = [
            r for r in critical_results if r.status in unhealthy_statuses
        ]
        critical_degraded = [
            r for r in critical_results if r.status in degraded_statuses
        ]

        # If any critical dependency is unhealthy, system is unhealthy
        if critical_unhealthy:
            return HealthStatus.UNHEALTHY

        # If any critical dependency is degraded, system is degraded
        if critical_degraded:
            return HealthStatus.DEGRADED

        # Check non-critical dependencies for degradation signals
        non_critical_unhealthy = [
            r for r in non_critical_results if r.status in unhealthy_statuses
        ]

        # If majority of non-critical deps are unhealthy, system is degraded
        if (
            non_critical_results
            and len(non_critical_unhealthy) > len(non_critical_results) / 2
        ):
            return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY

    async def get_comprehensive_health(self) -> ModelHealthResponse:
        """
        Get comprehensive health response including all dependencies and metrics.

        Returns:
            ModelHealthResponse: Complete health check response
        """
        start_time = time.time()

        async with correlation_context(operation="comprehensive_health_check"):
            # Get all dependency health results
            dependency_results = await self.check_all_dependencies()

            # Calculate overall status
            overall_status = self.calculate_overall_status(dependency_results)

            # Get resource metrics
            resource_metrics = self.get_resource_metrics()

            # Calculate uptime
            uptime_seconds = int(time.time() - self._system_start_time)

            # Calculate total latency
            total_latency_ms = (time.time() - start_time) * 1000

            # Convert results to dependency status objects
            dependencies = [
                result.to_dependency_status() for result in dependency_results
            ]

            # Map HealthStatus to the expected Literal type
            status_map: dict[
                HealthStatus, Literal["healthy", "degraded", "unhealthy"]
            ] = {
                HealthStatus.HEALTHY: "healthy",
                HealthStatus.DEGRADED: "degraded",
                HealthStatus.UNHEALTHY: "unhealthy",
                HealthStatus.UNKNOWN: "unhealthy",
                HealthStatus.TIMEOUT: "unhealthy",
                HealthStatus.RATE_LIMITED: "degraded",
                HealthStatus.CIRCUIT_OPEN: "degraded",
            }
            mapped_status = status_map.get(overall_status, "unhealthy")

            response = ModelHealthResponse(
                status=mapped_status,
                latency_ms=total_latency_ms,
                timestamp=datetime.now(timezone.utc),
                resource_usage=resource_metrics,
                dependencies=dependencies,
                uptime_seconds=uptime_seconds,
                version=_get_package_version(),
                environment=_get_environment(),
            )

            logger.info(
                "comprehensive_health_completed",
                overall_status=overall_status.value,
                dependency_count=len(dependencies),
                latency_ms=total_latency_ms,
                uptime_seconds=uptime_seconds,
            )

            return response

    def get_circuit_breaker_stats(self) -> ModelCircuitBreakerStatsCollection:
        """Get circuit breaker statistics for all dependencies."""
        stats = {}
        for name, circuit_breaker in self._circuit_breakers.items():
            stats[name] = ModelCircuitBreakerStats(
                state=circuit_breaker.state.value,
                failure_count=circuit_breaker.stats.failure_count,
                success_count=circuit_breaker.stats.success_count,
                total_calls=circuit_breaker.stats.total_calls,
                total_timeouts=circuit_breaker.stats.total_timeouts,
                last_failure_time=circuit_breaker.stats.last_failure_time,
                state_changed_at=circuit_breaker.stats.state_changed_at,
            )
        return ModelCircuitBreakerStatsCollection(circuit_breakers=stats)

    async def rate_limited_health_check(
        self, client_identifier: str
    ) -> ModelRateLimitedHealthCheckResponse:
        """
        Rate-limited health check endpoint for API exposure.

        Args:
            client_identifier: Client identifier (IP address, API key, etc.)

        Returns:
            Rate-limited health check response with proper typing
        """
        # Check rate limit
        if not await self._rate_limiter.is_allowed(client_identifier):
            return ModelRateLimitedHealthCheckResponse(
                health_check=None,
                rate_limited=True,
                error_message=f"Rate limit exceeded for client: {client_identifier}",
                rate_limit_reset_time=None,  # Could be calculated from rate limiter
                remaining_requests=0,
            )

        # Perform health check
        health_check_result = await self.get_comprehensive_health()
        return ModelRateLimitedHealthCheckResponse(
            health_check=health_check_result,
            rate_limited=False,
            rate_limit_reset_time=None,
            remaining_requests=None,
        )


# Global health manager instance
health_manager = HealthCheckManager()


# Convenience functions for registering common health checks
async def create_postgresql_health_check(
    connection_string: str,
) -> Callable[[], Awaitable[HealthCheckResult]]:
    """Create a PostgreSQL health check function."""

    async def check_postgresql() -> HealthCheckResult:
        import asyncpg  # transport-import-ok: health manager probes asyncpg connectivity directly (infra boundary), OMN-13283

        config = HealthCheckConfig(
            name="postgresql", dependency_type=DependencyType.DATABASE
        )

        try:
            conn = await asyncpg.connect(connection_string, timeout=5)
            await conn.execute("SELECT 1")
            await conn.close()

            return HealthCheckResult(
                config=config,
                status=HealthStatus.HEALTHY,
                latency_ms=0.0,  # Will be set by the manager
            )
        except Exception as e:
            return HealthCheckResult(
                config=config,
                status=HealthStatus.UNHEALTHY,
                latency_ms=0.0,
                error_message=_sanitize_error(e),
            )

    return check_postgresql


async def create_redis_health_check(
    redis_url: str,
) -> Callable[[], Awaitable[HealthCheckResult]]:
    """Create a Redis health check function."""

    async def check_redis() -> HealthCheckResult:
        import redis.asyncio as redis  # transport-import-ok: health manager probes redis connectivity directly (infra boundary), OMN-13283

        config = HealthCheckConfig(name="redis", dependency_type=DependencyType.CACHE)

        try:
            redis_from_url = cast("Callable[[str], redis.Redis]", redis.from_url)
            client: redis.Redis = redis_from_url(redis_url)
            await client.ping()
            await client.close()

            return HealthCheckResult(
                config=config, status=HealthStatus.HEALTHY, latency_ms=0.0
            )
        except Exception as e:
            return HealthCheckResult(
                config=config,
                status=HealthStatus.UNHEALTHY,
                latency_ms=0.0,
                error_message=_sanitize_error(e),
            )

    return check_redis


async def create_pinecone_health_check(
    api_key: str | None = None, environment: str | None = None
) -> Callable[[], Awaitable[HealthCheckResult]]:
    """Create a Pinecone health check function.

    Note: Modern Pinecone SDK (v3+) determines region from the API key,
    so the environment parameter is only used for metadata/logging purposes.

    Uses PineconeAsyncio for native async if available, otherwise falls back
    to run_in_executor to avoid blocking the event loop.

    Args:
        api_key: Pinecone API key. If None, check returns UNKNOWN status.
        environment: Optional environment identifier for metadata. Not required
            by Pinecone SDK v3+ but useful for logging/tracking.

    Returns:
        Async function that performs Pinecone health check.
    """

    async def check_pinecone() -> HealthCheckResult:
        config = HealthCheckConfig(
            name="pinecone", dependency_type=DependencyType.VECTOR_DB
        )

        # If API key not configured, return UNKNOWN status
        if not api_key:
            return HealthCheckResult(
                config=config,
                status=HealthStatus.UNKNOWN,
                latency_ms=0.0,
                error_message="Pinecone not configured (missing api_key)",
            )

        # Attempt to import Pinecone client - try async first, then sync
        pinecone_async_available = False
        PineconeAsyncio = None
        try:
            # PineconeAsyncio may not exist in all SDK versions
            from pinecone import (
                PineconeAsyncio as _PineconeAsyncio,  # pyright: ignore[reportAttributeAccessIssue]
            )

            PineconeAsyncio = _PineconeAsyncio
            pinecone_async_available = True
        except ImportError:
            pass

        try:
            from pinecone import Pinecone
        except ImportError:
            return HealthCheckResult(
                config=config,
                status=HealthStatus.UNKNOWN,
                latency_ms=0.0,
                error_message="Pinecone client library not installed",
            )

        # Perform actual health check by calling Pinecone API
        start_time = time.time()
        index_count = 0
        try:
            if pinecone_async_available and PineconeAsyncio is not None:
                # Use native async client for non-blocking I/O
                pc_async = PineconeAsyncio(api_key=api_key)
                try:
                    indexes = await pc_async.list_indexes()
                    # Get index count - handle different SDK versions
                    if hasattr(indexes, "names"):
                        index_count = len(indexes.names())
                    elif hasattr(indexes, "__len__"):
                        index_count = len(indexes)
                finally:
                    # Cleanup async client resources
                    if hasattr(pc_async, "close"):
                        await pc_async.close()
            else:
                # Fall back to synchronous client with run_in_executor
                # to avoid blocking the event loop
                loop = asyncio.get_running_loop()
                pc = Pinecone(api_key=api_key)

                def _sync_list_indexes() -> int:
                    result = pc.list_indexes()
                    if result and hasattr(result, "names"):
                        return len(result.names())
                    elif result and hasattr(result, "__len__"):
                        return len(result)
                    return 0

                index_count = await loop.run_in_executor(None, _sync_list_indexes)

            latency_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                config=config,
                status=HealthStatus.HEALTHY,
                latency_ms=latency_ms,
                metadata=HealthCheckMetadata(
                    connection_url=f"pinecone://{environment or 'default'}",
                    performance_metrics={"index_count": float(index_count)},
                ),
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                config=config,
                status=HealthStatus.UNHEALTHY,
                latency_ms=latency_ms,
                error_message=_sanitize_error(e),
            )

    return check_pinecone


# Type alias for health check result values - replaces dict[str, Any]
HealthCheckResultValue = str | int | float | bool | None
HealthCheckResultDict = dict[str, HealthCheckResultValue]


# === TEST-COMPATIBLE INTERFACES ===
# HealthCheckDetails, ResourceHealthCheck, and SystemHealth
# are imported from ..models.utils.model_health


class HealthManager:
    """
    Health manager with test-compatible interface.

    Provides:
    - Health check registration and execution
    - Circuit breaker integration
    - Rate limiting for health checks
    - System-wide health aggregation
    """

    def __init__(
        self,
        default_timeout: float = 5.0,
        rate_limit_window: float = 60.0,
        max_checks_per_window: int = 100,
    ):
        """
        Initialize health manager.

        Args:
            default_timeout: Default timeout for health checks in seconds
            rate_limit_window: Time window for rate limiting in seconds
            max_checks_per_window: Maximum health checks per window
        """
        self.default_timeout = default_timeout
        self.rate_limit_window = rate_limit_window
        self.max_checks_per_window = max_checks_per_window

        self.health_checks: dict[str, Callable[[], Awaitable[HealthCheckResult]]] = {}
        self.circuit_breakers: dict[str, AsyncCircuitBreaker] = {}
        self._check_counts: dict[str, list[float]] = {}
        self._rate_limiter = RateLimiter(
            max_requests=max_checks_per_window, window_seconds=int(rate_limit_window)
        )

    def register_health_check(
        self, name: str, check_func: Callable[[], Awaitable[HealthCheckResult]]
    ) -> None:
        """
        Register a health check function.

        Args:
            name: Name of the resource to check
            check_func: Async function that performs the health check
        """
        self.health_checks[name] = check_func
        self._check_counts[name] = []
        logger.info("health_check_registered", resource_name=name)

    async def check_resource_health(
        self, name: str, correlation_id: str | None = None
    ) -> ResourceHealthCheck:
        """
        Check health of a specific resource.

        Args:
            name: Name of the resource to check
            correlation_id: Optional correlation ID for tracking

        Returns:
            ResourceHealthCheck: Result of the health check
        """
        # Check rate limiting
        current_time = time.time()
        if name in self._check_counts:
            # Clean old entries
            cutoff = current_time - self.rate_limit_window
            self._check_counts[name] = [
                t for t in self._check_counts[name] if t > cutoff
            ]
            if len(self._check_counts[name]) >= self.max_checks_per_window:
                remaining = 0
                reset_time = cutoff + self.rate_limit_window
                return ResourceHealthCheck(
                    status=HealthStatus.RATE_LIMITED,
                    response_time=0.0,
                    details=HealthCheckDetails(
                        message="Rate limit exceeded",
                        rate_limit_active=True,
                        rate_limit_remaining=remaining,
                        rate_limit_reset_time=reset_time,
                        result_type="rate_limited",
                    ),
                    correlation_id=correlation_id,
                )
            self._check_counts[name].append(current_time)

        # Check circuit breaker
        if name in self.circuit_breakers:
            cb = self.circuit_breakers[name]
            # Check if circuit is open by comparing state value (string)
            # This supports both CircuitState (resource_manager) and
            # CircuitBreakerState (concurrency) enums since both use
            # the same string values ("open", "closed", "half_open")
            if hasattr(cb, "state"):
                state_value = getattr(cb.state, "value", str(cb.state))
                if state_value == "open":
                    failure_count = getattr(cb, "failure_count", None)
                    return ResourceHealthCheck(
                        status=HealthStatus.CIRCUIT_OPEN,
                        response_time=0.0,
                        details=HealthCheckDetails(
                            message="Circuit breaker is open",
                            circuit_open=True,
                            circuit_state=state_value,
                            circuit_failure_count=failure_count,
                            result_type="circuit_open",
                        ),
                        correlation_id=correlation_id,
                    )

        if name not in self.health_checks:
            return ResourceHealthCheck(
                status=HealthStatus.UNKNOWN,
                response_time=0.0,
                details=HealthCheckDetails(
                    error=f"Health check not registered: {name}", result_type="unknown"
                ),
                correlation_id=correlation_id,
            )

        check_func = self.health_checks[name]
        start_time = time.time()

        try:
            result = await asyncio.wait_for(check_func(), timeout=self.default_timeout)
            response_time = time.time() - start_time

            # Record success on circuit breaker (if it has record_success method)
            if name in self.circuit_breakers:
                cb = self.circuit_breakers[name]
                record_success_fn = getattr(cb, "record_success", None)
                if callable(record_success_fn):
                    record_success_fn()

            # Convert result to HealthCheckDetails
            if isinstance(result, HealthCheckDetails):
                details = result
            elif isinstance(result, dict):
                # Extract known fields from dict, put rest in extra
                known_fields = {
                    "message",
                    "error",
                    "version",
                    "connection_url",
                    "last_check",
                    "latency_ms",
                }
                extra = {k: str(v) for k, v in result.items() if k not in known_fields}
                details = HealthCheckDetails(
                    message=result.get("message") or result.get("status"),
                    version=result.get("version"),
                    latency_ms=response_time * 1000,
                    result_type="success",
                    extra=extra,
                )
            else:
                details = HealthCheckDetails(
                    message=str(result),
                    latency_ms=response_time * 1000,
                    result_type="success",
                )

            return ResourceHealthCheck(
                status=HealthStatus.HEALTHY,
                response_time=response_time,
                details=details,
                correlation_id=correlation_id,
            )

        except TimeoutError:
            response_time = time.time() - start_time
            return ResourceHealthCheck(
                status=HealthStatus.TIMEOUT,
                response_time=response_time,
                details=HealthCheckDetails(
                    error=f"Health check timed out after {self.default_timeout}s",
                    latency_ms=response_time * 1000,
                    result_type="timeout",
                ),
                correlation_id=correlation_id,
            )

        except Exception as e:
            response_time = time.time() - start_time

            # Record failure on circuit breaker (if it has record_failure method)
            if name in self.circuit_breakers:
                cb = self.circuit_breakers[name]
                record_failure_fn = getattr(cb, "record_failure", None)
                if callable(record_failure_fn):
                    record_failure_fn()

            return ResourceHealthCheck(
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                details=HealthCheckDetails(
                    error=_sanitize_error(e),
                    latency_ms=response_time * 1000,
                    result_type="error",
                ),
                correlation_id=correlation_id,
            )

    async def check_multiple_resources(
        self, names: list[str]
    ) -> dict[str, ResourceHealthCheck]:
        """
        Check health of multiple resources in parallel.

        Args:
            names: List of resource names to check

        Returns:
            dict mapping resource names to health check results
        """
        tasks = [self.check_resource_health(name) for name in names]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            name: (
                result
                if isinstance(result, ResourceHealthCheck)
                else ResourceHealthCheck(
                    status=HealthStatus.UNHEALTHY,
                    details=HealthCheckDetails(
                        error=(
                            _sanitize_error(result)
                            if isinstance(result, Exception)
                            else "Unknown error"
                        ),
                        result_type="error",
                    ),
                )
            )
            for name, result in zip(names, results, strict=True)
        }

    async def get_system_health(self) -> SystemHealth:
        """
        Get overall system health by checking all registered resources.

        Properly categorizes all HealthStatus values:
        - Unhealthy: UNHEALTHY, TIMEOUT, CIRCUIT_OPEN, UNKNOWN
        - Degraded: DEGRADED, RATE_LIMITED

        Returns:
            SystemHealth: Overall system health status
        """
        if not self.health_checks:
            return SystemHealth(
                overall_status=HealthStatus.HEALTHY, resource_statuses={}
            )

        resource_statuses = await self.check_multiple_resources(
            list(self.health_checks.keys())
        )

        # Determine overall status with proper categorization
        statuses = [r.status for r in resource_statuses.values()]

        # Define status categories
        unhealthy_statuses = {
            HealthStatus.UNHEALTHY,
            HealthStatus.TIMEOUT,
            HealthStatus.CIRCUIT_OPEN,
            HealthStatus.UNKNOWN,
        }
        degraded_statuses = {
            HealthStatus.DEGRADED,
            HealthStatus.RATE_LIMITED,
        }

        if all(s == HealthStatus.HEALTHY for s in statuses):
            overall_status = HealthStatus.HEALTHY
        elif any(s in unhealthy_statuses for s in statuses):
            # Any unhealthy status (UNHEALTHY, TIMEOUT, CIRCUIT_OPEN, UNKNOWN)
            overall_status = HealthStatus.UNHEALTHY
        elif any(s in degraded_statuses for s in statuses):
            # Degraded statuses only (DEGRADED, RATE_LIMITED)
            overall_status = HealthStatus.DEGRADED
        else:
            # Fallback to degraded for any unknown statuses
            overall_status = HealthStatus.DEGRADED

        return SystemHealth(
            overall_status=overall_status, resource_statuses=resource_statuses
        )

    def get_circuit_breaker_stats(self) -> ModelCircuitBreakerStatsCollection:
        """
        Get statistics for all circuit breakers.

        Returns:
            ModelCircuitBreakerStatsCollection: Circuit breaker statistics
        """
        stats: dict[str, ModelCircuitBreakerStats] = {}
        for name, cb in self.circuit_breakers.items():
            state = getattr(cb, "state", None)
            # Map state to expected Literal type
            if state is None:
                state_str = "closed"
            elif hasattr(state, "value"):
                state_str = str(state.value)
            else:
                state_str = str(state)
            state_literal: Literal["closed", "open", "half_open"]
            if state_str in ("closed", "open", "half_open"):
                state_literal = cast(
                    'Literal["closed", "open", "half_open"]', state_str
                )
            else:
                state_literal = "closed"  # Default to closed for unknown states

            # Get state_changed_at with fallback to current time
            state_changed_at = getattr(cb, "state_changed_at", None)
            if not isinstance(state_changed_at, datetime):
                state_changed_at = datetime.now(timezone.utc)

            stats[name] = ModelCircuitBreakerStats(
                state=state_literal,
                failure_count=getattr(cb, "failure_count", 0),
                success_count=getattr(cb, "success_count", 0),
                total_calls=getattr(cb, "total_calls", 0),
                total_timeouts=getattr(cb, "total_timeouts", 0),
                last_failure_time=getattr(cb, "last_failure_time", None),
                state_changed_at=state_changed_at,
            )

        return ModelCircuitBreakerStatsCollection(circuit_breakers=stats)

    def get_rate_limited_health_response(self) -> ModelRateLimitedHealthCheckResponse:
        """
        Get a rate-limited health response.

        Returns:
            ModelRateLimitedHealthCheckResponse: Rate limited response
        """
        return ModelRateLimitedHealthCheckResponse(
            status="rate_limited",
            message="Health check rate limited",
            details={
                "retry_after": self.rate_limit_window,
                "current_window_requests": sum(
                    len(counts) for counts in self._check_counts.values()
                ),
            },
            health_check=None,
            rate_limited=True,
            rate_limit_reset_time=None,
            remaining_requests=0,
        )

    def _sanitize_error(self, error: Exception) -> str:
        """
        Sanitize error message to remove sensitive information.

        Uses the shared centralized error sanitizer for consistent security handling
        across all modules.

        Args:
            error: Exception to sanitize

        Returns:
            Sanitized error message
        """
        # Delegate to the module-level function which uses the shared error_sanitizer
        return _sanitize_error(error)

    async def cleanup(self) -> None:
        """Clean up all health manager resources."""
        self.health_checks.clear()
        self.circuit_breakers.clear()
        self._check_counts.clear()
        logger.info("health_manager_cleanup_completed")
