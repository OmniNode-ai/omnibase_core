"""
Registry Injection Mixin for ONEX Tool Nodes.

Provides automatic registry dependency injection and validation.
Handles common registry patterns and protocol enforcement.
"""

from typing import Generic, Protocol, TypeVar

from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.core.errors.core_errors import CoreErrorCode
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.exceptions import OnexError
from omnibase_core.protocol.protocol_registry import ProtocolRegistry

# Type variable for registry protocol
RegistryT = TypeVar("RegistryT", bound=ProtocolRegistry)


class ProtocolRegistryAware(Protocol):
    """Protocol for classes that can accept a registry."""

    registry: ProtocolRegistry | None


class MixinRegistryInjection(Generic[RegistryT]):
    """
    Mixin that provides registry injection and validation.

    Features:
    - Type-safe registry injection
    - Automatic protocol validation
    - Registry health checking
    - Fail-fast on invalid registries

    Usage:
        class MyTool(MixinRegistryInjection[MyCustomRegistry], ProtocolReducer):
            def __init__(self, registry: Optional[MyCustomRegistry] = None, **kwargs):
                super().__init__(**kwargs)
                self.registry = registry

            def process(self, input_state):
                # Registry is validated and ready to use
                service = self.registry.get_service("my_service")
    """

    def __init__(self, **kwargs):
        """Initialize the registry injection mixin."""
        super().__init__(**kwargs)

        # Registry will be set via property
        self._registry: RegistryT | None = None
        self._registry_validated: bool = False

        emit_log_event(
            LogLevel.DEBUG,
            "🏗️ MIXIN_INIT: Initializing MixinRegistryInjection",
            {
                "mixin_class": self.__class__.__name__,
                "has_registry": hasattr(self, "registry"),
            },
        )

    @property
    def registry(self) -> RegistryT | None:
        """Get the injected registry."""
        return self._registry

    @registry.setter
    def registry(self, value: RegistryT | None) -> None:
        """Set and validate the registry."""
        emit_log_event(
            LogLevel.DEBUG,
            "🔧 REGISTRY_INJECTION: Setting registry",
            {
                "node_class": self.__class__.__name__,
                "registry_type": type(value).__name__ if value else "None",
                "is_none": value is None,
            },
        )

        self._registry = value

        if value is not None:
            # Validate registry on injection
            self._validate_registry()

    def _validate_registry(self) -> None:
        """Validate the injected registry meets protocol requirements."""
        if self._registry_validated:
            return

        emit_log_event(
            LogLevel.INFO,
            "🔍 REGISTRY_VALIDATION: Starting registry validation",
            {
                "node_class": self.__class__.__name__,
                "registry_type": type(self._registry).__name__,
            },
        )

        # Check if registry implements required protocol using duck typing
        required_methods = ["get_service", "register_service", "health_check"]
        missing_methods = [
            method for method in required_methods if not hasattr(self._registry, method)
        ]

        if missing_methods:
            error_msg = (
                f"Registry missing required methods: {missing_methods}. "
                f"Registry type: {type(self._registry)}"
            )
            emit_log_event(
                LogLevel.ERROR,
                f"❌ REGISTRY_VALIDATION: {error_msg}",
                {
                    "registry_type": type(self._registry).__name__,
                    "missing_methods": missing_methods,
                },
            )
            raise TypeError(error_msg)

        # Check registry health
        health_status = self._check_registry_health()
        if health_status not in [EnumOnexStatus.SUCCESS, EnumOnexStatus.UNKNOWN]:
            error_msg = f"Registry is not healthy: {health_status}"
            emit_log_event(
                LogLevel.ERROR,
                f"❌ REGISTRY_VALIDATION: {error_msg}",
                {
                    "health_status": health_status.value,
                    "registry_type": type(self._registry).__name__,
                },
            )
            raise OnexError(error_msg, error_code=CoreErrorCode.SERVICE_UNHEALTHY)

        self._registry_validated = True

        emit_log_event(
            LogLevel.INFO,
            "✅ REGISTRY_VALIDATION: Registry validated successfully",
            {
                "node_class": self.__class__.__name__,
                "registry_type": type(self._registry).__name__,
            },
        )

    def _check_registry_health(self) -> EnumOnexStatus:
        """Check health of the injected registry."""
        if self._registry is None:
            return EnumOnexStatus.UNKNOWN

        # Check if registry has health check method
        if hasattr(self._registry, "health_check"):
            try:
                health = self._registry.health_check()
                return (
                    health.status
                    if hasattr(health, "status")
                    else EnumOnexStatus.SUCCESS
                )
            except Exception as e:
                emit_log_event(
                    LogLevel.WARNING,
                    f"Registry health check failed: {e}",
                    {"error": str(e)},
                )
                return EnumOnexStatus.ERROR

        # No health check available, assume success
        return EnumOnexStatus.SUCCESS

    def get_service(self, service_name: str) -> object | None:
        """Get a service from the registry with validation."""
        if self._registry is None:
            emit_log_event(
                LogLevel.WARNING,
                "No registry available for service lookup",
                {"service_name": service_name},
            )
            return None

        # Ensure registry is validated
        if not self._registry_validated:
            self._validate_registry()

        # Get service from registry
        if hasattr(self._registry, "get_service"):
            try:
                service = self._registry.get_service(service_name)
                emit_log_event(
                    LogLevel.DEBUG,
                    f"Retrieved service from registry: {service_name}",
                    {
                        "service_name": service_name,
                        "service_type": type(service).__name__ if service else "None",
                    },
                )
                return service
            except Exception as e:
                emit_log_event(
                    LogLevel.ERROR,
                    f"Failed to get service from registry: {e}",
                    {"service_name": service_name, "error": str(e)},
                )
                return None

        emit_log_event(
            LogLevel.WARNING,
            "Registry does not support get_service method",
            {"registry_type": type(self._registry).__name__},
        )
        return None

    def register_service(self, service_name: str, service: object) -> bool:
        """Register a service with the registry."""
        if self._registry is None:
            emit_log_event(
                LogLevel.WARNING,
                "No registry available for service registration",
                {"service_name": service_name},
            )
            return False

        # Ensure registry is validated
        if not self._registry_validated:
            self._validate_registry()

        # Register service
        if hasattr(self._registry, "register_service"):
            try:
                self._registry.register_service(service_name, service)
                emit_log_event(
                    LogLevel.INFO,
                    f"Registered service with registry: {service_name}",
                    {
                        "service_name": service_name,
                        "service_type": type(service).__name__,
                    },
                )
                return True
            except Exception as e:
                emit_log_event(
                    LogLevel.ERROR,
                    f"Failed to register service: {e}",
                    {"service_name": service_name, "error": str(e)},
                )
                return False

        emit_log_event(
            LogLevel.WARNING,
            "Registry does not support register_service method",
            {"registry_type": type(self._registry).__name__},
        )
        return False
