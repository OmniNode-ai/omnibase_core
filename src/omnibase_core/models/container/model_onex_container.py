"""Model ONEX Dependency Injection Container.

This module provides the ModelONEXContainer, the primary dependency injection
container for the ONEX framework. It integrates with the contract-driven
architecture and provides:

- Protocol-based service resolution with caching
- Observable dependency injection with event emission
- Workflow orchestration support via ModelWorkflowCoordinator
- Optional performance monitoring and memory-mapped caching
- Context-based container management for async/thread isolation

The container wraps _BaseModelONEXContainer (dependency-injector based) and
adds enhanced features for production deployments.

Example:
    Basic usage::

        container = await create_model_onex_container()
        service = await container.get_service_async(ProtocolLogger)

    With context management::

        from omnibase_core.context import run_with_container

        async with run_with_container(container):
            current = await get_model_onex_container()

See Also:
    - _BaseModelONEXContainer: Low-level DI container
    - ServiceRegistry: New DI system for protocol-based resolution
    - ModelWorkflowCoordinator: Workflow orchestration
"""

# NOTE(OMN-1302): I001 (import order) disabled - Dual-Import Pattern for DI container (see OMN-1261).

from typing import TYPE_CHECKING, TypeVar, cast

from omnibase_core.decorators.decorator_allow_dict_any import allow_dict_any
from omnibase_core.decorators.decorator_error_handling import standard_error_handling
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import (
    SerializableValue,
    SerializedDict,
)
from omnibase_core.types.typed_dict_performance_checkpoint_result import (
    TypedDictPerformanceCheckpointResult,
)

if TYPE_CHECKING:
    from dependency_injector.providers import Configuration, Factory, Singleton

    from omnibase_core.container.container_service_registry import ServiceRegistry
    from omnibase_core.models.container.model_enhanced_logger import ModelEnhancedLogger
    from omnibase_core.models.container.model_registry_config import (
        ModelServiceRegistryConfig,
    )
    from omnibase_core.models.container.model_workflow_coordinator import (
        ModelWorkflowCoordinator,
    )
    from omnibase_core.models.container.model_workflow_factory import (
        ModelWorkflowFactory,
    )
    from omnibase_core.models.core.model_action_registry import ModelActionRegistry
    from omnibase_core.models.core.model_cli_command_registry import (
        ModelCliCommandRegistry,
    )
    from omnibase_core.models.core.model_event_type_registry import (
        ModelEventTypeRegistry,
    )
    from omnibase_core.models.security.model_secret_manager import ModelSecretManager
    from omnibase_core.protocols.compute.protocol_performance_monitor import (
        ProtocolPerformanceMonitor,
    )

import asyncio
import os
import tempfile
import threading
import time
from pathlib import Path

# Import needed for type annotations
from uuid import UUID, uuid4

# Import context-based container management
from omnibase_core.context.context_application import (
    get_current_container,
    set_current_container,
)
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.logging_structured import (
    emit_log_event_sync as emit_log_event,
)
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

# Infrastructure protocol imports for database and service discovery
from omnibase_core.protocols.infrastructure import (
    ProtocolDatabaseConnection,
    ProtocolServiceDiscovery,
)

# Compute protocol imports for tool caching
from omnibase_core.protocols.compute import ProtocolToolCache

# ServiceRegistry Dual-Import Pattern (OMN-1261):
# 1. TYPE_CHECKING import (header): Provides type hints for mypy/pyright static analysis
#    without triggering runtime circular imports.
# 2. Lazy import (__init__): Defers actual module loading to instantiation time,
#    when all modules are fully loaded, breaking the circular dependency chain:
#    model_onex_container -> container_service_registry -> models/container/__init__ -> model_onex_container

T = TypeVar("T")

# === CORE CONTAINER DEFINITION ===

from omnibase_core.models.container.model_base_model_onex_container import (
    _BaseModelONEXContainer,
)


class ModelONEXContainer:
    """Model ONEX dependency injection container.

    The primary DI container for ONEX applications. Wraps _BaseModelONEXContainer
    and adds production-ready features including service caching, performance
    monitoring, and workflow orchestration.

    This container uses protocol-based resolution - services are resolved by
    their protocol interface, not concrete implementation. This enables loose
    coupling and easy testing via mock implementations.

    Attributes:
        compute_cache_config: Configuration for NodeCompute instance caching.
        enable_performance_cache: Whether memory-mapped caching is enabled.
        tool_cache: Optional MemoryMappedToolCache for tool metadata caching.
        performance_monitor: Optional ProtocolPerformanceMonitor for metrics.

    Example:
        Basic service resolution::

            container = ModelONEXContainer(enable_service_registry=True)
            logger = await container.get_service_async(ProtocolLogger)

        With performance caching::

            container = ModelONEXContainer(
                enable_performance_cache=True,
                cache_dir=Path("/tmp/cache")
            )
            stats = container.get_performance_stats()

    Note:
        This class is NOT thread-safe. Use separate instances per thread or
        use context-based container management via get_model_onex_container().

    See Also:
        - create_model_onex_container: Factory function for creating containers
        - get_model_onex_container: Get container from current context
    """

    @allow_dict_any(
        reason="DI container requires generic service cache for protocol resolution"
    )
    def __init__(
        self,
        enable_performance_cache: bool = False,
        cache_dir: Path | None = None,
        compute_cache_config: ModelComputeCacheConfig | None = None,
        enable_service_registry: bool = True,
    ) -> None:
        """Initialize enhanced container with optional performance optimizations.

        This constructor uses a lazy import pattern for ServiceRegistry to avoid
        circular imports (see OMN-1261). The ServiceRegistry is imported at
        instantiation time rather than module load time.

        Args:
            enable_performance_cache: Enable memory-mapped tool cache and performance monitoring.
            cache_dir: Optional cache directory (defaults to temp directory).
            compute_cache_config: Cache configuration for NodeCompute instances (uses defaults if None).
            enable_service_registry: Enable new ServiceRegistry for protocol-based DI (default: True).

        Note:
            If ServiceRegistry initialization fails (import error or other exception),
            the container falls back to disabled service registry mode and logs the error.
            This ensures container creation succeeds even when optional dependencies fail.
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
        self._service_cache: dict[str, object] = {}

        # Optional performance enhancements
        self.enable_performance_cache = enable_performance_cache
        # tool_cache uses ProtocolToolCache for duck typing support.
        # MemoryMappedToolCache may not be available (optional import).
        # When not None, tool_cache is guaranteed to implement ProtocolToolCache.
        self.tool_cache: ProtocolToolCache | None = None
        self.performance_monitor: ProtocolPerformanceMonitor | None = None

        # Initialize ServiceRegistry (new DI system)
        # Note: ServiceRegistry is imported in TYPE_CHECKING block; using string annotation
        self._service_registry: "ServiceRegistry | None" = None  # noqa: UP037
        self._service_registry_lock = threading.Lock()
        self._enable_service_registry = enable_service_registry

        if enable_service_registry:
            # Lazy import to avoid circular dependency (OMN-1261)
            # The import is done here at instantiation time rather than at module load
            # time to break the circular chain: model_onex_container -> container_service_registry
            # -> models/container/__init__ -> model_onex_container
            try:
                from omnibase_core.container.container_service_registry import (
                    ServiceRegistry,
                )
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
            except Exception as e:
                # init-errors-ok: use safe defaults if ServiceRegistry initialization fails
                emit_log_event(
                    LogLevel.ERROR,
                    f"Failed to initialize ServiceRegistry: {e}",
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
    def config(self) -> "Configuration":
        return self._base_container.config

    @property
    def enhanced_logger(self) -> "Factory[ModelEnhancedLogger]":
        return self._base_container.enhanced_logger

    @property
    def workflow_factory(self) -> "Factory[ModelWorkflowFactory]":
        return self._base_container.workflow_factory

    @property
    def workflow_coordinator(self) -> "Singleton[ModelWorkflowCoordinator]":
        return self._base_container.workflow_coordinator

    @property
    def action_registry(self) -> "Singleton[ModelActionRegistry]":
        return self._base_container.action_registry

    @property
    def event_type_registry(self) -> "Singleton[ModelEventTypeRegistry]":
        return self._base_container.event_type_registry

    @property
    def command_registry(self) -> "Singleton[ModelCliCommandRegistry]":
        return self._base_container.command_registry

    @property
    def secret_manager(self) -> "Singleton[ModelSecretManager]":
        return self._base_container.secret_manager

    @property
    def service_registry(self) -> "ServiceRegistry":
        """Access to service registry (new DI system).

        Returns:
            ServiceRegistry instance.

        Raises:
            ModelOnexError: If registry is not initialized. Call
                initialize_service_registry() first.

        See Also:
            initialize_service_registry: Explicit initialization method.
        """
        if self._service_registry is None:
            raise ModelOnexError(
                message="Service registry not initialized. Call container.initialize_service_registry() first.",
                error_code=EnumCoreErrorCode.INVALID_STATE,
                context={
                    "hint": "Use initialize_service_registry(config) to initialize."
                },
            )
        return self._service_registry

    @standard_error_handling("Service registry initialization")
    def initialize_service_registry(
        self,
        config: "ModelServiceRegistryConfig | None" = None,
    ) -> "ServiceRegistry":
        """Initialize the service registry exactly once.

        This method provides explicit control over service registry initialization.
        After initialization, the ``service_registry`` property will return the
        registry instance directly. If accessed before initialization, the property
        raises ``ModelOnexError`` with ``INVALID_STATE`` error code.

        It uses lazy imports to avoid circular dependencies (see OMN-1261).

        Args:
            config: Registry configuration. Uses default if None.

        Returns:
            The initialized ServiceRegistry instance.

        Raises:
            ModelOnexError: If registry is already initialized, or if ServiceRegistry
                instantiation fails. The ``@standard_error_handling`` decorator wraps
                unexpected exceptions (e.g., ValueError, TypeError) in ModelOnexError
                with ``OPERATION_FAILED`` error code. Container state remains unchanged
                on failure, allowing retry with corrected configuration.

        Note:
            This method is thread-safe. Multiple threads can call it simultaneously;
            exactly one will succeed and others will receive INVALID_STATE errors.

        Example:
            Explicit initialization::

                container = ModelONEXContainer(enable_service_registry=False)
                registry = container.initialize_service_registry()

            With custom config::

                from omnibase_core.models.container.model_registry_config import (
                    ModelServiceRegistryConfig,
                )

                config = ModelServiceRegistryConfig(registry_name="custom")
                registry = container.initialize_service_registry(config)
        """
        with self._service_registry_lock:
            if self._service_registry is not None:
                raise ModelOnexError(
                    message="Service registry already initialized. Use container.service_registry.",
                    error_code=EnumCoreErrorCode.INVALID_STATE,
                    context={
                        "hint": "If you need reconfiguration, create a new container."
                    },
                )

            # Track whether custom config was provided before defaulting
            config_was_provided = config is not None

            # Lazy import to avoid circular dependency (OMN-1261)
            from omnibase_core.container.container_service_registry import (
                ServiceRegistry,
            )
            from omnibase_core.models.container.model_registry_config import (
                create_default_registry_config,
            )

            if config is None:
                config = create_default_registry_config()

            self._service_registry = ServiceRegistry(config)
            self._enable_service_registry = True

            emit_log_event(
                LogLevel.INFO,
                "ServiceRegistry initialized via initialize_service_registry()",
                {
                    "registry_name": config.registry_name,
                    "custom_config": config_was_provided,
                },
            )

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
            cached_service = cast(T, self._service_cache[cache_key])
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

                # service_instance is already typed as T from resolve_service[T]
                return service_instance

            except (
                AttributeError,
                KeyError,
                ModelOnexError,
                RuntimeError,
                ValueError,
            ) as registry_error:
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
                    message=f"Service resolution failed for {protocol_name}: {registry_error!s}",
                    error_code=EnumCoreErrorCode.DEPENDENCY_UNAVAILABLE,
                    context={
                        "protocol_type": protocol_name,
                        "service_name": service_name or "",
                        "correlation_id": str(final_correlation_id),
                        "hint": "Ensure the service is registered in ServiceRegistry",
                    },
                ) from registry_error

        # ServiceRegistry not enabled - raise error (no legacy fallback)
        raise ModelOnexError(
            message=f"Cannot resolve service {protocol_name}: ServiceRegistry is disabled",
            error_code=EnumCoreErrorCode.DEPENDENCY_UNAVAILABLE,
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
                # tool_cache implements ProtocolToolCache when not None
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

        except (AttributeError, KeyError, ModelOnexError, RuntimeError) as e:
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
        """Resolve a service by protocol type (synchronous).

        Compatibility alias for get_service_sync(). Prefer get_service_async()
        in async contexts to avoid blocking event loop.

        Args:
            protocol_type: Protocol interface to resolve.
            service_name: Optional service name for named registrations.

        Returns:
            Resolved service instance of type T.

        Raises:
            ModelOnexError: If service resolution fails or ServiceRegistry
                is disabled.
        """
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

    def get_workflow_orchestrator(self) -> "ModelWorkflowCoordinator":
        """Get the workflow orchestration coordinator singleton.

        Returns the ModelWorkflowCoordinator for executing LlamaIndex-style
        workflows. The coordinator manages workflow lifecycle, step execution,
        and error handling.

        Returns:
            ModelWorkflowCoordinator singleton instance.
        """
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
        """Get the service discovery implementation.

        Resolves ProtocolServiceDiscovery from the ServiceRegistry. Used for
        dynamic service lookup in distributed deployments.

        Returns:
            Service discovery implementation.

        Raises:
            ModelOnexError: If service discovery is not registered.
        """
        # type-abstract: Protocol used for DI resolution, concrete impl registered at runtime
        return await self.get_service_async(ProtocolServiceDiscovery)  # type: ignore[type-abstract]

    async def get_database(self) -> ProtocolDatabaseConnection:
        """Get the database connection implementation.

        Resolves ProtocolDatabaseConnection from the ServiceRegistry.

        Returns:
            Database connection implementation.

        Raises:
            ModelOnexError: If database connection is not registered.
        """
        # type-abstract: Protocol used for DI resolution, concrete impl registered at runtime
        return await self.get_service_async(ProtocolDatabaseConnection)  # type: ignore[type-abstract]

    async def get_external_services_health(self) -> dict[str, object]:
        """Get health status for all external services.

        Returns:
            Dictionary with service health information. Currently returns
            unavailable status as this requires omnibase-spi integration.
        """
        # TODO(OMN-TBD): Implement using ProtocolServiceResolver from omnibase_spi.protocols.container  [NEEDS TICKET]
        # Note: ProtocolServiceResolver available in omnibase_spi v0.2.0
        return {
            "status": "unavailable",
            "message": "External service health check not yet implemented - requires omnibase-spi integration",
        }

    async def refresh_external_services(self) -> None:
        """Force refresh all external service connections.

        Clears cached service instances and re-establishes connections.
        Currently logs a warning as this requires omnibase-spi integration.
        """
        # TODO(OMN-TBD): Implement using ProtocolServiceResolver from omnibase_spi.protocols.container  [NEEDS TICKET]
        # Note: ProtocolServiceResolver available in omnibase_spi v0.2.0
        emit_log_event(
            LogLevel.WARNING,
            "External service refresh not yet implemented - requires omnibase-spi integration",
            {"method": "refresh_external_services"},
        )

    async def warm_cache(self) -> None:
        """Warm up the tool cache for better performance.

        Pre-resolves common services to populate the service cache. This
        reduces latency for first-time service resolution in production.
        Called automatically when enable_cache=True in factory function.
        """
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
            except (
                Exception
            ):  # fallback-ok: service not found during cache warming is expected
                pass

        emit_log_event(
            LogLevel.INFO,
            f"Cache warming completed: {warmed_count}/{len(common_services)} services warmed",
        )

    def get_performance_stats(self) -> SerializedDict:
        """Get comprehensive performance statistics.

        Returns:
            Dictionary containing:
            - container_type: Container class name
            - cache_enabled: Whether performance cache is active
            - timestamp: Current time
            - base_metrics: Resolution counts, cache hits, error rates
            - tool_cache: Tool cache stats (if enabled)
            - performance_monitoring: Dashboard data (if enabled)
        """
        stats: SerializedDict = {
            "container_type": "ModelONEXContainer",
            "cache_enabled": self.enable_performance_cache,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Add base container metrics
        base_metrics = self.get_performance_metrics()
        # Cast to dict[str, SerializableValue] since to_value() returns object.
        # Safe because ModelSchemaValue.to_value() only returns JSON-compatible types.
        stats["base_metrics"] = cast(
            dict[str, SerializableValue],
            {key: value.to_value() for key, value in base_metrics.items()},
        )

        if self.tool_cache:
            # Cast dict[str, object] to SerializableValue for SerializedDict assignment
            stats["tool_cache"] = cast(
                SerializableValue, self.tool_cache.get_cache_stats()
            )

        if self.performance_monitor:
            # Cast TypedDictMonitoringDashboard to SerializableValue for SerializedDict assignment
            stats["performance_monitoring"] = cast(
                SerializableValue, self.performance_monitor.get_monitoring_dashboard()
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
        """Clean up container resources.

        Closes the tool cache if enabled and emits a log event. Call this
        when shutting down the application to release memory-mapped files.
        """
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

    # Explicit type annotation to satisfy mypy (from_dict returns Any from dependency_injector)
    result: ModelONEXContainer = container
    return result


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
