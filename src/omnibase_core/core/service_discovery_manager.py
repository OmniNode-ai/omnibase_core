"""
Service Discovery Manager

Manages service discovery and resolution with protocol-based abstraction.
Provides fallback strategies and service caching for ONEX container.
"""

from typing import Dict, List, Optional, TypeVar

from omnibase_spi import ProtocolLogger

from omnibase_core.core.core_error_codes import CoreErrorCode
from omnibase_core.core.decorators import allow_dict_str_any
from omnibase_core.core.hybrid_event_bus_factory import create_hybrid_event_bus
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.exceptions import OnexError
from omnibase_core.protocol.protocol_service_discovery import ProtocolServiceDiscovery
from omnibase_core.services.protocol_service_resolver import resolve_service_discovery

T = TypeVar("T")


class ServiceDiscoveryManager:
    """
    Manages service discovery and resolution with protocol-based abstraction.
    """

    @allow_dict_str_any("static configuration requires flexible structure")
    def __init__(
        self,
        static_config: dict[str, object],
        logger: ProtocolLogger,
    ):
        self.static_config = static_config
        self.logger = logger
        self.service_cache: dict[
            str,
            object,
        ] = {}  # allow_dict_str_any: service cache needs flexible typing
        self._service_discovery: Optional[ProtocolServiceDiscovery] = None

    async def resolve_service(
        self,
        protocol_type: type[T],
        service_name: str | None = None,
    ) -> T:
        """
        Resolve service instance with Consul discovery and fallback.

        Args:
            protocol_type: Protocol interface to resolve
            service_name: Optional Consul service name

        Returns:
            Service implementation instance
        """
        protocol_name = protocol_type.__name__
        cache_key = f"{protocol_name}:{service_name or 'default'}"

        # Check cache first
        if cache_key in self.service_cache:
            from typing import cast

            cached_service = self.service_cache[cache_key]
            return cast("T", cached_service)

        try:
            # Try protocol-based service discovery if service name provided
            if service_name and await self._is_service_discovery_available():
                service = await self._discover_from_service_discovery(
                    protocol_type, service_name
                )
                if service:
                    self.service_cache[cache_key] = service
                    return service
        except Exception as e:
            self.logger.emit_log_event_sync(
                level=LogLevel.WARNING,
                message=f"Service discovery failed for {service_name}: {e}",
                event_type="service_discovery_failed",
            )

        # Fallback to static configuration
        service = self._resolve_from_static_config(protocol_type)
        if service:
            self.service_cache[cache_key] = service
            return service

        # Create fallback implementation
        fallback_service = self._create_fallback_service(protocol_type)
        if fallback_service:
            self.service_cache[cache_key] = fallback_service
            return fallback_service

        msg = f"Unable to resolve service for protocol {protocol_name}"
        raise OnexError(
            msg,
            error_code=CoreErrorCode.SERVICE_RESOLUTION_FAILED,
        )

    async def _get_service_discovery(self) -> ProtocolServiceDiscovery:
        """Get service discovery implementation with caching."""
        if self._service_discovery is None:
            self._service_discovery = await resolve_service_discovery()
        return self._service_discovery

    async def _is_service_discovery_available(self) -> bool:
        """Check if service discovery is available."""
        try:
            service_discovery = await self._get_service_discovery()
            health = await service_discovery.get_service_health("self")
            return health.status == "healthy"
        except Exception:
            return False

    async def _discover_from_service_discovery(
        self,
        protocol_type: type[T],
        service_name: str,
    ) -> T | None:
        """Discover service instance from protocol-based service discovery."""
        try:
            service_discovery = await self._get_service_discovery()
            services = await service_discovery.discover_services(service_name)

            if services:
                # Use first available service
                service_info = services[0]
                return self._create_service_client(protocol_type, service_info)
            return None
        except Exception as e:
            self.logger.emit_log_event_sync(
                level=LogLevel.WARNING,
                message=f"Service discovery lookup failed: {e}",
                event_type="service_discovery_lookup_failed",
            )
            return None

    def _create_service_client(
        self,
        protocol_type: type[T],
        service_info: Dict[str, object],
    ) -> T:
        """Create service client from discovered service information."""
        # Build service URL from discovered service
        # base_url = f"http://{service_info.get('address')}:{service_info.get('port')}"  # Future use

        # This would be expanded with actual service client factories
        # based on protocol types discovered in contracts

        if "Logger" in protocol_type.__name__:
            from omnibase_core.tools.logging.tool_logger_engine.v1_0_0.node import (
                ToolLoggerEngineNode,
            )

            return ToolLoggerEngineNode()

        # Add more protocol-to-implementation mappings here
        # These would be auto-generated from contract analysis

        msg = f"No service client factory for protocol {protocol_type.__name__}"
        raise OnexError(
            msg,
            error_code=CoreErrorCode.SERVICE_RESOLUTION_FAILED,
        )

    def _resolve_from_static_config(self, protocol_type: type[T]) -> T | None:
        """Resolve service from static configuration."""
        protocol_name = protocol_type.__name__

        # Check static configuration for this protocol
        if protocol_name in self.static_config:
            config = self.static_config[protocol_name]
            return self._create_static_service(protocol_type, config)

        return None

    @allow_dict_str_any("service configuration requires flexible structure")
    def _create_static_service(
        self,
        protocol_type: type[T],
        config: dict[str, object],
    ) -> T:
        """Create service from static configuration."""
        # Service type from configuration
        # service_type = config.get("type", "default")  # Future use

        # This would be expanded with static service factories
        # based on protocol types and configurations from contracts

        if "Logger" in protocol_type.__name__:
            from omnibase_core.tools.logging.tool_logger_engine.v1_0_0.node import (
                ToolLoggerEngineNode,
            )

            return ToolLoggerEngineNode()

        msg = f"No static service factory for protocol {protocol_type.__name__}"
        raise OnexError(
            msg,
            error_code=CoreErrorCode.SERVICE_RESOLUTION_FAILED,
        )

    def _create_fallback_service(self, protocol_type: type[T]) -> T | None:
        """Create fallback service implementation."""
        protocol_name = protocol_type.__name__

        # Provide basic fallback implementations
        if "Logger" in protocol_name:
            from omnibase_core.core.bootstrap_logger import create_basic_logger

            return create_basic_logger()

        # EventBus resolution using memory-based event bus
        if "EventBus" in protocol_name or protocol_name == "event_bus":
            from typing import cast

            event_bus = create_hybrid_event_bus()
            return cast("T | None", event_bus)

        # More fallbacks would be added here based on common protocols
        return None
