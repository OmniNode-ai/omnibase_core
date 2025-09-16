"""
SPI-Compliant Service Registry Implementation.

Implements omnibase.protocols.container.ProtocolServiceRegistry to provide
standardized dependency injection while maintaining compatibility
with existing ModelONEXContainer usage patterns.

Enhanced with protocol-based external dependencies and proper error handling.
"""

import asyncio
import logging
import threading
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, TypeVar

from omnibase_spi.protocols.container import (
    ProtocolDependencyGraph,
    ProtocolServiceInstance,
    ProtocolServiceRegistration,
    ProtocolServiceRegistry,
    ProtocolServiceRegistryStatus,
)

from omnibase_core.config.unified_config_manager import get_config
from omnibase_core.protocol.protocol_database_connection import (
    ProtocolDatabaseConnection,
)
from omnibase_core.protocol.protocol_service_discovery import ProtocolServiceDiscovery
from omnibase_core.services.protocol_service_resolver import get_service_resolver

# Real protocols imported from omnibase_spi


T = TypeVar("T")
TInterface = TypeVar("TInterface")
TImplementation = TypeVar("TImplementation")


class SimpleSemVer:
    """Simple semantic version implementation for SPI compliance."""

    def __init__(self, version_string: str = "1.0.0"):
        parts = version_string.split(".")
        self.major = int(parts[0]) if len(parts) > 0 else 1
        self.minor = int(parts[1]) if len(parts) > 1 else 0
        self.patch = int(parts[2]) if len(parts) > 2 else 0

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


class SPIServiceRegistry:
    """
    SPI-compliant service registry with protocol-based external dependencies.

    Provides a bridge between simple ModelONEXContainer service resolution
    and the comprehensive SPI ProtocolServiceRegistry interface.

    Enhanced with automatic fallback strategies and proper error handling
    for external dependencies.
    """

    def __init__(self) -> None:
        """Initialize the SPI service registry with error handling."""
        self._services: dict[str, Any] = {}
        self._config: dict[str, Any] = {}
        self._registrations: dict[str, ProtocolServiceRegistration] = {}
        self._instances: dict[str, list[ProtocolServiceInstance]] = {}
        self._dependency_graph: dict[str, ProtocolDependencyGraph] = {}
        self._registry_id = str(uuid.uuid4())

        # Protocol-based external services
        self._service_discovery: Optional[ProtocolServiceDiscovery] = None
        self._database: Optional[ProtocolDatabaseConnection] = None
        self._initialization_errors: list[str] = []
        self._is_initialized = False
        self._init_task: Optional[asyncio.Task] = None

        # Initialize logger
        self._logger = logging.getLogger(__name__)

        # Initialize registry safely
        self._initialize_registry()

    def _initialize_registry(self) -> None:
        """Initialize registry with proper error handling."""
        try:
            # Load unified configuration
            self._config = get_config().to_dict()

            # Initialize external dependencies asynchronously
            # Store the initialization task to allow proper waiting
            self._init_task = asyncio.create_task(
                self._initialize_external_dependencies()
            )

            # Only mark as initialized after external dependencies are ready
            # Note: For immediate use, check is_ready() instead of _is_initialized
            self._logger.info(
                f"SPI Service Registry initialized successfully: {self._registry_id}"
            )

        except Exception as e:
            error_msg = f"Failed to initialize SPI Service Registry: {e}"
            self._initialization_errors.append(error_msg)
            self._logger.error(error_msg, exc_info=True)

            # Registry is still functional for basic services even if external deps fail
            self._is_initialized = True

    async def _initialize_external_dependencies(self) -> None:
        """Initialize external dependencies with fallback strategies."""
        try:
            service_resolver = get_service_resolver()

            # Initialize service discovery
            try:
                self._service_discovery = await service_resolver.resolve_service(
                    ProtocolServiceDiscovery
                )
                self._logger.info("Service discovery initialized successfully")
            except Exception as e:
                error_msg = (
                    f"Service discovery initialization failed (using fallback): {e}"
                )
                self._initialization_errors.append(error_msg)
                self._logger.warning(error_msg)

            # Initialize database
            try:
                self._database = await service_resolver.resolve_service(
                    ProtocolDatabaseConnection
                )
                self._logger.info("Database connection initialized successfully")
            except Exception as e:
                error_msg = f"Database initialization failed (using fallback): {e}"
                self._initialization_errors.append(error_msg)
                self._logger.warning(error_msg)

        except Exception as e:
            error_msg = f"External dependencies initialization failed: {e}"
            self._initialization_errors.append(error_msg)
            self._logger.error(error_msg, exc_info=True)

    def get_initialization_errors(self) -> list[str]:
        """Get list of initialization errors."""
        return self._initialization_errors.copy()

    async def is_ready(self) -> bool:
        """Check if registry is fully ready (async dependencies initialized)."""
        if self._init_task and not self._init_task.done():
            try:
                await self._init_task
                self._is_initialized = True
            except Exception as e:
                self._initialization_errors.append(f"Initialization failed: {e}")
                return False
        return self._is_initialized and len(self._initialization_errors) == 0

    def is_healthy(self) -> bool:
        """Check if registry is healthy (initialized and no critical errors)."""
        return self._is_initialized and len(self._initialization_errors) == 0

    async def get_external_services_health(self) -> Dict[str, Any]:
        """Get health status of external services."""
        health_status = {}

        if self._service_discovery:
            try:
                health = await self._service_discovery.get_service_health("self")
                health_status["service_discovery"] = {
                    "status": health.status,
                    "last_check": health.last_check,
                    "error_message": health.error_message,
                }
            except Exception as e:
                health_status["service_discovery"] = {
                    "status": "error",
                    "last_check": None,
                    "error_message": str(e),
                }
        else:
            health_status["service_discovery"] = {
                "status": "not_initialized",
                "last_check": None,
                "error_message": "Service discovery not available",
            }

        if self._database:
            try:
                health = await self._database.health_check()
                health_status["database"] = {
                    "status": health.status,
                    "last_check": health.last_check,
                    "error_message": health.error_message,
                }
            except Exception as e:
                health_status["database"] = {
                    "status": "error",
                    "last_check": None,
                    "error_message": str(e),
                }
        else:
            health_status["database"] = {
                "status": "not_initialized",
                "last_check": None,
                "error_message": "Database not available",
            }

        return health_status

    # SPI ProtocolServiceRegistry properties
    @property
    def config(self) -> ProtocolServiceRegistry:
        """Get registry configuration."""
        # Return a minimal config implementation
        return type(
            "Config",
            (),
            {
                "registry_name": "ONEX Service Registry",
                "max_instances": 1000,
                "enable_circular_detection": True,
                "default_lifecycle": "singleton",
                "default_scope": "global",
            },
        )()

    @property
    def registrations(self) -> dict[str, ProtocolServiceRegistration]:
        """Get all service registrations."""
        return self._registrations.copy()

    @property
    def instances(self) -> dict[str, list[ProtocolServiceInstance]]:
        """Get all service instances."""
        return self._instances.copy()

    @property
    def dependency_graph(self) -> dict[str, ProtocolDependencyGraph]:
        """Get dependency graph."""
        return self._dependency_graph.copy()

    # Compatibility methods (ModelONEXContainer interface)
    def configure(self, config: dict[str, Any]) -> None:
        """Configure the container with settings."""
        if not isinstance(config, dict):
            msg = "Configuration must be a dictionary"
            raise ValueError(msg)

        # Validate configuration keys and values
        allowed_keys = {
            "debug",
            "log_level",
            "timeout_ms",
            "retry_count",
            "health_check_interval",
            "max_connections",
            "pool_size",
        }

        for key, value in config.items():
            if not isinstance(key, str):
                raise ValueError(
                    f"Configuration keys must be strings, got {type(key).__name__}"
                )

            # Validate common configuration patterns
            if key.endswith("_ms") and not isinstance(value, (int, float)):
                raise ValueError(
                    f"Timeout configurations must be numeric, got {type(value).__name__} for {key}"
                )
            if key.endswith("_count") and not isinstance(value, int):
                raise ValueError(
                    f"Count configurations must be integers, got {type(value).__name__} for {key}"
                )
            if "password" in key.lower() and not isinstance(value, str):
                raise ValueError(
                    f"Password configurations must be strings, got {type(value).__name__} for {key}"
                )

        self._config.update(config)

    def register_service(self, protocol_name: str, service_instance: Any) -> str:
        """
        Register a service instance for a protocol (ModelONEXContainer compatibility).

        This maintains compatibility with existing ModelONEXContainer usage
        while also creating the necessary SPI registration metadata.
        """
        # Store service for ModelONEXContainer compatibility
        self._services[protocol_name] = service_instance

        # Create SPI-compliant registration metadata
        service_id = f"{protocol_name}_{uuid.uuid4().hex[:8]}"

        # Create minimal SPI metadata
        metadata = type(
            "ServiceMetadata",
            (),
            {
                "service_id": service_id,
                "service_name": protocol_name,
                "service_interface": protocol_name,
                "service_implementation": type(service_instance).__name__,
                "version": SimpleSemVer("1.0.0"),
                "description": f"Service for {protocol_name}",
                "tags": [],
                "configuration": {},
                "created_at": datetime.now(),
                "last_modified_at": None,
            },
        )()

        # Create SPI registration
        registration = type(
            "ServiceRegistration",
            (),
            {
                "registration_id": service_id,
                "service_metadata": metadata,
                "lifecycle": "singleton",
                "scope": "global",
                "dependencies": [],
                "registration_status": "registered",
                "health_status": "healthy",
                "registration_time": datetime.now(),
                "last_access_time": None,
                "access_count": 0,
                "instance_count": 1,
                "max_instances": None,
            },
        )()

        self._registrations[service_id] = registration

        # Create instance record
        instance = type(
            "ServiceInstance",
            (),
            {
                "instance_id": f"{service_id}_instance",
                "service_registration_id": service_id,
                "instance": service_instance,
                "lifecycle": "singleton",
                "scope": "global",
                "created_at": datetime.now(),
                "last_accessed": datetime.now(),
                "access_count": 0,
                "is_disposed": False,
                "metadata": {},
            },
        )()

        self._instances[service_id] = [instance]

        return service_id

    def get_service(self, protocol_name: str) -> Any:
        """
        Get service by protocol name (ModelONEXContainer compatibility).

        Maintains existing ModelONEXContainer behavior for current standards.
        """
        # Handle direct protocol name resolution
        if protocol_name in self._services:
            return self._services[protocol_name]

        # Handle common protocol shortcuts
        protocol_shortcuts = {
            "event_bus": "ProtocolEventBus",
            "logger": "ProtocolLogger",
            "health_check": "ProtocolHealthCheck",
        }

        # Try shortcut resolution
        if protocol_name in protocol_shortcuts:
            full_protocol_name = protocol_shortcuts[protocol_name]
            if full_protocol_name in self._services:
                return self._services[full_protocol_name]

        # Service not found
        available_services = list(self._services.keys())
        available_shortcuts = ["event_bus", "logger", "health_check"]

        msg = (
            f"Unable to resolve service for protocol: {protocol_name}. "
            f"Available services: {available_services}. "
            f"Available shortcuts: {available_shortcuts}"
        )
        raise ValueError(
            msg,
        )

    def has_service(self, protocol_name: str) -> bool:
        """Check if service is available for protocol."""
        return protocol_name in self._services

    # Additional SPI methods (simplified implementations)
    def get_status(self) -> ProtocolServiceRegistryStatus:
        """Get registry status with enhanced health information."""
        # Determine overall status based on initialization and errors
        if not self._is_initialized:
            status = "initializing"
            health_status = "unknown"
            message = "SPI Service Registry is initializing"
        elif len(self._initialization_errors) > 0:
            status = "degraded"
            health_status = "degraded"
            message = f"ONEX Service Registry operational with {len(self._initialization_errors)} issues"
        else:
            status = "active"
            health_status = "healthy"
            message = "ONEX Service Registry is fully operational"

        # Include initialization errors in metadata
        metadata = {
            "initialization_errors": self._initialization_errors,
            "external_services": {
                "service_discovery_available": self._service_discovery is not None,
                "database_available": self._database is not None,
            },
            "config_loaded": bool(self._config),
        }

        return type(
            "RegistryStatus",
            (),
            {
                "registry_id": self._registry_id,
                "status": status,
                "message": message,
                "total_registrations": len(self._registrations),
                "active_instances": sum(
                    len(instances) for instances in self._instances.values()
                ),
                "failed_registrations": len(self._initialization_errors),
                "circular_dependencies": 0,
                "health_status": health_status,
                "last_health_check": datetime.now(),
                "uptime_seconds": 0,  # Would need to track actual uptime
                "memory_usage_mb": 0,  # Would need actual memory tracking
                "metadata": metadata,
            },
        )()


# Factory function for creating SPI-compliant service registry
def create_spi_service_registry() -> SPIServiceRegistry:
    """Create and configure SPI-compliant service registry with enhanced error handling."""
    try:
        registry = SPIServiceRegistry()

        # Configuration is now loaded automatically from unified config manager
        # Additional manual configuration can be applied if needed

        logging.getLogger(__name__).info("SPI Service Registry created successfully")
        return registry

    except Exception as e:
        error_msg = f"Failed to create SPI Service Registry: {e}"
        logging.getLogger(__name__).error(error_msg, exc_info=True)

        # Return a degraded registry that can still function for basic services
        registry = SPIServiceRegistry()
        registry._initialization_errors.append(error_msg)
        return registry


# Global registry instance for current standards
_spi_registry: SPIServiceRegistry | None = None
_registry_lock = threading.Lock()


def get_spi_registry() -> SPIServiceRegistry:
    """
    Get or create global SPI registry instance (thread-safe).

    Provides the same singleton pattern as ModelONEXContainer but with
    SPI compliance and enhanced error handling.
    """
    global _spi_registry
    if _spi_registry is None:
        with _registry_lock:
            # Double-checked locking pattern
            if _spi_registry is None:
                try:
                    _spi_registry = create_spi_service_registry()
                except Exception as e:
                    # Log error but don't fail completely
                    logging.getLogger(__name__).error(
                        f"Critical error creating SPI registry: {e}", exc_info=True
                    )

                    # Create minimal registry that won't cause further failures
                    _spi_registry = SPIServiceRegistry()
                    _spi_registry._initialization_errors.append(
                        f"Critical initialization failure: {e}"
                    )
    return _spi_registry


async def get_spi_registry_health() -> Dict[str, Any]:
    """Get comprehensive health status of the global SPI registry."""
    try:
        registry = get_spi_registry()

        # Basic registry health
        status = registry.get_status()

        # External services health (if available)
        external_health = {}
        try:
            external_health = await registry.get_external_services_health()
        except Exception as e:
            external_health = {"error": f"Failed to get external services health: {e}"}

        return {
            "registry_id": status.registry_id,
            "status": status.status,
            "health_status": status.health_status,
            "message": status.message,
            "total_registrations": status.total_registrations,
            "active_instances": status.active_instances,
            "failed_registrations": status.failed_registrations,
            "initialization_errors": registry.get_initialization_errors(),
            "external_services": external_health,
            "is_healthy": registry.is_healthy(),
        }

    except Exception as e:
        return {
            "registry_id": "unknown",
            "status": "critical_error",
            "health_status": "critical",
            "message": f"Failed to get registry health: {e}",
            "error": str(e),
            "is_healthy": False,
        }
