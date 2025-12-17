from typing import TYPE_CHECKING, Any, TypeVar, cast

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict
from omnibase_core.types.typed_dict_performance_checkpoint_result import (
    TypedDictPerformanceCheckpointResult,
)

if TYPE_CHECKING:
    from omnibase_core.protocols.compute.protocol_performance_monitor import (
        ProtocolPerformanceMonitor,
    )

"""
Model ONEX Dependency Injection Container.

This module provides the ModelONEXContainer that integrates with
the contract-driven architecture, supporting workflow orchestration
and observable dependency injection.

"""

import asyncio
import os
import tempfile
import time
from pathlib import Path

# Import needed for type annotations
from uuid import UUID, uuid4

# Import context-based container management
from omnibase_core.context.application_context import (
    get_current_container,
    set_current_container,
)
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.configuration.model_compute_cache_config import (
    ModelComputeCacheConfig,
)

# Optional performance enhancements
try:
    from omnibase_core.cache.memory_mapped_tool_cache import MemoryMappedToolCache
except ImportError:
    # FALLBACK_REASON: cache module is optional performance enhancement,
    # system can operate without it using standard container behavior
    MemoryMappedToolCache = None

try:
    from omnibase_core.monitoring.performance_monitor import PerformanceMonitor
except ImportError:
    # FALLBACK_REASON: performance monitoring is optional feature,
    # container can function without monitoring capabilities
    PerformanceMonitor = None

# Type aliases for protocols not yet implemented in omnibase_core
# Future: import from omnibase_core.protocols once implemented
ProtocolDatabaseConnection = Any
ProtocolServiceDiscovery = Any

T = TypeVar("T")

# === CORE CONTAINER DEFINITION ===

from omnibase_core.models.container.model_base_model_onex_container import (
    _BaseModelONEXContainer,
)
from omnibase_core.utils.util_decorators import allow_dict_str_any


@allow_dict_str_any(
    "Container service cache and performance stats use dict[str, Any] for "
    "flexible service instance storage and statistics reporting."
)
class ModelONEXContainer:
    """
    Model ONEX dependency injection container.

    This container wraps the base DI container and adds:
    - Service resolution with caching and logging
    - Observable dependency injection with event emission
    - Contract-driven automatic service registration
    - Workflow orchestration support
    - Enhanced error handling and recovery patterns
    - Performance monitoring and caching
    """

    def __init__(
        self,
        enable_performance_cache: bool = False,
        cache_dir: Path | None = None,
        compute_cache_config: ModelComputeCacheConfig | None = None,
        enable_service_registry: bool = True,
    ) -> None:
        """
        Initialize enhanced container with optional performance optimizations.

        Args:
            enable_performance_cache: Enable memory-mapped tool cache and performance monitoring
            cache_dir: Optional cache directory (defaults to temp directory)
            compute_cache_config: Cache configuration for NodeCompute instances (uses defaults if None)
            enable_service_registry: Enable new ServiceRegistry (default: True)
        """
        self._base_container = _BaseModelONEXContainer()

        # Initialize cache configuration for NodeCompute
        self.compute_cache_config = compute_cache_config or ModelComputeCacheConfig()

        # Initialize performance tracking
        self._performance_metrics = {
            "total_resolutions": 0,
            "cache_hit_rate": 0.0,
            "avg_resolution_time_ms": 0.0,
            "error_rate": 0.0,
            "active_services": 0,
        }

        # Initialize service cache
        self._service_cache: dict[str, Any] = {}

        # Optional performance enhancements
        self.enable_performance_cache = enable_performance_cache
        self.tool_cache: Any = None
        self.performance_monitor: ProtocolPerformanceMonitor | None = None

        # Initialize ServiceRegistry (new DI system)
        self._service_registry: Any = None
        self._enable_service_registry = enable_service_registry

        if enable_service_registry:
            try:
                from omnibase_core.container.service_registry import ServiceRegistry
                from omnibase_core.models.container.model_registry_config import (
                    create_default_registry_config,
                )

                registry_config = create_default_registry_config()
                self._service_registry = ServiceRegistry(registry_config)

                emit_log_event(
                    LogLevel.INFO,
                    "ServiceRegistry initialized for container",
                    {"registry_name": registry_config.registry_name},
                )
            except ImportError as e:
                emit_log_event(
                    LogLevel.WARNING,
                    f"ServiceRegistry not available: {e}",
                )
                self._enable_service_registry = False

        if enable_performance_cache and MemoryMappedToolCache is not None:
            # Initialize memory-mapped cache
            cache_directory = (
                cache_dir or Path(tempfile.gettempdir()) / "onex_production_cache"
            )
            self.tool_cache = MemoryMappedToolCache(
                cache_dir=cache_directory,
                max_cache_size_mb=200,  # Production cache size
                enable_lazy_loading=True,
            )

            # Initialize performance monitoring if available
            if PerformanceMonitor is not None:
                self.performance_monitor = PerformanceMonitor(cache=self.tool_cache)

            emit_log_event(
                LogLevel.INFO,
                f"ModelONEXContainer initialized with performance cache at {cache_directory}",
            )

    @property
    def base_container(self) -> _BaseModelONEXContainer:
        """Access to base ModelONEXContainer for current standards."""
        return self._base_container

    @property
    def config(self) -> Any:
        """Access to configuration."""
        return self._base_container.config

    @property
    def enhanced_logger(self) -> Any:
        """Access to enhanced logger."""
        return self._base_container.enhanced_logger

    @property
    def workflow_factory(self) -> Any:
        """Access to workflow factory."""
        return self._base_container.workflow_factory

    @property
    def workflow_coordinator(self) -> Any:
        """Access to workflow coordinator."""
        return self._base_container.workflow_coordinator

    @property
    def action_registry(self) -> Any:
        """Access to action registry."""
        return self._base_container.action_registry

    @property
    def event_type_registry(self) -> Any:
        """Access to event type registry."""
        return self._base_container.event_type_registry

    @property
    def command_registry(self) -> Any:
        """Access to command registry."""
        return self._base_container.command_registry

    @property
    def secret_manager(self) -> Any:
        """Access to secret manager."""
        return self._base_container.secret_manager

    @property
    def service_registry(self) -> Any:
        """
        Access to service registry (new DI system).

        Returns:
            ServiceRegistry instance if enabled, None otherwise
        """
        return self._service_registry

    async def get_service_async(
        self,
        protocol_type: type[T],
        service_name: str | None = None,
        correlation_id: UUID | None = None,
    ) -> T:
        """
        Async service resolution with caching and logging.

        Enhanced with ServiceRegistry support - tries registry first, then falls back
        to alternative resolution if registry lookup fails.

        Args:
            protocol_type: Protocol interface to resolve
            service_name: Optional service name
            correlation_id: Optional correlation ID for tracking

        Returns:
            T: Resolved service instance

        Raises:
            ModelOnexError: If service resolution fails
        """
        protocol_name = protocol_type.__name__
        cache_key = f"{protocol_name}:{service_name or 'default'}"
        final_correlation_id = correlation_id or uuid4()

        # Check cache first
        if cache_key in self._service_cache:
            emit_log_event(
                LogLevel.INFO,
                f"Service resolved from cache: {protocol_name}",
                {
                    "protocol_type": protocol_name,
                    "service_name": service_name,
                    "correlation_id": str(final_correlation_id),
                },
            )
            cached_service: T = self._service_cache[cache_key]
            return cached_service

        # Use ServiceRegistry (new DI system) - fail fast if enabled
        if self._enable_service_registry and self._service_registry is not None:
            try:
                service_instance = await self._service_registry.resolve_service(
                    interface=protocol_type,
                    context={"correlation_id": final_correlation_id},
                )

                # Cache successful resolution
                self._service_cache[cache_key] = service_instance

                emit_log_event(
                    LogLevel.INFO,
                    f"Service resolved from registry: {protocol_name}",
                    {
                        "protocol_type": protocol_name,
                        "service_name": service_name,
                        "correlation_id": str(final_correlation_id),
                        "source": "service_registry",
                    },
                )

                # Use object cast since T is a TypeVar resolved at runtime
                typed_service = cast(T, service_instance)
                return typed_service

            except Exception as registry_error:
                # Fail fast - ServiceRegistry is the only resolution mechanism when enabled
                emit_log_event(
                    LogLevel.ERROR,
                    f"ServiceRegistry resolution failed: {protocol_name}",
                    {
                        "error": str(registry_error),
                        "correlation_id": str(final_correlation_id),
                    },
                )
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.DEPENDENCY_UNAVAILABLE,
                    message=f"Service resolution failed for {protocol_name}: {registry_error!s}",
                    context={
                        "protocol_type": protocol_name,
                        "service_name": service_name or "",
                        "correlation_id": str(final_correlation_id),
                        "hint": "Ensure the service is registered in ServiceRegistry",
                    },
                ) from registry_error

        # ServiceRegistry not enabled - raise error (no legacy fallback)
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.DEPENDENCY_UNAVAILABLE,
            message=f"Cannot resolve service {protocol_name}: ServiceRegistry is disabled",
            context={
                "protocol_type": protocol_name,
                "service_name": service_name or "",
                "correlation_id": str(final_correlation_id),
                "hint": "Enable ServiceRegistry or register the service",
            },
        )

    def get_service_sync(
        self,
        protocol_type: type[T],
        service_name: str | None = None,
    ) -> T:
        """
        Synchronous service resolution with optional performance monitoring.

        Args:
            protocol_type: Protocol interface to resolve
            service_name: Optional service name

        Returns:
            T: Resolved service instance
        """
        if not self.enable_performance_cache or not self.performance_monitor:
            # Standard resolution without performance monitoring
            return asyncio.run(self.get_service_async(protocol_type, service_name))

        # Enhanced resolution with performance monitoring
        correlation_id = f"svc_{int(time.time() * 1000)}_{service_name or 'default'}"
        start_time = time.perf_counter()

        try:
            # Check tool cache for metadata (optimization)
            cache_hit = False
            if service_name and self.tool_cache:
                tool_metadata = self.tool_cache.lookup_tool(
                    service_name.replace("_registry", ""),
                )
                if tool_metadata:
                    cache_hit = True
                    emit_log_event(
                        LogLevel.DEBUG,
                        f"Tool metadata cache hit for {service_name}",
                    )

            # Perform actual service resolution
            service_instance = asyncio.run(
                self.get_service_async(protocol_type, service_name)
            )

            end_time = time.perf_counter()
            resolution_time_ms = (end_time - start_time) * 1000

            # Track performance
            self.performance_monitor.track_operation(
                operation_name=f"service_resolution_{protocol_type.__name__}",
                duration_ms=resolution_time_ms,
                cache_hit=cache_hit,
                correlation_id=correlation_id,
            )

            # Log slow resolutions
            if resolution_time_ms > 50:  # >50ms is considered slow
                emit_log_event(
                    LogLevel.WARNING,
                    f"Slow service resolution: {service_name} took {resolution_time_ms:.2f}ms",
                )

            return service_instance

        except Exception as e:
            end_time = time.perf_counter()
            resolution_time_ms = (end_time - start_time) * 1000

            # Track failed resolution
            if self.performance_monitor:
                self.performance_monitor.track_operation(
                    operation_name=f"service_resolution_failed_{protocol_type.__name__}",
                    duration_ms=resolution_time_ms,
                    cache_hit=False,
                    correlation_id=correlation_id,
                )

            emit_log_event(
                LogLevel.ERROR,
                f"Service resolution failed for {service_name}: {e}",
            )

            raise

    # Compatibility alias
    def get_service(
        self,
        protocol_type: type[T],
        service_name: str | None = None,
    ) -> T:
        """Modern standards method."""
        return self.get_service_sync(protocol_type, service_name)

    def get_service_optional(
        self,
        protocol_type: type[T],
        service_name: str | None = None,
    ) -> T | None:
        """
        Get service with optional return - returns None if not found.

        This method provides a non-throwing alternative to get_service(),
        useful for optional dependencies that may not be available in all
        container configurations.

        Args:
            protocol_type: Protocol interface to resolve
            service_name: Optional service name

        Returns:
            Service instance of type T, or None if service cannot be resolved
        """
        try:
            return self.get_service_sync(protocol_type, service_name)
        except Exception:  # fallback-ok: Optional service getter intentionally returns None when service unavailable
            return None

    def get_workflow_orchestrator(self) -> Any:
        """Get workflow orchestration coordinator."""
        return self.workflow_coordinator()

    def get_performance_metrics(self) -> dict[str, ModelSchemaValue]:
        """
        Get container performance metrics.

        Returns:
            Dict containing resolution times, cache hits, errors, etc.
        """
        # Convert performance metrics to ModelSchemaValue
        return {
            key: ModelSchemaValue.from_value(value)
            for key, value in self._performance_metrics.items()
        }

    async def get_service_discovery(self) -> ProtocolServiceDiscovery:
        """Get service discovery implementation with automatic fallback."""
        return await self.get_service_async(ProtocolServiceDiscovery)

    async def get_database(self) -> ProtocolDatabaseConnection:
        """Get database connection implementation with automatic fallback."""
        return await self.get_service_async(ProtocolDatabaseConnection)

    async def get_external_services_health(self) -> dict[str, object]:
        """Get health status for all external services."""
        # TODO: Ready to implement using ProtocolServiceResolver from omnibase_spi.protocols.container
        # Note: ProtocolServiceResolver available in omnibase_spi v0.2.0
        # service_resolver = get_service_resolver()
        # return await service_resolver.get_all_service_health()
        return {
            "status": "unavailable",
            "message": "External service health check not yet implemented - requires omnibase-spi integration",
        }

    async def refresh_external_services(self) -> None:
        """Force refresh all external service connections."""
        # TODO: Ready to implement using ProtocolServiceResolver from omnibase_spi.protocols.container
        # Note: ProtocolServiceResolver available in omnibase_spi v0.2.0
        # service_resolver = get_service_resolver()

        # Refresh service discovery if cached
        # try:
        #     await service_resolver.refresh_service(ProtocolServiceDiscovery)
        # except Exception:
        #     pass  # Service may not be cached yet

        # Refresh database if cached
        # try:
        #     await service_resolver.refresh_service(ProtocolDatabaseConnection)
        # except Exception:
        #     pass  # Service may not be cached yet

        emit_log_event(
            LogLevel.WARNING,
            "External service refresh not yet implemented - requires omnibase-spi integration",
            {"method": "refresh_external_services"},
        )

    async def warm_cache(self) -> None:
        """Warm up the tool cache for better performance."""
        if not self.tool_cache:
            return

        emit_log_event(
            LogLevel.INFO,
            "Starting cache warming process",
        )

        # Common tool registries to pre-warm
        common_services = [
            "contract_validator_registry",
            "contract_driven_generator_registry",
            "file_writer_registry",
            "logger_engine_registry",
            "smart_log_formatter_registry",
            "ast_generator_registry",
            "workflow_generator_registry",
        ]

        warmed_count = 0
        for service_name in common_services:
            try:
                # Pre-resolve service to warm container cache
                self.get_service(object, service_name)
                warmed_count += 1
            except Exception:
                pass  # Expected for some services

        emit_log_event(
            LogLevel.INFO,
            f"Cache warming completed: {warmed_count}/{len(common_services)} services warmed",
        )

    def get_performance_stats(self) -> SerializedDict:
        """Get comprehensive performance statistics."""
        stats: SerializedDict = {
            "container_type": "ModelONEXContainer",
            "cache_enabled": self.enable_performance_cache,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Add base container metrics
        base_metrics = self.get_performance_metrics()
        stats["base_metrics"] = {
            key: value.to_value() for key, value in base_metrics.items()
        }

        if self.tool_cache:
            stats["tool_cache"] = self.tool_cache.get_cache_stats()

        if self.performance_monitor:
            stats["performance_monitoring"] = (
                self.performance_monitor.get_monitoring_dashboard()
            )

        return stats

    async def run_performance_checkpoint(
        self, phase_name: str = "production"
    ) -> TypedDictPerformanceCheckpointResult:
        """Run comprehensive performance checkpoint.

        This method delegates to a PerformanceMonitor implementation that satisfies
        ProtocolPerformanceMonitor. When performance monitoring is not enabled or
        the PerformanceMonitor module is not available, returns an error result.

        Args:
            phase_name: Name of the checkpoint phase (e.g., "production", "development")

        Returns:
            TypedDictPerformanceCheckpointResult containing either:
            - Performance metrics, recommendations, and status when monitoring is enabled
            - An error message when performance monitoring is not available

        Note:
            Performance monitoring requires omnibase_core.monitoring.performance_monitor.PerformanceMonitor
            to be implemented. This module is optional and may not be present in all deployments.
            When unavailable, this method returns a graceful error response rather than raising.

        See Also:
            - ProtocolPerformanceMonitor: Protocol defining the required interface
            - TypedDictPerformanceCheckpointResult: Return type structure
        """
        if not self.performance_monitor:
            return TypedDictPerformanceCheckpointResult(
                error="Performance monitoring not enabled. "
                "The omnibase_core.monitoring.performance_monitor module is not available. "
                "Enable by implementing PerformanceMonitor satisfying ProtocolPerformanceMonitor."
            )

        # Delegate to performance monitor implementation
        # See ProtocolPerformanceMonitor for the expected interface
        result: TypedDictPerformanceCheckpointResult = (
            await self.performance_monitor.run_optimization_checkpoint(phase_name)
        )
        return result

    def close(self) -> None:
        """Clean up resources."""
        if self.tool_cache:
            self.tool_cache.close()

        emit_log_event(
            LogLevel.INFO,
            "ModelONEXContainer closed",
        )


# === HELPER FUNCTIONS ===
# Helper functions moved to base_model_onex_container.py

# === CONTAINER FACTORY ===


async def create_model_onex_container(
    enable_cache: bool = False,
    cache_dir: Path | None = None,
    compute_cache_config: ModelComputeCacheConfig | None = None,
    enable_service_registry: bool = True,
) -> ModelONEXContainer:
    """
    Create and configure model ONEX container with optional performance optimizations.

    Args:
        enable_cache: Enable memory-mapped tool cache and performance monitoring
        cache_dir: Optional cache directory (defaults to temp directory)
        compute_cache_config: Cache configuration for NodeCompute instances (uses defaults if None)
        enable_service_registry: Enable new ServiceRegistry (default: True)

    Returns:
        ModelONEXContainer: Configured container instance
    """
    container = ModelONEXContainer(
        enable_performance_cache=enable_cache,
        cache_dir=cache_dir,
        compute_cache_config=compute_cache_config,
        enable_service_registry=enable_service_registry,
    )

    # Load configuration into base container
    container.config.from_dict(
        {
            "logging": {"level": os.getenv("LOG_LEVEL", "INFO")},
            "consul": {
                "agent_url": f"http://{os.getenv('CONSUL_HOST', 'localhost')}:{os.getenv('CONSUL_PORT', '8500')}",
                "datacenter": os.getenv("CONSUL_DATACENTER", "dc1"),
                "timeout": int(os.getenv("CONSUL_TIMEOUT", "10")),
            },
            "services": {
                # Enhanced service configurations
            },
            "workflows": {
                "default_timeout": int(os.getenv("WORKFLOW_TIMEOUT", "300")),
                "max_concurrent_workflows": int(os.getenv("MAX_WORKFLOWS", "10")),
            },
            "database": {
                "circuit_breaker": {
                    "failure_threshold": int(
                        os.getenv("DB_CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5")
                    ),
                    "recovery_timeout": int(
                        os.getenv("DB_CIRCUIT_BREAKER_RECOVERY_TIMEOUT", "60")
                    ),
                    "half_open_max_calls": int(
                        os.getenv("DB_CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS", "3")
                    ),
                },
            },
        },
    )

    # Warm up caches for better performance
    if enable_cache:
        await container.warm_cache()

    return container


# === GLOBAL ENHANCED CONTAINER ===


async def get_model_onex_container() -> ModelONEXContainer:
    """Get or create container instance from current context.

    This function retrieves the container from the current execution context
    using contextvars. If no container exists in the context, it creates
    a new one and sets it in the context.

    The context-based approach provides proper isolation between:
    - Different asyncio tasks
    - Different threads
    - Nested contexts (via token-based reset)

    Returns:
        ModelONEXContainer: The container instance for the current context

    Example:
        # Using context manager (recommended for new code):
        from omnibase_core.context import run_with_container

        container = await create_model_onex_container()
        async with run_with_container(container):
            # Container is now available via get_model_onex_container()
            current = await get_model_onex_container()

        # Legacy usage (still works):
        container = await get_model_onex_container()  # Creates if needed
    """
    container = get_current_container()
    if container is None:
        container = await create_model_onex_container()
        set_current_container(container)
    return container


def get_model_onex_container_sync() -> ModelONEXContainer:
    """Get container synchronously from current context.

    This function checks for a container in the current context
    (via contextvars). If no container exists, it creates a new one
    and sets it in the context.

    Note: This creates a new event loop for each call when no container
    is available. Prefer using get_model_onex_container() in async code.

    Returns:
        ModelONEXContainer: The container instance for the current context
    """
    # Check contextvar for existing container
    container = get_current_container()
    if container is not None:
        return container

    # No container exists - create one
    # asyncio.run creates a new context, so the container set inside
    # won't propagate back. We need to capture and set it here.
    container = asyncio.run(create_model_onex_container())

    # Set in context for future access
    set_current_container(container)

    return container
