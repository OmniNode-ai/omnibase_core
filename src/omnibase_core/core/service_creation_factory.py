"""
Service Creation Factory.

Generic factory pattern implementation for managing service creation strategies.
Provides coordinated access to different service creation approaches with
proper type safety and generic support.
"""

from typing import Any, TypeVar, Generic, Protocol, Callable, cast, Type
from uuid import UUID, uuid4

from omnibase_core.core.protocols_service_creation import (
    ProtocolLoggingService,
    ProtocolRegistryService,
    ProtocolServiceCreationStrategy,
)
from omnibase_core.core.service_creation_strategies import (
    FallbackServiceCreationStrategy,
    MinimalLoggingServiceStrategy,
    ProtocolBasedLoggingServiceStrategy,
    RegistryServiceCreationStrategy,
)

# Type variables for generic factory patterns
T = TypeVar("T")  # Service type
P = TypeVar("P")  # Protocol type
S = TypeVar("S")  # Strategy type


class ServiceProvider(Protocol[T]):
    """Protocol for objects that can provide services."""

    def get_service(self, service_type: type[T]) -> T | None:
        """Get a service of the specified type."""
        ...

    def has_service(self, service_type: type[T]) -> bool:
        """Check if service of the specified type is available."""
        ...


class GenericServiceFactory(Generic[T]):
    """
    Generic service factory with type-safe service creation.

    Provides a foundation for creating type-safe service factories
    that can handle any service type while maintaining proper generics.
    """

    def __init__(self) -> None:
        """Initialize generic factory."""
        self._providers: list[ServiceProvider[T]] = []
        self._service_cache: dict[type[T], T] = {}
        self._factory_id: UUID = uuid4()

    def add_provider(self, provider: ServiceProvider[T]) -> None:
        """Add a service provider."""
        self._providers.append(provider)

    def remove_provider(self, provider: ServiceProvider[T]) -> bool:
        """Remove a service provider."""
        try:
            self._providers.remove(provider)
            return True
        except ValueError:
            return False

    def get_service(self, service_type: type[T]) -> T | None:
        """
        Get service with caching and type safety.

        Args:
            service_type: The service type to retrieve

        Returns:
            Service instance or None if not found
        """
        # Check cache first
        if service_type in self._service_cache:
            return self._service_cache[service_type]

        # Try providers
        for provider in self._providers:
            service = provider.get_service(service_type)
            if service is not None:
                # Cache the service
                self._service_cache[service_type] = service
                return service

        return None

    def clear_cache(self) -> None:
        """Clear the service cache."""
        self._service_cache.clear()

    def get_cached_services(self) -> dict[type[T], T]:
        """Get all cached services."""
        return self._service_cache.copy()


class TypedServiceCreationStrategy(Generic[T]):
    """
    Generic service creation strategy with type constraints.

    Provides a base for creating type-safe service creation strategies
    that work with specific service types.
    """

    def __init__(self, target_type: type[T]) -> None:
        """Initialize with target service type."""
        self._target_type = target_type
        self._strategy_name = f"TypedStrategy[{target_type.__name__}]"

    @property
    def strategy_name(self) -> str:
        """Get strategy name."""
        return self._strategy_name

    def can_create(self, service_type: type) -> bool:
        """Check if this strategy can create the service type."""
        return service_type == self._target_type or issubclass(service_type, self._target_type)

    def get_service(self, protocol_type: Type[T]) -> T | None:
        """
        Get service with type checking.

        Args:
            protocol_type: The protocol type to resolve

        Returns:
            Service implementation or None
        """
        if not self.can_create(protocol_type):
            return None

        return self.create_service(protocol_type)

    def create_service(self, protocol_type: type[T]) -> T | None:
        """
        Create service instance. Override in subclasses.

        Args:
            protocol_type: The protocol type to create

        Returns:
            Service instance or None
        """
        raise NotImplementedError("Subclasses must implement create_service")

    def is_available(self) -> bool:
        """Check if strategy is available. Override in subclasses."""
        return True


class ServiceCreationFactory:
    """
    Factory for coordinating service creation strategies.

    Manages multiple service creation strategies and selects the appropriate
    one based on availability and protocol type requirements.
    """

    def __init__(self) -> None:
        """Initialize factory with default strategies."""
        self._strategies: list[ProtocolServiceCreationStrategy] = []
        self._logging_strategies: list[ProtocolServiceCreationStrategy] = []
        self._registry: ProtocolRegistryService | None = None

    def set_registry(self, registry: ProtocolRegistryService | None) -> None:
        """
        Set the registry service and rebuild strategies.

        Args:
            registry: Registry service implementation or None
        """
        self._registry = registry
        self._rebuild_strategies()

    def get_service(self, protocol_type: type[T]) -> T | None:
        """
        Get service using appropriate strategy.

        Args:
            protocol_type: The protocol interface to resolve

        Returns:
            Service implementation or None if not found
        """
        # Special handling for logging services
        if self._is_logging_protocol(protocol_type):
            return self._get_logging_service(protocol_type)

        # Try general service strategies
        for strategy in self._strategies:
            if strategy.is_available():
                service = strategy.get_service(protocol_type)
                if service is not None:
                    return service

        return None

    def get_logging_service(self) -> ProtocolLoggingService | None:
        """
        Get logging service with special bootstrap handling.

        Returns:
            Logging service implementation or fallback
        """
        # Create a concrete implementation request instead of using abstract protocol
        from omnibase_core.core.service_creation_strategies import MinimalLoggingServiceStrategy

        # Try logging strategies first
        for strategy in self._logging_strategies:
            if strategy.is_available():
                # Use Any type for protocol compatibility
                from typing import Any
                service = strategy.get_service(cast(type[Any], ProtocolLoggingService))
                if service is not None:
                    return cast(ProtocolLoggingService, service)

        # Fallback to minimal logging
        fallback = MinimalLoggingServiceStrategy()
        result = fallback.get_service(cast(type[Any], ProtocolLoggingService))
        return cast(ProtocolLoggingService, result) if result else None

    def _get_logging_service(self, protocol_type: type[T]) -> T | None:
        """
        Get logging service using logging-specific strategies.

        Args:
            protocol_type: The logging protocol interface

        Returns:
            Logging service implementation
        """
        for strategy in self._logging_strategies:
            if strategy.is_available():
                service = strategy.get_service(protocol_type)
                if service is not None:
                    return service

        # Fallback to minimal logging if all else fails
        fallback_strategy = MinimalLoggingServiceStrategy()
        return fallback_strategy.get_service(protocol_type)

    def _rebuild_strategies(self) -> None:
        """Rebuild strategy lists based on current registry."""
        self._strategies = []
        self._logging_strategies = []

        # Registry-based strategy (highest priority)
        if self._registry is not None:
            registry_strategy = RegistryServiceCreationStrategy(self._registry)
            self._strategies.append(registry_strategy)

            # Protocol-based logging strategy
            protocol_logging_strategy = ProtocolBasedLoggingServiceStrategy(
                self._registry
            )
            self._logging_strategies.append(protocol_logging_strategy)

        # Fallback strategy (lowest priority for general services)
        fallback_strategy = FallbackServiceCreationStrategy()
        self._strategies.append(fallback_strategy)

        # Minimal logging strategy (fallback for logging)
        minimal_logging_strategy = MinimalLoggingServiceStrategy()
        self._logging_strategies.append(minimal_logging_strategy)

    def _is_logging_protocol(self, protocol_type: type[T]) -> bool:
        """Check if protocol type is logging-related."""
        return (
            hasattr(protocol_type, "__name__")
            and "logging" in protocol_type.__name__.lower()
        ) or protocol_type == ProtocolLoggingService

    def get_available_strategies(self) -> list[str]:
        """
        Get list of currently available strategy names.

        Returns:
            List of available strategy names
        """
        available = []
        for strategy in self._strategies:
            if strategy.is_available():
                available.append(strategy.strategy_name)
        return available

    def get_available_logging_strategies(self) -> list[str]:
        """
        Get list of currently available logging strategy names.

        Returns:
            List of available logging strategy names
        """
        available = []
        for strategy in self._logging_strategies:
            if strategy.is_available():
                available.append(strategy.strategy_name)
        return available


# Export for use
__all__ = ["ServiceCreationFactory"]