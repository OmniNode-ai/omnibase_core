#!/usr/bin/env python3
"""
Protocol-based Service Resolver

Resolves external dependencies through protocol abstractions with
automatic fallback strategies and unified configuration management.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional, TypeVar, get_type_hints

from omnibase_core.config.unified_config_manager import get_config
from omnibase_core.model.service.model_service_cache_stats import (
    ModelServiceCacheEntry,
    ModelServiceCacheStats,
)
from omnibase_core.model.service.model_service_health import ModelServiceHealth
from omnibase_core.model.service.model_service_health_aggregate import (
    ModelServiceHealthAggregate,
    ModelServiceHealthSummary,
)
from omnibase_core.protocol.protocol_database_connection import (
    ProtocolDatabaseConnection,
)
from omnibase_core.protocol.protocol_service_discovery import ProtocolServiceDiscovery
from omnibase_core.services.consul_service_discovery import ConsulServiceDiscovery
from omnibase_core.services.memory_database import InMemoryDatabase
from omnibase_core.services.memory_service_discovery import InMemoryServiceDiscovery
from omnibase_core.services.postgresql_database import PostgreSQLDatabase

T = TypeVar("T")

logger = logging.getLogger(__name__)


class ProtocolServiceResolver:
    """
    Protocol-based service resolver with automatic fallback strategies.

    Resolves services through protocol abstractions, automatically handling
    fallbacks when external dependencies are unavailable.
    """

    def __init__(self):
        self._service_cache: Dict[str, Any] = {}
        self._fallback_cache: Dict[str, Any] = {}
        self._config = get_config()
        self._initialized_services: Dict[str, bool] = {}

    async def resolve_service(self, protocol_type: type[T]) -> T:
        """
        Resolve service implementation for protocol with fallback.

        Args:
            protocol_type: Protocol interface to resolve

        Returns:
            Service implementation instance

        Raises:
            RuntimeError: If no implementation can be resolved
        """
        protocol_name = protocol_type.__name__

        # Check cache first
        if protocol_name in self._service_cache:
            return self._service_cache[protocol_name]

        # Resolve primary implementation
        try:
            service = await self._resolve_primary_implementation(protocol_type)
            if service:
                # Test the service
                if await self._test_service_connectivity(service):
                    self._service_cache[protocol_name] = service
                    logger.info(
                        f"Successfully resolved {protocol_name} with primary implementation"
                    )
                    return service
                else:
                    logger.warning(
                        f"Primary {protocol_name} implementation failed connectivity test"
                    )
        except Exception as e:
            logger.warning(
                f"Failed to resolve primary {protocol_name} implementation: {e}"
            )

        # Fallback to in-memory implementation
        try:
            fallback_service = await self._resolve_fallback_implementation(
                protocol_type
            )
            if fallback_service:
                self._service_cache[protocol_name] = fallback_service
                self._fallback_cache[protocol_name] = fallback_service
                logger.info(
                    f"Successfully resolved {protocol_name} with fallback implementation"
                )
                return fallback_service
        except Exception as e:
            logger.error(
                f"Failed to resolve fallback {protocol_name} implementation: {e}"
            )

        raise RuntimeError(f"Unable to resolve any implementation for {protocol_name}")

    async def _resolve_primary_implementation(
        self, protocol_type: type[T]
    ) -> Optional[T]:
        """Resolve primary implementation based on protocol type."""
        protocol_name = protocol_type.__name__

        if protocol_name == "ProtocolServiceDiscovery":
            return await self._create_consul_service_discovery()
        elif protocol_name == "ProtocolDatabaseConnection":
            return await self._create_postgresql_database()

        return None

    async def _resolve_fallback_implementation(
        self, protocol_type: type[T]
    ) -> Optional[T]:
        """Resolve fallback implementation based on protocol type."""
        protocol_name = protocol_type.__name__

        if protocol_name == "ProtocolServiceDiscovery":
            return await self._create_memory_service_discovery()
        elif protocol_name == "ProtocolDatabaseConnection":
            return await self._create_memory_database()

        return None

    async def _create_consul_service_discovery(
        self,
    ) -> Optional[ConsulServiceDiscovery]:
        """Create Consul service discovery instance."""
        try:
            service = ConsulServiceDiscovery()

            # Configure from unified config
            sd_config = self._config.service_discovery
            service.configure(
                consul_url=sd_config.consul_url,
                datacenter=sd_config.consul_datacenter,
                timeout=sd_config.consul_timeout,
                token=sd_config.consul_token,
            )

            # Initialize the service
            if await service.connect():
                return service
            else:
                logger.warning("Failed to connect to Consul service discovery")
                return None

        except Exception as e:
            logger.error(f"Error creating Consul service discovery: {e}")
            return None

    async def _create_postgresql_database(self) -> Optional[PostgreSQLDatabase]:
        """Create PostgreSQL database instance."""
        try:
            service = PostgreSQLDatabase()

            # Configure from unified config
            db_config = self._config.database
            await service.configure(
                dsn=db_config.postgres_dsn,
                min_connections=db_config.postgres_min_connections,
                max_connections=db_config.postgres_max_connections,
                connection_timeout=db_config.postgres_connection_timeout,
                command_timeout=db_config.postgres_command_timeout,
            )

            # Initialize the service
            if await service.connect():
                return service
            else:
                logger.warning("Failed to connect to PostgreSQL database")
                return None

        except Exception as e:
            logger.error(f"Error creating PostgreSQL database: {e}")
            return None

    async def _create_memory_service_discovery(self) -> InMemoryServiceDiscovery:
        """Create in-memory service discovery instance."""
        service = InMemoryServiceDiscovery()
        await service.connect()
        return service

    async def _create_memory_database(self) -> InMemoryDatabase:
        """Create in-memory database instance."""
        service = InMemoryDatabase()
        await service.connect()
        return service

    async def _test_service_connectivity(self, service: Any) -> bool:
        """Test service connectivity with health check."""
        try:
            if hasattr(service, "health_check"):
                health = await service.health_check()
                return health.status == "healthy"
            elif hasattr(service, "connect"):
                # If service has connect method, test it
                return await service.connect()
            else:
                # Assume service is healthy if no health check available
                return True
        except Exception as e:
            logger.warning(f"Service connectivity test failed: {e}")
            return False

    def is_using_fallback(self, protocol_type: type[T]) -> bool:
        """Check if protocol is using fallback implementation."""
        protocol_name = protocol_type.__name__
        return protocol_name in self._fallback_cache

    async def get_service_health(self, protocol_type: type[T]) -> ModelServiceHealth:
        """Get health status for service."""
        protocol_name = protocol_type.__name__
        try:
            service = await self.resolve_service(protocol_type)
            if hasattr(service, "health_check"):
                health = await service.health_check()
                # Adapt health check result to ModelServiceHealth
                return ModelServiceHealth(
                    service_name=protocol_name,
                    service_type="custom",  # Can be enhanced with mapping
                    status="reachable" if getattr(health, "status", "unknown") == "healthy" else "error",
                    connection_string=f"protocol://{protocol_name}",
                    last_check_time=getattr(health, "last_check", datetime.now().isoformat()),
                    error_message=getattr(health, "error_message", None),
                )
            else:
                return ModelServiceHealth(
                    service_name=protocol_name,
                    service_type="custom",
                    status="reachable",  # Assume healthy if no health check
                    connection_string=f"protocol://{protocol_name}",
                    last_check_time=datetime.now().isoformat(),
                )
        except Exception as e:
            return ModelServiceHealth(
                service_name=protocol_name,
                service_type="custom",
                status="error",
                connection_string=f"protocol://{protocol_name}",
                error_message=str(e),
                last_check_time=datetime.now().isoformat(),
            )

    async def get_all_service_health(self) -> ModelServiceHealthAggregate:
        """Get health status for all resolved services."""
        health_statuses = {}
        errors = []
        start_time = datetime.now()

        # Check service discovery
        if "ProtocolServiceDiscovery" in self._service_cache:
            try:
                health_statuses["service_discovery"] = await self.get_service_health(
                    ProtocolServiceDiscovery
                )
            except Exception as e:
                errors.append(f"Failed to check service_discovery: {str(e)}")

        # Check database
        if "ProtocolDatabaseConnection" in self._service_cache:
            try:
                health_statuses["database"] = await self.get_service_health(
                    ProtocolDatabaseConnection
                )
            except Exception as e:
                errors.append(f"Failed to check database: {str(e)}")

        # Calculate duration
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        aggregate = ModelServiceHealthAggregate(
            services=health_statuses,
            check_timestamp=datetime.now(),
            check_duration_ms=duration_ms,
            errors=errors,
            summary=ModelServiceHealthSummary(
                total_services=len(self._service_cache),
                healthy_services=sum(1 for s in health_statuses.values() if s.is_healthy()),
                unhealthy_services=sum(1 for s in health_statuses.values() if s.is_unhealthy()),
                degraded_services=sum(1 for s in health_statuses.values() if s.is_degraded()),
                unknown_services=0,
                overall_status="all_healthy" if all(s.is_healthy() for s in health_statuses.values()) else "partial_healthy",
                last_check_timestamp=datetime.now(),
            ),
        )
        
        # Recalculate summary with proper statistics
        aggregate.summary = aggregate.calculate_summary()
        return aggregate

    async def refresh_service(self, protocol_type: type[T]) -> T:
        """Force refresh service resolution (bypass cache)."""
        protocol_name = protocol_type.__name__

        # Clear from caches
        if protocol_name in self._service_cache:
            del self._service_cache[protocol_name]
        if protocol_name in self._fallback_cache:
            del self._fallback_cache[protocol_name]

        # Re-resolve
        return await self.resolve_service(protocol_type)

    async def shutdown(self) -> None:
        """Shutdown all services and clean up resources."""
        for service_name, service in self._service_cache.items():
            try:
                if hasattr(service, "disconnect"):
                    await service.disconnect()
                elif hasattr(service, "close"):
                    await service.close()
                logger.info(f"Successfully shutdown {service_name}")
            except Exception as e:
                logger.error(f"Error shutting down {service_name}: {e}")

        self._service_cache.clear()
        self._fallback_cache.clear()

    def get_cache_stats(self) -> ModelServiceCacheStats:
        """Get cache statistics."""
        cache_entries = []
        
        # Build cache entries
        for protocol_name, service in self._service_cache.items():
            is_fallback = protocol_name in self._fallback_cache
            cache_entries.append(
                ModelServiceCacheEntry(
                    service_name=protocol_name,
                    protocol_type=type(service).__name__,
                    cached_at=datetime.now(),  # Would be better to track actual cache time
                    last_accessed=datetime.now(),  # Would be better to track actual access time
                    hit_count=self._initialized_services.get(protocol_name, 0),
                    is_fallback=is_fallback,
                )
            )
        
        return ModelServiceCacheStats(
            total_services=len(self._service_cache),
            primary_services=len(self._service_cache) - len(self._fallback_cache),
            fallback_services=len(self._fallback_cache),
            cache_entries=cache_entries,
            cache_hit_rate=0.0,  # Would need to track hits/misses for accurate rate
            total_hits=0,  # Would need to track for accurate stats
            total_misses=0,  # Would need to track for accurate stats
        )


# Global service resolver instance
_service_resolver: Optional[ProtocolServiceResolver] = None


def get_service_resolver() -> ProtocolServiceResolver:
    """Get global service resolver instance."""
    global _service_resolver
    if _service_resolver is None:
        _service_resolver = ProtocolServiceResolver()
    return _service_resolver


async def resolve_service_discovery() -> ProtocolServiceDiscovery:
    """Convenience function to resolve service discovery."""
    resolver = get_service_resolver()
    return await resolver.resolve_service(ProtocolServiceDiscovery)


async def resolve_database() -> ProtocolDatabaseConnection:
    """Convenience function to resolve database connection."""
    resolver = get_service_resolver()
    return await resolver.resolve_service(ProtocolDatabaseConnection)
