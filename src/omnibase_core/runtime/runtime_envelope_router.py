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

Exports:
    EnvelopeRouter: The main router class

Design Patterns:
    - Dispatcher Pattern: route_envelope() selects handlers based on envelope type
    - Executor Pattern: execute_with_handler() performs actual handler invocation
    - Registry Pattern: handlers and nodes are registered and looked up by key

Related:
    - OMN-228: EnvelopeRouter implementation
    - OMN-226: ProtocolHandler protocol
    - OMN-227: ModelRuntimeNodeInstance wrapper
    - OMN-1067: Move RuntimeNodeInstance to models/runtime/

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = ["EnvelopeRouter"]

import asyncio
import logging
import threading
import time
from typing import TYPE_CHECKING

from omnibase_core.decorators.decorator_error_handling import standard_error_handling
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_handler_type import EnumHandlerType
from omnibase_core.models.core.model_onex_envelope import ModelOnexEnvelope
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.runtime.runtime_protocol_node import ProtocolNodeRuntime
from omnibase_core.types.typed_dict_routing_info import TypedDictRoutingInfo

if TYPE_CHECKING:
    from omnibase_core.models.runtime.model_runtime_node_instance import (
        ModelRuntimeNodeInstance,
    )
    from omnibase_core.protocols.runtime.protocol_handler import ProtocolHandler

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

        **Why Different Semantics?**
            - **Handlers** represent *capabilities* (how to handle HTTP, Kafka, etc.)
              Multiple handlers with the same capability is a configuration choice
              (e.g., upgrading HTTP handler v1 to v2), so replacement is allowed.
            - **Nodes** represent *identities* (specific service instances)
              Node slugs are used for routing and must be unique. Allowing replacement
              could silently break routing rules and cause hard-to-debug issues.

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
        EnvelopeRouter uses a hybrid thread safety model optimized for the
        "freeze after init" pattern:

        .. warning::

            **CRITICAL**: All ``register_handler()`` and ``register_node()`` calls
            MUST complete before any concurrent routing or execution. Call ``freeze()``
            after registration to enforce read-only mode and enable thread-safe access.

            **Required Pattern**::

                # 1. Registration phase (single-threaded)
                router = EnvelopeRouter()
                router.register_handler(handler)
                router.register_node(node)
                router.freeze()  # <-- CRITICAL: freeze before sharing

                # 2. Execution phase (thread-safe after freeze)
                await router.execute_with_handler(envelope, node)

        **Registration Phase** (single-threaded recommended):
            Registration methods (``register_handler``, ``register_node``, ``freeze``)
            are protected by an internal ``threading.Lock``. This ensures:

            - Atomic check-then-modify for the frozen flag
            - No race condition between ``freeze()`` and registration attempts
            - Prevention of data corruption (torn writes) during concurrent access

            **Important**: The lock prevents structural corruption but does NOT
            eliminate all race conditions. For example, application-level check-then-
            modify patterns (e.g., "check if handler exists, then register") can still
            race if performed outside the lock. The lock only protects individual
            method calls, not multi-step application logic.

            The **recommended pattern** is single-threaded registration during
            application startup, followed by ``freeze()``.

            **Requirement**: All ``register_handler()`` and ``register_node()`` calls
            MUST complete before calling ``freeze()``. Once frozen, the router
            transitions to read-only mode and can be safely shared across threads.

        **Read Phase** (multi-threaded safe after freeze):
            After ``freeze()`` is called, the router becomes read-only. Read operations
            (``route_envelope``, ``execute_with_handler``, property access) are safe
            for concurrent access without locking because:

            - Python dict reads are thread-safe (GIL protection)
            - No mutations occur after freeze
            - The frozen flag prevents any new registrations

        Recommended Pattern (Freeze After Init):
            Register all handlers and nodes during application startup (ideally
            single-threaded), then call ``freeze()`` to enforce the read-only contract.

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

        Alternative Strategies (if dynamic registration is needed):

        1. **Per-Thread Instances**: Create separate EnvelopeRouter instances per
           thread/coroutine. This avoids any shared state.

           .. code-block:: python

               import threading
               _thread_local = threading.local()

               def get_router() -> EnvelopeRouter:
                   if not hasattr(_thread_local, "router"):
                       _thread_local.router = EnvelopeRouter()
                   return _thread_local.router

        2. **Async Locking (for async contexts)**: If registration must occur
           concurrently with routing in async code, use asyncio.Lock externally.

           .. code-block:: python

               import asyncio
               lock = asyncio.Lock()

               async with lock:
                   if not router.is_frozen:
                       router.register_handler(handler)

        WARNING: While registration methods are internally synchronized, the router
        is NOT designed for concurrent registration AND routing. The internal lock
        only protects registration methods, not reads. Always freeze before sharing
        the router across threads for routing operations.

        As per coding guidelines: "Never share node instances across threads
        without explicit synchronization."

        What NOT to Do:

        1. **Do NOT share an unfrozen router across threads**:
           Registration and routing operations can race, leading to undefined behavior.

           .. code-block:: python

               # WRONG - unfrozen router shared across threads
               router = EnvelopeRouter()  # Not frozen!
               threading.Thread(target=lambda: router.register_handler(h)).start()
               await router.route_envelope(envelope)  # Race condition!

        2. **Do NOT call register_handler/register_node after freeze()**:
           This will raise ModelOnexError(INVALID_STATE). Plan all registrations
           before freezing.

           .. code-block:: python

               # WRONG - registration after freeze
               router.freeze()
               router.register_handler(late_handler)  # Raises INVALID_STATE!

        3. **Do NOT skip the freeze() call before concurrent access**:
           Without freeze(), the router provides NO thread safety guarantees for
           routing operations. Always freeze before sharing across threads.

           .. code-block:: python

               # WRONG - no freeze before concurrent access
               router = EnvelopeRouter()
               router.register_handler(handler)
               # Missing: router.freeze()
               executor.map(lambda e: router.route_envelope(e), envelopes)  # Unsafe!

        Mitigation Strategies Summary:

        +---------------------------+----------------------------------------------+-------------------+
        | Strategy                  | When to Use                                  | Trade-offs        |
        +===========================+==============================================+===================+
        | **Freeze After Init**     | Default for most applications. Register all  | Cannot add new    |
        | (Recommended)             | handlers/nodes at startup, then freeze.      | handlers at       |
        |                           |                                              | runtime.          |
        +---------------------------+----------------------------------------------+-------------------+
        | **Per-Thread Instances**  | When threads need isolated routing state.    | Memory overhead,  |
        |                           | Each thread creates its own router.          | handler duplication|
        +---------------------------+----------------------------------------------+-------------------+
        | **Async Locking**         | When dynamic registration is required in     | Performance cost, |
        |                           | async code with concurrent routing.          | complexity.       |
        +---------------------------+----------------------------------------------+-------------------+

        TOCTOU Consideration:
            After ``freeze()``, read methods (``route_envelope``, ``execute_with_handler``)
            access ``self._handlers`` and ``self._nodes`` without locking for performance.
            This is safe because:

            1. The freeze contract guarantees no concurrent registration after freeze()
            2. Python dict reads are atomic under the GIL
            3. The data is effectively immutable after freeze()

            If ``register_handler()`` is somehow called concurrently with routing after
            freeze (violating the contract), the behavior is undefined. The router is
            explicitly designed for the "register all, then freeze, then route" pattern.

    Example:
        Basic usage:

        .. code-block:: python

            from omnibase_core.runtime import EnvelopeRouter, ModelRuntimeNodeInstance

            runtime = EnvelopeRouter()
            runtime.register_handler(http_handler)
            runtime.register_node(my_node_instance)

            response = await runtime.execute_with_handler(envelope, my_node_instance)

    Integration Example (EnvelopeRouter + ModelRuntimeNodeInstance):
        Complete workflow showing handler registration, node setup, and execution:

        .. code-block:: python

            from omnibase_core.runtime import EnvelopeRouter, ModelRuntimeNodeInstance
            from omnibase_core.enums import EnumNodeType, EnumHandlerType
            from omnibase_core.models.core.model_onex_envelope import ModelOnexEnvelope

            # 1. Create router and register handlers
            router = EnvelopeRouter()
            router.register_handler(http_handler)   # handler_type=HTTP
            router.register_handler(db_handler)     # handler_type=DATABASE

            # 2. Create and register node instance
            instance = ModelRuntimeNodeInstance(
                slug="my-compute-node",
                node_type=EnumNodeType.COMPUTE_GENERIC,
                contract=my_contract,
            )
            router.register_node(instance)

            # 3. CRITICAL: Freeze BEFORE any concurrent access
            #    Registration MUST complete before sharing the router
            router.freeze()

            # 4. Connect instance to router (after freeze is safe)
            instance.set_runtime(router)
            await instance.initialize()

            # 5. Execute (thread-safe after freeze)
            envelope = ModelOnexEnvelope(
                envelope_id=uuid4(),
                envelope_version=version,
                correlation_id=uuid4(),
                source_node="client",
                target_node=instance.slug,
                operation="PROCESS_DATA",
                payload={"data": "value"},
                handler_type=EnumHandlerType.HTTP,
                timestamp=datetime.now(UTC),
            )

            # Option A: Via instance (recommended for application code)
            response = await instance.handle(envelope)

            # Option B: Via router directly (for advanced use cases)
            response = await router.execute_with_handler(envelope, instance)

            # 6. Check response
            if response.success:
                print(f"Result: {response.payload}")
            else:
                print(f"Error: {response.error}")

            # 7. Cleanup
            await instance.shutdown()

    Attributes:
        _handlers: Registry of handlers by EnumHandlerType key.
        _nodes: Registry of node instances by slug.
        _frozen: If True, registration methods will raise ModelOnexError.
            Use ``freeze()`` to set this and ``is_frozen`` property to check.
        _registration_lock: Threading lock that protects registration methods
            (``register_handler``, ``register_node``, ``freeze``) to ensure atomic
            check-then-modify operations on the frozen flag and registries.

    See Also:
        - :class:`~omnibase_core.protocols.runtime.protocol_handler.ProtocolHandler`:
          Protocol for handler implementations
        - :class:`~omnibase_core.models.runtime.model_runtime_node_instance.ModelRuntimeNodeInstance`:
          Node instance wrapper
        - :doc:`/docs/guides/THREADING`: Comprehensive thread safety guidelines
          including production checklists, synchronization patterns, and the
          thread safety matrix for all ONEX components.

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

        Thread Safety:
            Initializes a threading.Lock to protect registration methods. This
            ensures atomic check-then-modify operations on the frozen flag and
            registries during the registration phase.
        """
        self._handlers: dict[EnumHandlerType, ProtocolHandler] = {}
        self._nodes: dict[str, ModelRuntimeNodeInstance] = {}
        self._frozen: bool = False
        # Lock protects registration methods to ensure atomic frozen check + modify
        self._registration_lock: threading.Lock = threading.Lock()

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

        Thread Safety:
            This method is protected by an internal lock to ensure atomic
            check-then-modify operations on the frozen flag and handler registry.
        """
        # Validate handler outside lock - no state mutation here
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

        # Lock protects frozen check + registry modification as atomic operation
        with self._registration_lock:
            # Check frozen state inside lock - this is the critical section
            if self._frozen:
                raise ModelOnexError(
                    message="Cannot register handler: EnvelopeRouter is frozen. "
                    "Registration is not allowed after freeze() has been called.",
                    error_code=EnumCoreErrorCode.INVALID_STATE,
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

    @standard_error_handling("Node registration")
    def register_node(self, node: ModelRuntimeNodeInstance) -> None:
        """
        Register a node instance by its slug.

        Node instances are stored using their slug as the key. Unlike handlers,
        duplicate slug registration raises an error (slugs must be unique).

        Args:
            node: A ModelRuntimeNodeInstance with a unique slug.

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

        Thread Safety:
            This method is protected by an internal lock to ensure atomic
            check-then-modify operations on the frozen flag and node registry.
        """
        # Validate node outside lock - no state mutation here
        if node is None:
            raise ModelOnexError(
                message="Cannot register None node. ModelRuntimeNodeInstance is required.",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        slug = node.slug

        # Lock protects frozen check + registry modification as atomic operation
        with self._registration_lock:
            # Check frozen state inside lock - this is the critical section
            if self._frozen:
                raise ModelOnexError(
                    message="Cannot register node: EnvelopeRouter is frozen. "
                    "Registration is not allowed after freeze() has been called.",
                    error_code=EnumCoreErrorCode.INVALID_STATE,
                )

            if slug in self._nodes:
                raise ModelOnexError(
                    message=f"Node with slug '{slug}' is already registered. "
                    "Cannot register duplicate node slug.",
                    error_code=EnumCoreErrorCode.DUPLICATE_REGISTRATION,
                    node_slug=slug,
                )

            self._nodes[slug] = node

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
            This is a one-way operation - there is no ``unfreeze()`` method
            by design, as unfreezing would defeat the thread-safety guarantees.

        Thread Safety:
            This method is protected by an internal lock to ensure atomic
            setting of the frozen flag. This prevents race conditions where
            a registration could slip through during the freeze transition.

        .. versionadded:: 0.4.0
        """
        with self._registration_lock:
            self._frozen = True

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

        .. warning::

            **Freeze Contract Enforced at Runtime**

            This method enforces the freeze contract at runtime by raising
            ``ModelOnexError(INVALID_STATE)`` if called before ``freeze()``.
            This prevents TOCTOU (Time-of-Check-Time-of-Use) race conditions
            where handlers could be modified between lookup and use.

            After ``freeze()``, this method reads ``self._handlers`` WITHOUT
            holding a lock. This is intentional for performance - acquiring a
            lock on every routing operation would be prohibitively expensive
            in high-throughput scenarios.

            **This is safe ONLY because the router MUST be frozen before use.**

            The freeze contract guarantees:

            1. After ``freeze()`` is called, the handler registry becomes immutable
            2. No concurrent registration can occur after freeze
            3. Python dict reads are atomic under the GIL

            **Required Pattern**::

                # 1. Registration phase (single-threaded)
                router = EnvelopeRouter()
                router.register_handler(http_handler)
                router.freeze()  # <-- CRITICAL: freeze before any routing

                # 2. Routing phase (safe after freeze)
                routing_info = router.route_envelope(envelope)

        Args:
            envelope: The envelope to route. Must have handler_type set.

        Returns:
            dict: A dictionary containing:
                - "handler": The ProtocolHandler for this envelope type
                - "handler_type": The EnumHandlerType used for routing

        Raises:
            ModelOnexError: If the router is not frozen (INVALID_STATE).
            ModelOnexError: If envelope is None (INVALID_PARAMETER).
            ModelOnexError: If envelope.handler_type is None (INVALID_PARAMETER).
            ModelOnexError: If no handler is registered for the handler_type
                (ITEM_NOT_REGISTERED).

        Example:
            .. code-block:: python

                runtime = EnvelopeRouter()
                runtime.register_handler(http_handler)
                runtime.freeze()  # REQUIRED before routing

                routing_info = runtime.route_envelope(envelope)
                handler = routing_info["handler"]
                response = await handler.execute(envelope)

        Note:
            The returned dict structure allows for future extension with
            additional routing metadata (e.g., routing version, timestamp,
            fallback handlers) without breaking existing code.
        """
        # Freeze contract enforcement - route_envelope() requires frozen state
        # This MUST be checked BEFORE any access to self._handlers to prevent
        # TOCTOU race conditions where handlers could be modified during routing.
        if not self._frozen:
            raise ModelOnexError(
                message="route_envelope() called before freeze(). "
                "Registration MUST complete and freeze() MUST be called before routing. "
                "This is required for thread safety.",
                error_code=EnumCoreErrorCode.INVALID_STATE,
            )

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

        if not isinstance(handler_type, EnumHandlerType):
            raise ModelOnexError(
                message=f"Envelope handler_type must be EnumHandlerType, got {type(handler_type).__name__}",
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
        instance: ModelRuntimeNodeInstance,
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

        Exception Handling Asymmetry:
            This method has DUAL error handling behavior by design:

            **Routing Errors** (RAISES ModelOnexError):
                - None envelope → ModelOnexError (INVALID_PARAMETER)
                - None instance → ModelOnexError (INVALID_PARAMETER)
                - None handler_type → ModelOnexError (INVALID_PARAMETER)
                - No registered handler → ModelOnexError (ITEM_NOT_REGISTERED)

                These errors represent CALLER mistakes (invalid inputs, missing
                configuration) and should propagate as exceptions so callers
                can fix them at development time.

            **Handler Execution Errors** (RETURNS error envelope):
                - Handler raises any Exception → Error envelope returned
                - Handler timeout, network errors, etc. → Error envelope returned

                These errors represent RUNTIME issues that occur during normal
                operation. They are converted to error envelopes so the message
                flow continues and errors can be tracked via correlation_id.

            **Never Caught** (ALWAYS propagates):
                - SystemExit, KeyboardInterrupt, GeneratorExit
                - asyncio.CancelledError

                These signals must propagate for proper shutdown and task
                cancellation semantics.

        Args:
            envelope: The input envelope to process. Must have handler_type set.
            instance: The ModelRuntimeNodeInstance receiving this envelope.
                Provides context for execution (slug, contract, etc.).

        Returns:
            ModelOnexEnvelope: The response envelope containing either:
                - Success response with payload from handler
                - Error response with error message if handler execution failed

        Raises:
            ModelOnexError: If envelope is None (INVALID_PARAMETER).
            ModelOnexError: If instance is None (INVALID_PARAMETER).
            ModelOnexError: If envelope.handler_type is None (INVALID_PARAMETER).
            ModelOnexError: If no handler is registered for the handler_type
                (ITEM_NOT_REGISTERED).

        Example:
            Proper error handling must account for BOTH exceptions AND error
            envelopes:

            .. code-block:: python

                router = EnvelopeRouter()
                router.register_handler(http_handler)

                # Callers MUST handle both exceptions and error envelopes
                try:
                    response = await router.execute_with_handler(envelope, instance)

                    # Handler execution completed - check envelope for success/error
                    if response.success:
                        print(f"Result: {response.payload}")
                    else:
                        # Handler execution error (e.g., network timeout)
                        print(f"Handler error: {response.error}")
                        # Error envelope preserves correlation_id for tracking
                        print(f"Correlation ID: {response.correlation_id}")

                except ModelOnexError as e:
                    # Routing error (invalid inputs, missing handler)
                    # These indicate caller mistakes that should be fixed
                    if e.error_code == EnumCoreErrorCode.ITEM_NOT_REGISTERED:
                        print(f"Missing handler: {e.message}")
                    elif e.error_code == EnumCoreErrorCode.INVALID_PARAMETER:
                        print(f"Invalid input: {e.message}")
                    else:
                        raise  # Unexpected error, propagate

        Note:
            The asymmetry is intentional:
            - Routing errors are DEVELOPMENT-TIME issues (wrong config, missing
              handlers) - exceptions force immediate attention.
            - Handler errors are RUNTIME issues (network failures, timeouts) -
              error envelopes enable graceful degradation and observability.

            Handler execution error envelopes preserve the correlation_id for
            distributed tracing and include the original error message.
        """
        # Validate inputs
        if envelope is None:
            raise ModelOnexError(
                message="Cannot execute with None envelope. Envelope is required.",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        if instance is None:
            raise ModelOnexError(
                message="Cannot execute with None instance. ModelRuntimeNodeInstance is required.",
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
        # Logging Level Strategy:
        # - Success: DEBUG level - per-operation success logs would create excessive volume
        #   in production (filtered at INFO+). Useful for development/debugging only.
        # - Failure: WARNING level - failures warrant production visibility for monitoring
        #   and alerting. This asymmetry is intentional and consistent with compute_executor.py.
        start_time = time.perf_counter()
        try:
            response = await handler.execute(envelope)
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Validate handler return type to harden against misbehaving handlers.
            # Handlers MUST return ModelOnexEnvelope per ProtocolHandler contract.
            # We use object typing for runtime validation: object is a supertype of
            # all types, allowing isinstance checks while avoiding Any.
            # This defensive programming catches misbehaving handler implementations.
            response_unchecked: object = response
            if not isinstance(response_unchecked, ModelOnexEnvelope):
                logger.warning(
                    "Handler returned invalid type %s instead of ModelOnexEnvelope "
                    "for envelope %s (handler_type=%s, duration=%.2fms)",
                    type(response_unchecked).__name__,
                    envelope.envelope_id,
                    routing_info["handler_type"].value,
                    duration_ms,
                )
                # Convert invalid return to error envelope for observability
                return ModelOnexEnvelope.create_response(
                    request=envelope,
                    payload={},
                    success=False,
                    error=f"Handler returned invalid type {type(response_unchecked).__name__}, "
                    f"expected ModelOnexEnvelope",
                )

            logger.debug(
                "Handler execution completed in %.2fms for envelope %s (handler_type=%s)",
                duration_ms,
                envelope.envelope_id,
                routing_info["handler_type"].value,
            )
            return response
        except (GeneratorExit, KeyboardInterrupt, SystemExit):
            # Never catch cancellation/exit signals - they must propagate
            raise
        except asyncio.CancelledError:
            # Never suppress async cancellation - required for proper task cleanup
            raise
        except Exception as e:
            # boundary-ok: handler errors converted to error envelope per router contract
            duration_ms = (time.perf_counter() - start_time) * 1000
            # Log the error for observability before converting to error envelope
            logger.warning(
                "Handler execution failed for envelope %s with handler type %s: %s (duration: %.2fms)",
                envelope.envelope_id,
                routing_info["handler_type"].value,
                str(e),
                duration_ms,
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

        Thread Safety Note:
            This method does not cache results. While caching could improve
            performance for repeated calls, it was intentionally avoided because:

            1. **Freeze Race Condition**: Cache invalidation could race with
               freeze() in edge cases where __repr__ is called during the
               transition to frozen state.

            2. **Read Safety Post-Freeze**: After freeze(), the handler and node
               dictionaries are effectively read-only, making live dict reads
               inherently safe without additional synchronization.

            3. **Bounded Work**: The threshold-based abbreviation (<=10 items
               shows details, >10 shows counts only) already bounds the work
               to O(threshold), making the performance impact of not caching
               negligible for typical debugging scenarios.

            For high-frequency __repr__ calls in performance-critical code,
            consider storing the result in a local variable.

        Returns:
            str: Detailed format including handler types, node slugs (or counts),
                and frozen state
        """
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

        return (
            f"EnvelopeRouter(handlers={handler_repr}, nodes={node_repr}, "
            f"frozen={self._frozen})"
        )
