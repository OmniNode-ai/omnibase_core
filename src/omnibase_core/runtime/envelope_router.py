"""
EnvelopeRouter - Transport-agnostic orchestrator for ONEX node execution.

This module provides the EnvelopeRouter class, which orchestrates envelope
execution across multiple node instances and handlers. It is the core
coordinator that:
- Registers and manages handlers by EnumHandlerType
- Registers and manages node instances by slug
- Routes envelopes to appropriate handlers
- Executes handlers and returns responses

Architecture:
    EnvelopeRouter follows the transport-agnostic design pattern - it contains
    NO transport-specific code (no Kafka, HTTP, or database imports). All
    transport-specific logic is encapsulated in handlers that implement
    ProtocolHandler. This enables:

    - Pure in-memory orchestration for testing
    - Swappable transports without changing runtime code
    - Clear separation between coordination and I/O

Design Patterns:
    - Dispatcher Pattern: route_envelope() selects handlers based on envelope type
    - Executor Pattern: execute_with_handler() performs actual handler invocation
    - Registry Pattern: handlers and nodes are registered and looked up by key

Related:
    - OMN-228: EnvelopeRouter implementation
    - OMN-226: ProtocolHandler protocol
    - OMN-227: RuntimeNodeInstance wrapper

.. versionadded:: 0.4.0
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from omnibase_core.decorators.error_handling import standard_error_handling
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_handler_type import EnumHandlerType
from omnibase_core.models.core.model_onex_envelope import ModelOnexEnvelope
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.runtime.protocol_node_runtime import ProtocolNodeRuntime
from omnibase_core.types.typed_dict_routing_info import TypedDictRoutingInfo

if TYPE_CHECKING:
    from omnibase_core.protocols.runtime.protocol_handler import ProtocolHandler
    from omnibase_core.runtime.runtime_node_instance import RuntimeNodeInstance

logger = logging.getLogger(__name__)


class EnvelopeRouter(ProtocolNodeRuntime):
    """
    Transport-agnostic orchestrator for ONEX node execution.

    EnvelopeRouter provides pure in-memory orchestration without any transport
    dependencies (no Kafka, HTTP, or database imports). It coordinates:
    - Handler registration and lookup by EnumHandlerType
    - Node instance registration and management
    - Envelope routing to appropriate handlers
    - Handler execution with proper error handling

    MVP Implementation:
        This is the minimal viable implementation (OMN-228). Lifecycle methods
        (initialize, shutdown) and health checks are deferred to Beta.

    Registration Semantics:
        Handlers and nodes have different registration semantics by design:

        +---------------+-------------------+-------------------+---------------------+
        | Entity        | Key               | Duplicate Action  | Use Case            |
        +===============+===================+===================+=====================+
        | **Handler**   | handler_type      | Replace (default) | Hot-swapping,       |
        |               | (EnumHandlerType) | or Raise          | testing, upgrades   |
        +---------------+-------------------+-------------------+---------------------+
        | **Node**      | slug (str)        | Always Raise      | Deterministic       |
        |               |                   |                   | routing, config     |
        +---------------+-------------------+-------------------+---------------------+

        **Handlers** (Replaceable by Default):
            - Keyed by ``handler_type`` (EnumHandlerType enum value)
            - Default behavior: Silent replacement (last-write-wins)
            - Use ``replace=False`` for strict mode that raises on duplicates
            - Rationale: Enables handler hot-swapping (test -> production),
              mock injection for testing, and runtime handler upgrades

            .. code-block:: python

                # Default: replacement allowed
                router.register_handler(http_handler_v1)
                router.register_handler(http_handler_v2)  # Replaces v1 silently

                # Strict: raises on duplicate
                router.register_handler(db_handler, replace=False)
                router.register_handler(other_db_handler, replace=False)  # Raises!

        **Nodes** (Always Unique):
            - Keyed by ``slug`` (string identifier)
            - Always raises ModelOnexError on duplicate registration
            - Rationale: Node slugs are used for deterministic routing. Allowing
              replacement could silently break routing rules and cause hard-to-debug
              issues. If you need to update a node, unregister first (not yet
              implemented in MVP).

            .. code-block:: python

                router.register_node(compute_node)  # slug="my-compute"
                router.register_node(another_node)   # slug="my-compute" -> Raises!

    Thread Safety:
        WARNING: EnvelopeRouter is NOT thread-safe. The handler and node registries
        use dict without synchronization.

        Recommended Pattern (Freeze After Init):
            The safest approach is to register all handlers and nodes during
            application startup, then call ``freeze()`` to prevent further
            modifications. This enforces the read-only contract and is safe for
            concurrent reads with no locking overhead.

            .. code-block:: python

                # During application startup (single-threaded)
                router = EnvelopeRouter()
                router.register_handler(http_handler)
                router.register_handler(db_handler)
                router.register_node(compute_node)
                router.freeze()  # Prevent further registration

                # After freeze, router is read-only (thread-safe for reads)
                # Any registration attempt raises ModelOnexError(INVALID_STATE)
                response = await router.execute_with_handler(envelope, node)

                # Check frozen state if needed
                assert router.is_frozen  # True

        Mitigation Strategies (choose one):

        1. **External Locking (sync contexts)**: Wrap all register/route calls with
           threading.Lock when sharing across threads.

           .. code-block:: python

               import threading
               lock = threading.Lock()

               with lock:
                   runtime.register_handler(handler)

        2. **Async Locking (async contexts)**: Use asyncio.Lock for coroutine-safe
           access when sharing across async tasks.

           .. code-block:: python

               import asyncio
               lock = asyncio.Lock()

               async with lock:
                   runtime.register_handler(handler)

        3. **Per-Thread Instances**: Create separate EnvelopeRouter instances per
           thread/coroutine. This avoids locking overhead entirely.

           .. code-block:: python

               import threading
               _thread_local = threading.local()

               def get_router() -> EnvelopeRouter:
                   if not hasattr(_thread_local, "router"):
                       _thread_local.router = EnvelopeRouter()
                   return _thread_local.router

        4. **Read-Only After Initialization**: Register all handlers/nodes during
           startup, then treat the router as read-only. Safe for concurrent reads
           if no writes occur after initialization.

        As per coding guidelines: "Never share node instances across threads
        without explicit synchronization."

    Example:
        .. code-block:: python

            from omnibase_core.runtime import EnvelopeRouter, NodeInstance

            runtime = EnvelopeRouter()
            runtime.register_handler(http_handler)
            runtime.register_node(my_node_instance)

            response = await runtime.execute_with_handler(envelope, my_node_instance)

    Attributes:
        _handlers: Registry of handlers by EnumHandlerType key.
        _nodes: Registry of node instances by slug.
        _frozen: If True, registration methods will raise ModelOnexError.
            Use ``freeze()`` to set this and ``is_frozen`` property to check.

    See Also:
        - :class:`~omnibase_core.protocols.runtime.protocol_handler.ProtocolHandler`:
          Protocol for handler implementations
        - :class:`~omnibase_core.runtime.runtime_node_instance.RuntimeNodeInstance`:
          Node instance wrapper

    .. versionadded:: 0.4.0
    """

    # Performance threshold for __repr__ output.
    # Show detailed handler types and node slugs when registry size is at or below
    # this threshold. Above this threshold, show abbreviated count-only output
    # to avoid expensive dict iteration in large registries.
    _REPR_ITEM_THRESHOLD: int = 10

    def __init__(self) -> None:
        """
        Initialize EnvelopeRouter with empty registries.

        Creates empty handler and node registries. Handlers and nodes must be
        registered before envelope execution. Call ``freeze()`` after registration
        to prevent further modifications and enable safe concurrent access.
        """
        self._handlers: dict[EnumHandlerType, ProtocolHandler] = {}
        self._nodes: dict[str, RuntimeNodeInstance] = {}
        self._repr_cache: str | None = None
        self._frozen: bool = False

    @standard_error_handling("Handler registration")
    def register_handler(
        self, handler: ProtocolHandler, *, replace: bool = True
    ) -> None:
        """
        Register a handler by its handler_type.

        Handlers are stored using their handler_type property as the key.
        By default, if a handler with the same handler_type is already registered,
        it will be silently replaced (last-write-wins semantics). This behavior
        can be changed using the ``replace`` parameter.

        Args:
            handler: A handler implementing ProtocolHandler. Must have:
                - handler_type property returning EnumHandlerType
                - callable execute method for envelope processing
                - callable describe method for handler metadata
            replace: If True (default), silently replace any existing handler
                with the same handler_type. If False, raise ModelOnexError when
                attempting to register a handler_type that is already registered.
                Use ``replace=False`` for strict registration that catches
                accidental duplicate registrations.

        Raises:
            ModelOnexError: If the router is frozen (INVALID_STATE).
            ModelOnexError: If handler is None.
            ModelOnexError: If handler lacks handler_type property.
            ModelOnexError: If handler.handler_type is not EnumHandlerType.
            ModelOnexError: If handler lacks callable execute method.
            ModelOnexError: If handler lacks callable describe method.
            ModelOnexError: If replace=False and a handler with the same
                handler_type is already registered (DUPLICATE_REGISTRATION).

        Example:
            .. code-block:: python

                runtime = EnvelopeRouter()

                # Default behavior: silent replacement
                runtime.register_handler(http_handler)
                runtime.register_handler(new_http_handler)  # Replaces previous

                # Strict mode: raise on duplicate
                runtime.register_handler(database_handler, replace=False)
                runtime.register_handler(other_db_handler, replace=False)  # Raises!

                # After freeze, registration raises
                runtime.freeze()
                runtime.register_handler(another_handler)  # Raises INVALID_STATE!

        Note:
            Registration is idempotent for the same handler instance. When
            ``replace=True`` (default), registering a different handler with
            the same handler_type replaces the previous handler without warning.
            Use ``replace=False`` during initialization to catch configuration
            errors where multiple handlers are accidentally registered for the
            same type. After calling ``freeze()``, all registration attempts
            will raise ModelOnexError with INVALID_STATE.
        """
        # Check frozen state first - fail fast before any validation
        if self._frozen:
            raise ModelOnexError(
                message="Cannot register handler: EnvelopeRouter is frozen. "
                "Registration is not allowed after freeze() has been called.",
                error_code=EnumCoreErrorCode.INVALID_STATE,
            )

        if handler is None:
            raise ModelOnexError(
                message="Cannot register None handler. Handler is required.",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        # Validate handler_type property exists
        if not hasattr(handler, "handler_type"):
            raise ModelOnexError(
                message="Handler must have 'handler_type' property. "
                "Ensure handler implements ProtocolHandler interface.",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        # Access handler_type and validate it's the correct type
        handler_type = handler.handler_type
        if not isinstance(handler_type, EnumHandlerType):
            raise ModelOnexError(
                message=f"Handler handler_type must be EnumHandlerType, got {type(handler_type).__name__}",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        # Validate execute method is callable
        if not hasattr(handler, "execute") or not callable(
            getattr(handler, "execute", None)
        ):
            raise ModelOnexError(
                message="Handler must have callable 'execute' method. "
                "Ensure handler implements ProtocolHandler interface.",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        # Validate describe method is callable
        if not hasattr(handler, "describe") or not callable(
            getattr(handler, "describe", None)
        ):
            raise ModelOnexError(
                message="Handler must have callable 'describe' method. "
                "Ensure handler implements ProtocolHandler interface.",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        if not replace and handler_type in self._handlers:
            raise ModelOnexError(
                message=f"Handler for type '{handler_type.value}' already registered. "
                "Use replace=True to overwrite.",
                error_code=EnumCoreErrorCode.DUPLICATE_REGISTRATION,
            )

        # Log warning when replacing existing handler
        if handler_type in self._handlers:
            logger.warning(
                "Replacing existing handler for type '%s' with new handler",
                handler_type.value,
            )

        self._handlers[handler_type] = handler
        self._repr_cache = None  # Invalidate cache

    @standard_error_handling("Node registration")
    def register_node(self, node: RuntimeNodeInstance) -> None:
        """
        Register a node instance by its slug.

        Node instances are stored using their slug as the key. Unlike handlers,
        duplicate slug registration raises an error (slugs must be unique).

        Args:
            node: A RuntimeNodeInstance with a unique slug.

        Raises:
            ModelOnexError: If the router is frozen (INVALID_STATE).
            ModelOnexError: If node is None.
            ModelOnexError: If a node with the same slug is already registered.

        Example:
            .. code-block:: python

                runtime = EnvelopeRouter()
                runtime.register_node(compute_node)
                runtime.register_node(effect_node)

                # After freeze, registration raises
                runtime.freeze()
                runtime.register_node(another_node)  # Raises INVALID_STATE!

        Note:
            Node slugs must be unique within the runtime. Attempting to register
            a second node with the same slug will raise ModelOnexError with
            DUPLICATE_REGISTRATION error code. After calling ``freeze()``, all
            registration attempts will raise ModelOnexError with INVALID_STATE.
        """
        # Check frozen state first - fail fast before any validation
        if self._frozen:
            raise ModelOnexError(
                message="Cannot register node: EnvelopeRouter is frozen. "
                "Registration is not allowed after freeze() has been called.",
                error_code=EnumCoreErrorCode.INVALID_STATE,
            )

        if node is None:
            raise ModelOnexError(
                message="Cannot register None node. RuntimeNodeInstance is required.",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        slug = node.slug
        if slug in self._nodes:
            raise ModelOnexError(
                message=f"Node with slug '{slug}' is already registered. "
                "Cannot register duplicate node slug.",
                error_code=EnumCoreErrorCode.DUPLICATE_REGISTRATION,
                node_slug=slug,
            )

        self._nodes[slug] = node
        self._repr_cache = None  # Invalidate cache

    def freeze(self) -> None:
        """
        Freeze the router to prevent further handler and node registration.

        Once frozen, any calls to ``register_handler()`` or ``register_node()``
        will raise ModelOnexError with INVALID_STATE error code. This enforces
        the read-only-after-init pattern for thread safety.

        The freeze operation is idempotent - calling freeze() multiple times
        has no additional effect.

        Example:
            .. code-block:: python

                router = EnvelopeRouter()
                router.register_handler(http_handler)
                router.register_node(compute_node)

                # Freeze to prevent further modifications
                router.freeze()
                assert router.is_frozen

                # Subsequent registration attempts raise INVALID_STATE
                router.register_handler(another_handler)  # Raises!

        Note:
            Freezing also invalidates the repr cache to ensure the frozen state
            is reflected in debug output. This is a one-way operation - there
            is no ``unfreeze()`` method by design, as unfreezing would defeat
            the thread-safety guarantees.

        .. versionadded:: 0.4.0
        """
        self._frozen = True
        self._repr_cache = None  # Invalidate cache to reflect frozen state

    @property
    def is_frozen(self) -> bool:
        """
        Check if the router is frozen.

        Returns:
            bool: True if the router is frozen and registration is disabled,
                False if registration is still allowed.

        Example:
            .. code-block:: python

                router = EnvelopeRouter()
                assert not router.is_frozen  # Initially unfrozen

                router.freeze()
                assert router.is_frozen  # Now frozen

        .. versionadded:: 0.4.0
        """
        return self._frozen

    @standard_error_handling("Envelope routing")
    def route_envelope(self, envelope: ModelOnexEnvelope) -> TypedDictRoutingInfo:
        """
        Route an envelope to the appropriate handler.

        This method acts as the DISPATCHER - it selects the correct handler
        based on the envelope's handler_type field and enforces routing rules.

        Args:
            envelope: The envelope to route. Must have handler_type set.

        Returns:
            dict: A dictionary containing:
                - "handler": The ProtocolHandler for this envelope type
                - "handler_type": The EnumHandlerType used for routing

        Raises:
            ModelOnexError: If envelope.handler_type is None.
            ModelOnexError: If no handler is registered for the handler_type.

        Example:
            .. code-block:: python

                runtime = EnvelopeRouter()
                runtime.register_handler(http_handler)

                routing_info = runtime.route_envelope(envelope)
                handler = routing_info["handler"]
                response = await handler.execute(envelope)

        Note:
            The returned dict structure allows for future extension with
            additional routing metadata (e.g., routing version, timestamp,
            fallback handlers) without breaking existing code.
        """
        if envelope is None:
            raise ModelOnexError(
                message="Cannot route None envelope. Envelope is required.",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        # Validate envelope type for defensive programming
        if not isinstance(envelope, ModelOnexEnvelope):
            raise ModelOnexError(
                message=f"Expected ModelOnexEnvelope, got {type(envelope).__name__}",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        handler_type = envelope.handler_type
        if handler_type is None:
            raise ModelOnexError(
                message="Cannot route envelope without handler_type. "
                "Set envelope.handler_type to specify routing.",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
                envelope_operation=envelope.operation,
            )

        if handler_type not in self._handlers:
            raise ModelOnexError(
                message=f"No handler registered for handler_type '{handler_type.value}'. "
                f"Register a handler with handler_type={handler_type} before routing.",
                error_code=EnumCoreErrorCode.ITEM_NOT_REGISTERED,
                envelope_operation=envelope.operation,
            )

        return {
            "handler": self._handlers[handler_type],
            "handler_type": handler_type,
        }

    async def execute_with_handler(
        self,
        envelope: ModelOnexEnvelope,
        instance: RuntimeNodeInstance,
    ) -> ModelOnexEnvelope:
        """
        Execute the handler for the given envelope and instance.

        This method acts as the EXECUTOR - it performs the actual call into
        the handler, applies validation, and wraps exceptions in error envelopes.

        The execution flow:
        1. Validate inputs (envelope, instance)
        2. Route envelope to find appropriate handler
        3. Call handler.execute() with the envelope
        4. Return response envelope (success or error)

        On handler execution failure, this method catches the exception and
        returns an error envelope rather than propagating the exception.

        Args:
            envelope: The input envelope to process. Must have handler_type set.
            instance: The RuntimeNodeInstance receiving this envelope.
                Provides context for execution (slug, contract, etc.).

        Returns:
            ModelOnexEnvelope: The response envelope containing either:
                - Success response with payload from handler
                - Error response with error message if execution failed

        Raises:
            ModelOnexError: If envelope is None.
            ModelOnexError: If instance is None.
            ModelOnexError: If envelope.handler_type is None.
            ModelOnexError: If no handler is registered for the handler_type.

        Example:
            .. code-block:: python

                runtime = EnvelopeRouter()
                runtime.register_handler(http_handler)

                response = await runtime.execute_with_handler(envelope, instance)

                if response.success:
                    print(f"Result: {response.payload}")
                else:
                    print(f"Error: {response.error}")

        Note:
            Handler execution errors are caught and converted to error envelopes.
            The error envelope preserves the correlation_id for tracking and
            includes the original error message in the error field.
        """
        # Validate inputs
        if envelope is None:
            raise ModelOnexError(
                message="Cannot execute with None envelope. Envelope is required.",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        if instance is None:
            raise ModelOnexError(
                message="Cannot execute with None instance. RuntimeNodeInstance is required.",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        # Validate handler_type before routing
        if envelope.handler_type is None:
            raise ModelOnexError(
                message="Cannot execute envelope without handler_type. "
                "Set envelope.handler_type to specify which handler to use.",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
                envelope_operation=envelope.operation,
                node_slug=instance.slug,
            )

        # Route to find handler (may raise if not found)
        routing_info = self.route_envelope(envelope)
        handler: ProtocolHandler = routing_info["handler"]

        # Execute handler and handle errors
        #
        # Exception Handling Strategy:
        # 1. NEVER catch cancellation/exit signals (SystemExit, KeyboardInterrupt,
        #    GeneratorExit, asyncio.CancelledError) - these must propagate for proper
        #    shutdown and task cancellation semantics.
        # 2. All other exceptions are converted to error envelopes - this is the
        #    documented contract for EnvelopeRouter (never raises from handler
        #    execution, returns error envelopes for observability instead).
        #
        # fallback-ok: Handler exceptions (except cancellation signals) are intentionally
        # caught and converted to error envelopes per the EnvelopeRouter contract.
        try:
            response = await handler.execute(envelope)
            return response
        except (SystemExit, KeyboardInterrupt, GeneratorExit):
            # Never catch cancellation/exit signals - they must propagate
            raise
        except asyncio.CancelledError:
            # Never suppress async cancellation - required for proper task cleanup
            raise
        except Exception as e:
            # Log the error for observability before converting to error envelope
            logger.warning(
                "Handler execution failed for envelope %s with handler type %s: %s",
                envelope.envelope_id,
                routing_info["handler_type"].value,
                str(e),
                exc_info=True,
            )
            # Convert exception to error envelope - this is intentional behavior
            # per the EnvelopeRouter contract (see docstring)
            return ModelOnexEnvelope.create_response(
                request=envelope,
                payload={},
                success=False,
                error=f"Handler execution failed: {e}",
            )

    def __str__(self) -> str:
        """
        Human-readable string representation.

        Returns:
            str: Format "EnvelopeRouter[handlers=N, nodes=M, frozen=bool]"
        """
        return (
            f"EnvelopeRouter[handlers={len(self._handlers)}, "
            f"nodes={len(self._nodes)}, frozen={self._frozen}]"
        )

    def __repr__(self) -> str:
        """
        Detailed representation for debugging.

        Performance Note:
            To avoid expensive dict iteration in large registries, this method
            shows abbreviated output when collections exceed a threshold.
            - Small registries (<=10 items): Show full list of handler types/slugs
            - Large registries (>10 items): Show count only to avoid performance impact

            The result is cached and invalidated when handlers or nodes are registered,
            or when the router is frozen.

        Returns:
            str: Detailed format including handler types, node slugs (or counts),
                and frozen state
        """
        if self._repr_cache is not None:
            return self._repr_cache

        # Optimize handler representation for large registries
        handler_count = len(self._handlers)
        if handler_count <= self._REPR_ITEM_THRESHOLD:
            handler_repr = repr([ht.value for ht in self._handlers])
        else:
            handler_repr = f"<{handler_count} handlers>"

        # Optimize node representation for large registries
        node_count = len(self._nodes)
        if node_count <= self._REPR_ITEM_THRESHOLD:
            node_repr = repr(list(self._nodes.keys()))
        else:
            node_repr = f"<{node_count} nodes>"

        self._repr_cache = (
            f"EnvelopeRouter(handlers={handler_repr}, nodes={node_repr}, "
            f"frozen={self._frozen})"
        )
        return self._repr_cache


__all__ = ["EnvelopeRouter"]
