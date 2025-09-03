#!/usr/bin/env python3
"""
Enhanced ONEX Container with Memory-Mapped Cache Integration

Integrates the Codanna-inspired memory-mapped tool cache with the existing
ONEX container system for production-ready performance optimizations.
"""

import asyncio
import time
from pathlib import Path
from typing import TypeVar

try:
    from omnibase_core.cache.memory_mapped_tool_cache import (
        MemoryMappedToolCache,
    )
except ImportError:
    # Cache module not available, use None as fallback
    MemoryMappedToolCache = None
from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.core.onex_container import ModelONEXContainer
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel

try:
    from omnibase_core.monitoring.performance_monitor import (
        PerformanceMonitor,
    )
except ImportError:
    # Performance monitoring not available, use None as fallback
    PerformanceMonitor = None

T = TypeVar("T")


class ModelONEXContainer(ModelONEXContainer):
    """
    Enhanced ONEX container with Codanna performance optimizations.

    Adds memory-mapped tool caching and performance monitoring to the
    standard ONEX dependency injection container.
    """

    def __init__(
        self,
        enable_performance_cache: bool = True,
        cache_dir: Path | None = None,
    ):
        """Initialize enhanced container with performance optimizations."""
        super().__init__()

        self.enable_performance_cache = enable_performance_cache
        self.tool_cache: MemoryMappedToolCache | None = None
        self.performance_monitor: PerformanceMonitor | None = None

        if enable_performance_cache and MemoryMappedToolCache is not None:
            # Initialize memory-mapped cache
            cache_directory = cache_dir or Path("/tmp/onex_production_cache")
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
                f"Enhanced ONEX container initialized with performance cache at {cache_directory}",
                event_type="enhanced_container_init",
            )

    def get_service(
        self,
        protocol_type: type[T],
        service_name: str | None = None,
    ) -> T:
        """
        Enhanced service resolution with performance monitoring and caching.

        Wraps the standard container service resolution with:
        - Performance monitoring
        - Tool metadata caching
        - Codanna optimization tracking
        """
        if not self.enable_performance_cache or not self.performance_monitor:
            # Fallback to standard container behavior
            return super().get_service(protocol_type, service_name)

        # Generate correlation ID for tracing
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
                        event_type="tool_cache_hit",
                    )

            # Perform actual service resolution
            service_instance = super().get_service(protocol_type, service_name)

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
                    event_type="slow_service_resolution",
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
                event_type="service_resolution_error",
            )

            raise

    async def warm_cache(self) -> None:
        """Warm up the tool cache for better performance."""
        if not self.tool_cache:
            return

        emit_log_event(
            LogLevel.INFO,
            "Starting cache warming process",
            event_type="cache_warming_start",
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
            event_type="cache_warming_complete",
        )

    def get_performance_stats(self) -> dict:
        """Get comprehensive performance statistics."""
        stats = {
            "container_type": "ModelONEXContainer",
            "cache_enabled": self.enable_performance_cache,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        if self.tool_cache:
            stats["tool_cache"] = self.tool_cache.get_cache_stats()

        if self.performance_monitor:
            stats["performance_monitoring"] = (
                self.performance_monitor.get_monitoring_dashboard()
            )

        return stats

    async def run_performance_checkpoint(self, phase_name: str = "production") -> dict:
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
            "Enhanced ONEX container closed",
            event_type="enhanced_container_close",
        )


# Global enhanced container instance
_enhanced_container: ModelONEXContainer | None = None


async def create_enhanced_container(
    enable_cache: bool = True,
    cache_dir: Path | None = None,
) -> ModelONEXContainer:
    """Create enhanced container with performance optimizations."""
    container = ModelONEXContainer(
        enable_performance_cache=enable_cache,
        cache_dir=cache_dir,
    )

    # Apply standard container configuration
    await container.init()

    # Warm up caches for better performance
    if enable_cache:
        await container.warm_cache()

    return container


async def get_enhanced_container() -> ModelONEXContainer:
    """Get global enhanced container instance."""
    global _enhanced_container

    if _enhanced_container is None:
        _enhanced_container = await create_enhanced_container()

    return _enhanced_container


def get_enhanced_container_sync() -> ModelONEXContainer:
    """Get enhanced container synchronously."""
    return asyncio.run(get_enhanced_container())


async def main():
    """Demonstrate enhanced container with Codanna optimizations."""

    # Create enhanced container
    container = await create_enhanced_container(
        enable_cache=True,
        cache_dir=Path("/tmp/demo_enhanced_cache"),
    )

    # Test service resolutions

    test_services = [
        ("contract_validator_registry", "Contract Validator"),
        ("file_writer_registry", "File Writer"),
        ("logger_engine_registry", "Logger Engine"),
        ("smart_log_formatter_registry", "Smart Log Formatter"),
    ]

    for service_name, _display_name in test_services:
        start_time = time.perf_counter()

        try:
            container.get_service(object, service_name)
            end_time = time.perf_counter()
            (end_time - start_time) * 1000

        except Exception:
            end_time = time.perf_counter()
            (end_time - start_time) * 1000

    # Show performance statistics

    stats = container.get_performance_stats()

    if "tool_cache" in stats:
        stats["tool_cache"]

    if "performance_monitoring" in stats:
        perf_stats = stats["performance_monitoring"]

        target_status = perf_stats.get("target_status", {})
        for _target, _met in target_status.items():
            pass

    # Run performance checkpoint

    try:
        # This would work with proper baseline data
        await container.run_performance_checkpoint(
            "demo_enhanced_container",
        )
    except Exception:
        pass

    # Show optimization recommendations

    # Cleanup
    container.close()


if __name__ == "__main__":
    asyncio.run(main())
