"""
ProtocolHandlerRegistry - Protocol for handler registry abstraction.

This module provides the protocol definition for handler registries used by
the dispatch engine and mixin components. The protocol abstracts the handler
registry interface, enabling dependency inversion and testability.

Design Pattern:
    This protocol follows the "freeze after init" pattern where registries
    are configured during startup and then frozen for thread-safe read access.
    Implementations must enforce frozen state before lookup operations.

Dependency Injection:
    Register implementations under the "ProtocolHandlerRegistry" DI token:

    .. code-block:: python

        container.register_service(
            "ProtocolHandlerRegistry",
            handler_registry_instance
        )

    Then resolve via DI in node constructors:

    .. code-block:: python

        registry = container.get_service("ProtocolHandlerRegistry")
        self._init_handler_routing(handler_routing, registry)

Usage:
    .. code-block:: python

        from omnibase_core.protocols.runtime import ProtocolHandlerRegistry

        def requires_registry(registry: ProtocolHandlerRegistry) -> None:
            # Ensure registry is frozen before use
            assert registry.is_frozen

            # Look up handler by ID
            handler = registry.get_handler_by_id("user-event-handler")
            if handler is not None:
                result = await handler.handle(envelope)

Related:
    - OMN-934: Handler registry for message dispatch engine
    - OMN-1293: Contract-driven handler routing
    - ServiceHandlerRegistry: Concrete implementation
    - MixinHandlerRouting: Uses this protocol for handler resolution

.. versionadded:: 0.6.3
"""

from __future__ import annotations

__all__ = ["ProtocolHandlerRegistry"]

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
    from omnibase_core.protocols.runtime.protocol_message_handler import (
        ProtocolMessageHandler,
    )


@runtime_checkable
class ProtocolHandlerRegistry(Protocol):
    """
    Protocol for handler registry abstraction in the dispatch engine.

    The handler registry manages handler registrations and provides
    lookup capabilities for the dispatch engine and routing mixins.

    Design Pattern:
        The registry follows the "freeze after init" pattern:
        1. Registration phase: Register handlers during startup
        2. Freeze: Call freeze() to lock the registry
        3. Execution phase: Thread-safe reads for handler lookup

    Thread Safety:
        After freeze(), the registry is read-only and safe for concurrent
        access. Implementations must enforce frozen state before lookup
        operations to ensure thread safety.

    Example:
        .. code-block:: python

            from omnibase_core.protocols.runtime import ProtocolHandlerRegistry

            def uses_registry(registry: ProtocolHandlerRegistry) -> None:
                # Registry must be frozen before lookup
                if not registry.is_frozen:
                    raise RuntimeError("Registry must be frozen")

                handler = registry.get_handler_by_id("my-handler")
                if handler:
                    result = await handler.handle(envelope)

    See Also:
        - :class:`~omnibase_core.services.service_handler_registry.ServiceHandlerRegistry`:
          Concrete implementation
        - :class:`~omnibase_core.mixins.mixin_handler_routing.MixinHandlerRouting`:
          Uses this protocol for handler resolution

    .. versionadded:: 0.6.3
    """

    @property
    def is_frozen(self) -> bool:
        """
        Check if the registry is frozen.

        The registry must be frozen before lookup operations are allowed.
        This enforces the "freeze after init" pattern for thread safety.

        Returns:
            bool: True if frozen and registration is disabled,
                False if registration is still allowed.

        Example:
            .. code-block:: python

                if registry.is_frozen:
                    handler = registry.get_handler_by_id("my-handler")
                else:
                    raise RuntimeError("Registry not frozen")

        .. versionadded:: 0.6.3
        """
        ...

    def get_handler_by_id(self, handler_id: str) -> ProtocolMessageHandler | None:
        """
        Get a handler by its unique ID.

        Looks up a registered handler by its handler_id. Returns None
        if the handler is not found.

        Args:
            handler_id: The handler's unique identifier.

        Returns:
            ProtocolMessageHandler or None if not found.

        Raises:
            ModelOnexError: If registry is not frozen (INVALID_STATE).
                Implementations must enforce frozen state before lookup.

        Example:
            .. code-block:: python

                handler = registry.get_handler_by_id("user-event-handler")
                if handler:
                    result = await handler.handle(envelope)
                else:
                    # Handler not registered
                    pass

        Thread Safety:
            This method is safe for concurrent access after freeze().

        .. versionadded:: 0.6.3
        """
        ...

    def get_handlers(
        self,
        category: EnumMessageCategory,
        message_type: str | None = None,
    ) -> list[ProtocolMessageHandler]:
        """
        Get handlers that can process the given category and message type.

        Returns handlers matching the category and optionally filtering by
        message type. Handlers with empty message_types accept all message
        types in their category.

        Args:
            category: The message category to look up.
            message_type: Optional specific message type to filter by.

        Returns:
            list[ProtocolMessageHandler]: List of matching handlers.
                Empty list if no handlers match.

        Raises:
            ModelOnexError: If registry is not frozen (INVALID_STATE).
                Implementations must enforce frozen state before lookup.

        Example:
            .. code-block:: python

                from omnibase_core.enums import EnumMessageCategory

                # Get all EVENT handlers
                handlers = registry.get_handlers(EnumMessageCategory.EVENT)

                # Get handlers for specific message type
                handlers = registry.get_handlers(
                    EnumMessageCategory.EVENT,
                    message_type="UserCreated",
                )

        Thread Safety:
            This method is safe for concurrent access after freeze().

        .. versionadded:: 0.6.3
        """
        ...

    @property
    def handler_count(self) -> int:
        """
        Get the total number of registered handlers.

        Returns:
            int: Number of registered handlers.

        Example:
            .. code-block:: python

                count = registry.handler_count
                print(f"Registry has {count} handlers")

        .. versionadded:: 0.6.3
        """
        ...
