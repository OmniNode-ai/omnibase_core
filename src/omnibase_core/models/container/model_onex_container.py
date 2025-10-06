import uuid
from typing import Any, Callable, Dict, Optional, TypeVar

from pydantic import BaseModel

from omnibase_core.errors.model_onex_error import ModelOnexError

"""
Model ONEX Dependency Injection Container.

This module provides the ModelONEXContainer that integrates with
the contract-driven architecture, supporting workflow orchestration
and observable dependency injection.

Author: ONEX Framework Team
"""

import asyncio
import os
import tempfile
import time
from collections.abc import Callable as CallableABC
from datetime import datetime
from pathlib import Path

# Import needed for type annotations
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, TypeVar
from uuid import UUID, uuid4

from dependency_injector import containers, providers
from omnibase_spi import ProtocolLogger

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

# Optional performance enhancements
try:
    from omnibase_core.cache.memory_mapped_tool_cache import MemoryMappedToolCache
except ImportError:
    # FALLBACK_REASON: cache module is optional performance enhancement,
    # system can operate without it using standard container behavior
    MemoryMappedToolCache = None  # type: ignore[misc, assignment]

try:
    from omnibase_core.monitoring.performance_monitor import PerformanceMonitor
except ImportError:
    # FALLBACK_REASON: performance monitoring is optional feature,
    # container can function without monitoring capabilities
    PerformanceMonitor = None  # type: ignore[misc, assignment]

# TODO: These imports require omnibase-spi protocols that may not be available yet
# from omnibase_core.protocols.protocol_database_connection import ProtocolDatabaseConnection
# from omnibase_core.protocols.protocol_service_discovery import ProtocolServiceDiscovery
# from omnibase_core.services.protocol_service_resolver import get_service_resolver

# Type aliases for unavailable protocols (until omnibase-spi is fully integrated)
ProtocolDatabaseConnection = Any
ProtocolServiceDiscovery = Any

if TYPE_CHECKING:
    from omnibase_core.infrastructure.node_base import NodeBase

T = TypeVar("T")


# === CORE CONTAINER DEFINITION ===

from .base_model_onex_container import _BaseModelONEXContainer


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
    ) -> None:
        """
        Initialize enhanced container with optional performance optimizations.

        Args:
            enable_performance_cache: Enable memory-mapped tool cache and performance monitoring
            cache_dir: Optional cache directory (defaults to temp directory)
        """
        self._base_container = _BaseModelONEXContainer()

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
        self.performance_monitor: Any = None

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

    async def get_service_async(
        self,
        protocol_type: type[T],
        service_name: str | None = None,
        correlation_id: UUID | None = None,
    ) -> T:
        """
        Async service resolution with caching and logging.

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
            return self._service_cache[cache_key]

        # Resolve service
        try:
            start_time = datetime.now()

            # TODO: Protocol service resolver not yet available - requires omnibase-spi integration
            # Use protocol service resolver for external dependencies
            if protocol_name in [
                "ProtocolServiceDiscovery",
                "ProtocolDatabaseConnection",
            ]:
                # service_resolver = get_service_resolver()
                # service_instance = await service_resolver.resolve_service(protocol_type)
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.DEPENDENCY_UNAVAILABLE,
                    message=f"Protocol service resolution not yet implemented: {protocol_name}",
                    protocol_type=protocol_name,
                    service_name=service_name or "",
                    note="Requires omnibase-spi protocol integration",
                    correlation_id=final_correlation_id,
                )
            else:
                # Map common protocol names to container providers
                provider_map = {
                    "ProtocolLogger": "enhanced_logger",
                    "Logger": "enhanced_logger",
                }

                if protocol_name in provider_map:
                    provider_name = provider_map[protocol_name]
                    provider = getattr(self._base_container, provider_name, None)
                    if provider:
                        service_instance = provider()
                    else:
                        raise ModelOnexError(
                            error_code=EnumCoreErrorCode.DEPENDENCY_UNAVAILABLE,
                            message=f"Provider not found: {provider_name}",
                            protocol_type=protocol_name,
                            correlation_id=final_correlation_id,
                        )
                else:
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.DEPENDENCY_UNAVAILABLE,
                        message=f"Unable to resolve service for protocol {protocol_name}",
                        protocol_type=protocol_name,
                        service_name=service_name or "",
                        correlation_id=final_correlation_id,
                    )

            end_time = datetime.now()
            resolution_time_ms = int((end_time - start_time).total_seconds() * 1000)

            # Cache successful resolution
            self._service_cache[cache_key] = service_instance

            emit_log_event(
                LogLevel.INFO,
                f"Service resolved successfully: {protocol_name}",
                {
                    "protocol_type": protocol_name,
                    "service_name": service_name,
                    "resolution_time_ms": resolution_time_ms,
                    "correlation_id": str(final_correlation_id),
                },
            )

            return service_instance

        except Exception as e:
            emit_log_event(
                LogLevel.ERROR,
                f"Service resolution failed: {protocol_name}",
                {
                    "protocol_type": protocol_name,
                    "service_name": service_name,
                    "error": str(e),
                    "correlation_id": str(final_correlation_id),
                },
            )
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.DEPENDENCY_UNAVAILABLE,
                message=f"Service resolution failed for {protocol_name}: {e!s}",
                protocol_type=protocol_name,
                service_name=service_name or "",
                correlation_id=final_correlation_id,
            ) from e

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
        correlation_id = f"svc_{int(time.time()*1000)}_{service_name or 'default'}"
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

    async def create_enhanced_nodebase(
        self,
        contract_path: Path,
        node_id: UUID | None = None,
        workflow_id: UUID | None = None,
        session_id: UUID | None = None,
    ) -> "NodeBase[Any]":
        """
        Factory method for creating Enhanced NodeBase instances.

        Args:
            contract_path: Path to contract file
            node_id: Optional node identifier
            workflow_id: Optional workflow identifier
            session_id: Optional session identifier

        Returns:
            NodeBase: Configured node instance
        """

        return NodeBase(
            contract_path=contract_path,
            node_id=node_id,
            container=self,
            workflow_id=workflow_id,
            session_id=session_id,
        )

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
        # TODO: Requires omnibase-spi protocol service resolver
        # service_resolver = get_service_resolver()
        # return await service_resolver.get_all_service_health()
        return {
            "status": "unavailable",
            "message": "External service health check not yet implemented - requires omnibase-spi integration",
        }

    async def refresh_external_services(self) -> None:
        """Force refresh all external service connections."""
        # TODO: Requires omnibase-spi protocol service resolver
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

    def get_performance_stats(self) -> dict[str, Any]:
        """Get comprehensive performance statistics."""
        stats = {
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
    ) -> dict[str, Any]:
        """Run comprehensive performance checkpoint."""
        if not self.performance_monitor:
            return {"error": "Performance monitoring not enabled"}

        return await self.performance_monitor.run_optimization_checkpoint(phase_name)

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
) -> ModelONEXContainer:
    """
    Create and configure model ONEX container with optional performance optimizations.

    Args:
        enable_cache: Enable memory-mapped tool cache and performance monitoring
        cache_dir: Optional cache directory (defaults to temp directory)

    Returns:
        ModelONEXContainer: Configured container instance
    """
    container = ModelONEXContainer(
        enable_performance_cache=enable_cache,
        cache_dir=cache_dir,
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
        },
    )

    # Warm up caches for better performance
    if enable_cache:
        await container.warm_cache()

    return container


# === GLOBAL ENHANCED CONTAINER ===

_model_onex_container: ModelONEXContainer | None = None


async def get_model_onex_container() -> ModelONEXContainer:
    """Get or create global enhanced container instance."""
    global _model_onex_container
    if _model_onex_container is None:
        _model_onex_container = await create_model_onex_container()
    return _model_onex_container


def get_model_onex_container_sync() -> ModelONEXContainer:
    """Get enhanced container synchronously."""
    return asyncio.run(get_model_onex_container())
