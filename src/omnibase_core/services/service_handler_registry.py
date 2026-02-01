"""
ServiceHandlerRegistry - Thread-safe registry for message handlers.

This module provides the ServiceHandlerRegistry class for managing handler
registrations in the dispatch engine. Handlers are the execution units that
process messages after routing.

Design Pattern:
    The ServiceHandlerRegistry follows the "freeze after init" pattern (like EnvelopeRouter):
    1. Registration phase: Register handlers during startup (single-threaded)
    2. Freeze: Call freeze() to prevent further modifications
    3. Execution phase: Thread-safe read access for handler lookup

    This pattern ensures:
    - No runtime registration overhead (no locking on reads)
    - Thread-safe concurrent access after freeze
    - Clear separation between configuration and execution phases

Thread Safety:
    - Registration methods are protected by threading.Lock
    - After freeze(), the registry is read-only and thread-safe
    - Execution shape validation occurs at registration time

Related:
    - OMN-934: Handler registry for message dispatch engine
    - EnvelopeRouter: Uses similar freeze-after-init pattern
    - ModelHandlerRegistration: Handler metadata model
    - ModelExecutionShapeValidation: Validates execution shapes

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = ["ServiceHandlerRegistry"]

import logging
import threading
from collections import defaultdict
from uuid import UUID, uuid4

from omnibase_core.decorators.decorator_error_handling import standard_error_handling
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.validation.model_execution_shape_validation import (
    ModelExecutionShapeValidation,
)
from omnibase_core.protocols.runtime.protocol_message_handler import (
    ProtocolMessageHandler,
)

logger = logging.getLogger(__name__)


class ServiceHandlerRegistry:
    """
    Thread-safe registry for message handlers with freeze pattern.

    The ServiceHandlerRegistry manages handler registrations for the dispatch engine.
    It stores handlers by category and message type, validates execution shapes
    at registration time, and provides efficient lookup for dispatching.

    Design Pattern:
        The registry follows the "freeze after init" pattern:
        1. Registration phase: Register handlers during startup
        2. Freeze: Call freeze() to lock the registry
        3. Execution phase: Thread-safe reads for handler lookup

    Thread Safety:
        - Registration methods are protected by threading.Lock
        - After freeze(), the registry is read-only and safe for concurrent access
        - Execution shape validation occurs at registration time

    Execution Shape Validation:
        At registration time, the registry validates that the handler's category
        and node_kind combination forms a valid execution shape per ONEX standards:
        - EVENT -> REDUCER (valid)
        - EVENT -> ORCHESTRATOR (valid)
        - COMMAND -> ORCHESTRATOR (valid)
        - COMMAND -> EFFECT (valid)
        - INTENT -> EFFECT (valid)
        - Other combinations are rejected

    Example:
        .. code-block:: python

            from omnibase_core.services import ServiceHandlerRegistry

            # 1. Create registry and register handlers
            registry = ServiceHandlerRegistry()
            registry.register_handler(user_event_handler)
            registry.register_handler(order_command_handler)

            # 2. Freeze to prevent modifications
            registry.freeze()

            # 3. Look up handlers (thread-safe after freeze)
            handlers = registry.get_handlers(
                category=EnumMessageCategory.EVENT,
                message_type="UserCreated",
            )

    Attributes:
        _handlers_by_category: Handlers organized by category -> list of entries
        _handlers_by_id: Handlers indexed by handler_id for fast lookup
        _frozen: If True, registration is disabled
        _registration_lock: Lock protecting registration methods

    See Also:
        - :class:`ProtocolMessageHandler`: Handler protocol definition
        - :class:`~omnibase_core.runtime.runtime_envelope_router.EnvelopeRouter`:
          Similar freeze-after-init pattern
        - :class:`~omnibase_core.models.validation.model_execution_shape_validation.ModelExecutionShapeValidation`:
          Execution shape validation

    .. versionadded:: 0.4.0
    """

    class _HandlerEntry:
        """
        Internal entry for a registered handler.

        Stores the handler instance and its registration metadata.
        This is an implementation detail and not part of the public API.
        """

        __slots__ = ("handler", "message_types", "registration_id")

        def __init__(
            self,
            handler: ProtocolMessageHandler,
            message_types: set[str],
            registration_id: UUID,
        ) -> None:
            self.handler = handler
            self.message_types = message_types
            self.registration_id = registration_id

    def __init__(self) -> None:
        """
        Initialize ServiceHandlerRegistry with empty registries.

        Creates empty handler registries. Handlers must be registered before
        dispatch. Call ``freeze()`` after registration to prevent further
        modifications and enable safe concurrent access.
        """
        # Handlers organized by category
        self._handlers_by_category: dict[
            EnumMessageCategory, list[ServiceHandlerRegistry._HandlerEntry]
        ] = defaultdict(list)
        # Handlers indexed by handler_id for fast lookup and duplicate detection
        self._handlers_by_id: dict[str, ServiceHandlerRegistry._HandlerEntry] = {}
        # Frozen flag
        self._frozen: bool = False
        # Lock protects registration methods
        self._registration_lock: threading.Lock = threading.Lock()

    def register_handler(
        self,
        handler: ProtocolMessageHandler,
        message_types: set[str] | None = None,
    ) -> None:
        """
        Register a handler for message dispatch.

        Registers the handler and validates that its category/node_kind
        combination forms a valid execution shape.

        Args:
            handler: A handler implementing ProtocolMessageHandler.
            message_types: Optional override for message types.
                If None, uses handler.message_types property.
                If empty set, handler accepts all message types in category.

        Raises:
            ModelOnexError: If registry is frozen (INVALID_STATE).
            ModelOnexError: If handler is None (INVALID_PARAMETER).
            ModelOnexError: If handler lacks required properties (INVALID_PARAMETER).
            ModelOnexError: If handler_id is already registered (DUPLICATE_REGISTRATION).
            ModelOnexError: If execution shape is invalid (VALIDATION_FAILED).

        Example:
            .. code-block:: python

                registry = ServiceHandlerRegistry()

                # Register with handler's message_types
                registry.register_handler(user_event_handler)

                # Register with custom message_types
                registry.register_handler(
                    order_handler,
                    message_types={"OrderCreated", "OrderUpdated"},
                )

                # After registration, freeze
                registry.freeze()

        Thread Safety:
            This method is protected by an internal lock to ensure atomic
            validation and registration.

        .. versionadded:: 0.4.0
        """
        self._register_handler_impl(handler, message_types)

    @standard_error_handling("Handler registration")
    def _register_handler_impl(
        self,
        handler: ProtocolMessageHandler,
        message_types: set[str] | None = None,
    ) -> None:
        """Internal implementation of handler registration."""
        # Validate handler outside lock
        self._validate_handler(handler)

        # Get handler properties
        handler_id = handler.handler_id
        category = handler.category
        node_kind = handler.node_kind
        effective_message_types = (
            message_types if message_types is not None else handler.message_types
        )

        # Validate execution shape outside lock
        self._validate_execution_shape(handler_id, category, node_kind)

        # Create registration entry
        registration_id = uuid4()
        entry = ServiceHandlerRegistry._HandlerEntry(
            handler=handler,
            message_types=effective_message_types,
            registration_id=registration_id,
        )

        # Lock for atomic frozen check + registration
        with self._registration_lock:
            if self._frozen:
                raise ModelOnexError(
                    message="Cannot register handler: ServiceHandlerRegistry is frozen. "
                    "Registration is not allowed after freeze() has been called.",
                    error_code=EnumCoreErrorCode.INVALID_STATE,
                )

            if handler_id in self._handlers_by_id:
                raise ModelOnexError(
                    message=f"Handler with ID '{handler_id}' is already registered. "
                    "Use unregister_handler() first to replace.",
                    error_code=EnumCoreErrorCode.DUPLICATE_REGISTRATION,
                )

            # Register in both indexes
            self._handlers_by_id[handler_id] = entry
            self._handlers_by_category[category].append(entry)

            logger.debug(
                "Registered handler '%s' for category '%s' with %d message types",
                handler_id,
                category.value,
                len(effective_message_types) if effective_message_types else 0,
            )

    def unregister_handler(self, handler_id: str) -> bool:
        """
        Unregister a handler by its ID.

        Removes the handler from the registry. Returns True if the handler
        was found and removed, False if not found.

        Args:
            handler_id: The unique identifier of the handler to remove.

        Returns:
            bool: True if handler was found and removed, False if not found.

        Raises:
            ModelOnexError: If registry is frozen (INVALID_STATE).

        Example:
            .. code-block:: python

                registry = ServiceHandlerRegistry()
                registry.register_handler(handler)

                # Remove the handler
                removed = registry.unregister_handler("my-handler")
                assert removed is True

                # Try to remove again
                removed = registry.unregister_handler("my-handler")
                assert removed is False

        Thread Safety:
            This method is protected by an internal lock.

        .. versionadded:: 0.4.0
        """
        return self._unregister_handler_impl(handler_id)

    @standard_error_handling("Handler unregistration")
    def _unregister_handler_impl(self, handler_id: str) -> bool:
        """Internal implementation of handler unregistration."""
        with self._registration_lock:
            if self._frozen:
                raise ModelOnexError(
                    message="Cannot unregister handler: ServiceHandlerRegistry is frozen. "
                    "Modification is not allowed after freeze() has been called.",
                    error_code=EnumCoreErrorCode.INVALID_STATE,
                )

            if handler_id not in self._handlers_by_id:
                return False

            entry = self._handlers_by_id.pop(handler_id)

            # Remove from category index
            category = entry.handler.category
            category_list = self._handlers_by_category[category]
            self._handlers_by_category[category] = [
                e for e in category_list if e.registration_id != entry.registration_id
            ]

            logger.debug("Unregistered handler '%s'", handler_id)
            return True

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

        Example:
            .. code-block:: python

                registry = ServiceHandlerRegistry()
                registry.register_handler(user_handler)
                registry.freeze()

                # Get all EVENT handlers
                handlers = registry.get_handlers(EnumMessageCategory.EVENT)

                # Get handlers for specific message type
                handlers = registry.get_handlers(
                    EnumMessageCategory.EVENT,
                    message_type="UserCreated",
                )

        Thread Safety:
            This method is safe for concurrent access after freeze().

        .. versionadded:: 0.4.0
        """
        # Enforce freeze contract for thread safety
        if not self._frozen:
            raise ModelOnexError(
                message="get_handlers() called before freeze(). "
                "Registration MUST complete and freeze() MUST be called before lookup. "
                "This is required for thread safety.",
                error_code=EnumCoreErrorCode.INVALID_STATE,
            )

        entries = self._handlers_by_category.get(category, [])
        result: list[ProtocolMessageHandler] = []

        for entry in entries:
            # Check if handler accepts this message type
            if message_type is None:
                # No type filter - include all handlers for category
                result.append(entry.handler)
            elif not entry.message_types:
                # Empty message_types means accept all
                result.append(entry.handler)
            elif message_type in entry.message_types:
                # Specific message type matches
                result.append(entry.handler)

        return result

    def get_handler_by_id(self, handler_id: str) -> ProtocolMessageHandler | None:
        """
        Get a handler by its unique ID.

        Args:
            handler_id: The handler's unique identifier.

        Returns:
            ProtocolMessageHandler or None if not found.

        Raises:
            ModelOnexError: If registry is not frozen (INVALID_STATE).

        Example:
            .. code-block:: python

                registry = ServiceHandlerRegistry()
                registry.register_handler(my_handler)
                registry.freeze()

                handler = registry.get_handler_by_id("my-handler")
                if handler:
                    result = await handler.handle(envelope)

        Thread Safety:
            This method is safe for concurrent access after freeze().

        .. versionadded:: 0.4.0
        """
        if not self._frozen:
            raise ModelOnexError(
                message="get_handler_by_id() called before freeze(). "
                "Registration MUST complete and freeze() MUST be called before lookup.",
                error_code=EnumCoreErrorCode.INVALID_STATE,
            )

        entry = self._handlers_by_id.get(handler_id)
        return entry.handler if entry else None

    def freeze(self) -> None:
        """
        Freeze the registry to prevent further modifications.

        Once frozen, any calls to ``register_handler()`` or ``unregister_handler()``
        will raise ModelOnexError with INVALID_STATE error code. This enforces
        the read-only-after-init pattern for thread safety.

        The freeze operation is idempotent - calling freeze() multiple times
        has no additional effect.

        Example:
            .. code-block:: python

                registry = ServiceHandlerRegistry()
                registry.register_handler(handler)

                # Freeze to prevent modifications
                registry.freeze()
                assert registry.is_frozen

                # Subsequent registration attempts raise INVALID_STATE
                registry.register_handler(another_handler)  # Raises!

        Note:
            This is a one-way operation - there is no ``unfreeze()`` method
            by design, as unfreezing would defeat the thread-safety guarantees.

        Thread Safety:
            This method is protected by an internal lock to ensure atomic
            setting of the frozen flag.

        .. versionadded:: 0.4.0
        """
        with self._registration_lock:
            self._frozen = True

    @property
    def is_frozen(self) -> bool:
        """
        Check if the registry is frozen.

        Returns:
            bool: True if frozen and registration is disabled,
                False if registration is still allowed.

        Example:
            .. code-block:: python

                registry = ServiceHandlerRegistry()
                assert not registry.is_frozen

                registry.freeze()
                assert registry.is_frozen

        .. versionadded:: 0.4.0
        """
        return self._frozen

    @property
    def handler_count(self) -> int:
        """
        Get the total number of registered handlers.

        Returns:
            int: Number of registered handlers.

        Example:
            .. code-block:: python

                registry = ServiceHandlerRegistry()
                assert registry.handler_count == 0

                registry.register_handler(handler)
                assert registry.handler_count == 1

        .. versionadded:: 0.4.0
        """
        return len(self._handlers_by_id)

    def _validate_handler(self, handler: ProtocolMessageHandler | None) -> None:
        """
        Validate that a handler meets the ProtocolMessageHandler requirements.

        Args:
            handler: The handler to validate.

        Raises:
            ModelOnexError: If handler is None or lacks required properties.
        """
        if handler is None:
            raise ModelOnexError(
                message="Cannot register None handler. Handler is required.",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        # Validate handler_id property
        if not hasattr(handler, "handler_id"):
            raise ModelOnexError(
                message="Handler must have 'handler_id' property. "
                "Ensure handler implements ProtocolMessageHandler interface.",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        handler_id = handler.handler_id
        if not isinstance(handler_id, str) or not handler_id:
            raise ModelOnexError(
                message=f"Handler handler_id must be non-empty string, got {type(handler_id).__name__}",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        # Validate category property
        if not hasattr(handler, "category"):
            raise ModelOnexError(
                message="Handler must have 'category' property. "
                "Ensure handler implements ProtocolMessageHandler interface.",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        category = handler.category
        if not isinstance(category, EnumMessageCategory):
            raise ModelOnexError(
                message=f"Handler category must be EnumMessageCategory, got {type(category).__name__}",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        # Validate node_kind property
        if not hasattr(handler, "node_kind"):
            raise ModelOnexError(
                message="Handler must have 'node_kind' property. "
                "Ensure handler implements ProtocolMessageHandler interface.",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        node_kind = handler.node_kind
        if not isinstance(node_kind, EnumNodeKind):
            raise ModelOnexError(
                message=f"Handler node_kind must be EnumNodeKind, got {type(node_kind).__name__}",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        # Validate message_types property
        if not hasattr(handler, "message_types"):
            raise ModelOnexError(
                message="Handler must have 'message_types' property. "
                "Ensure handler implements ProtocolMessageHandler interface.",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        message_types = handler.message_types
        if not isinstance(message_types, set):
            raise ModelOnexError(
                message=f"Handler message_types must be set[str], got {type(message_types).__name__}",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        # Validate handle method is callable
        if not hasattr(handler, "handle") or not callable(
            getattr(handler, "handle", None)
        ):
            raise ModelOnexError(
                message="Handler must have callable 'handle' method. "
                "Ensure handler implements ProtocolMessageHandler interface.",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

    def _validate_execution_shape(
        self,
        handler_id: str,
        category: EnumMessageCategory,
        node_kind: EnumNodeKind,
    ) -> None:
        """
        Validate that the handler's category/node_kind forms a valid execution shape.

        Uses ModelExecutionShapeValidation to check ONEX architectural compliance.

        Args:
            handler_id: Handler ID for error messages.
            category: The message category.
            node_kind: The target node kind.

        Raises:
            ModelOnexError: If execution shape is not valid (VALIDATION_FAILED).
        """
        validation = ModelExecutionShapeValidation.validate_shape(
            source_category=category,
            target_node_kind=node_kind,
        )

        if not validation.is_allowed:
            raise ModelOnexError(
                message=f"Handler '{handler_id}' has invalid execution shape: "
                f"{category.value} -> {node_kind.value}. {validation.rationale}",
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
            )

    def __str__(self) -> str:
        """
        Human-readable string representation.

        Returns:
            str: Format "ServiceHandlerRegistry[handlers=N, frozen=bool]"
        """
        return f"ServiceHandlerRegistry[handlers={len(self._handlers_by_id)}, frozen={self._frozen}]"

    def __repr__(self) -> str:
        """
        Detailed representation for debugging.

        Returns:
            str: Detailed format including handler IDs and categories.
        """
        handler_ids = list(self._handlers_by_id.keys())
        categories = list(self._handlers_by_category.keys())

        # Limit output for large registries
        if len(handler_ids) > 10:
            handler_repr = f"<{len(handler_ids)} handlers>"
        else:
            handler_repr = repr(handler_ids)

        if len(categories) > 5:
            category_repr = f"<{len(categories)} categories>"
        else:
            category_repr = repr([c.value for c in categories])

        return (
            f"ServiceHandlerRegistry(handlers={handler_repr}, "
            f"categories={category_repr}, frozen={self._frozen})"
        )
