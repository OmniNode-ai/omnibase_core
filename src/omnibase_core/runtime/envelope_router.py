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

from typing import TYPE_CHECKING

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_handler_type import EnumHandlerType
from omnibase_core.models.core.model_onex_envelope import ModelOnexEnvelope
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.runtime.protocol_node_runtime import ProtocolNodeRuntime
from omnibase_core.types.typed_dict_routing_info import TypedDictRoutingInfo

if TYPE_CHECKING:
    from omnibase_core.protocols.runtime.protocol_handler import ProtocolHandler
    from omnibase_core.runtime.runtime_node_instance import RuntimeNodeInstance


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
        Handlers and nodes have different registration semantics:
        - **Handlers**: Allow replacement (last-write-wins). Registering a handler
          with the same handler_type silently replaces the previous handler. This
          enables handler hot-swapping and testing patterns.
        - **Nodes**: Raise on duplicate slugs. Node slugs must be unique within
          the runtime. Attempting to register a second node with the same slug
          raises ModelOnexError. This prevents accidental overwriting of node
          configurations.

    Thread Safety:
        WARNING: EnvelopeRouter is NOT thread-safe. The handler and node registries
        use dict without synchronization. For concurrent access:
        - Use external locking (e.g., threading.Lock around register/route calls), or
        - Create separate EnvelopeRouter instances per thread/coroutine
        - Consider using asyncio.Lock for async contexts

        Example with external locking:
            .. code-block:: python

                import threading
                lock = threading.Lock()

                with lock:
                    runtime.register_handler(handler)

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

    See Also:
        - :class:`~omnibase_core.protocols.runtime.protocol_handler.ProtocolHandler`:
          Protocol for handler implementations
        - :class:`~omnibase_core.runtime.runtime_node_instance.RuntimeNodeInstance`:
          Node instance wrapper

    .. versionadded:: 0.4.0
    """

    def __init__(self) -> None:
        """
        Initialize EnvelopeRouter with empty registries.

        Creates empty handler and node registries. Handlers and nodes must be
        registered before envelope execution.
        """
        self._handlers: dict[EnumHandlerType, ProtocolHandler] = {}
        self._nodes: dict[str, RuntimeNodeInstance] = {}

    def register_handler(self, handler: ProtocolHandler) -> None:
        """
        Register a handler by its handler_type.

        Handlers are stored using their handler_type property as the key.
        If a handler with the same handler_type is already registered, it
        will be silently replaced (last-write-wins semantics).

        Args:
            handler: A handler implementing ProtocolHandler. Must have a
                handler_type property returning EnumHandlerType.

        Raises:
            ModelOnexError: If handler is None.
            AttributeError: If handler lacks handler_type property.

        Example:
            .. code-block:: python

                runtime = EnvelopeRouter()
                runtime.register_handler(http_handler)
                runtime.register_handler(database_handler)

        Note:
            Registration is idempotent for the same handler instance. Registering
            a different handler with the same handler_type replaces the previous
            handler without warning.
        """
        if handler is None:
            raise ModelOnexError(
                message="Cannot register None handler. Handler is required.",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        # Access handler_type - will raise AttributeError if not present
        handler_type = handler.handler_type
        if not isinstance(handler_type, EnumHandlerType):
            raise ModelOnexError(
                message=f"Handler handler_type must be EnumHandlerType, got {type(handler_type).__name__}",
                error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            )

        self._handlers[handler_type] = handler

    def register_node(self, node: RuntimeNodeInstance) -> None:
        """
        Register a node instance by its slug.

        Node instances are stored using their slug as the key. Unlike handlers,
        duplicate slug registration raises an error (slugs must be unique).

        Args:
            node: A RuntimeNodeInstance with a unique slug.

        Raises:
            ModelOnexError: If node is None.
            ModelOnexError: If a node with the same slug is already registered.

        Example:
            .. code-block:: python

                runtime = EnvelopeRouter()
                runtime.register_node(compute_node)
                runtime.register_node(effect_node)

        Note:
            Node slugs must be unique within the runtime. Attempting to register
            a second node with the same slug will raise ModelOnexError with
            DUPLICATE_REGISTRATION error code.
        """
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
        # fallback-ok: Handler exceptions are intentionally caught and converted to
        # error envelopes. This is the documented contract - EnvelopeRouter never raises
        # from handler execution, instead returning error envelopes for observability.
        try:
            response = await handler.execute(envelope)
            return response
        except Exception as e:  # fallback-ok: intentional - convert to error envelope
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
            str: Format "EnvelopeRouter[handlers=N, nodes=M]"
        """
        return (
            f"EnvelopeRouter[handlers={len(self._handlers)}, nodes={len(self._nodes)}]"
        )

    def __repr__(self) -> str:
        """
        Detailed representation for debugging.

        Returns:
            str: Detailed format including handler types and node slugs
        """
        handler_types = [ht.value for ht in self._handlers]
        node_slugs = list(self._nodes.keys())
        return f"EnvelopeRouter(handlers={handler_types!r}, nodes={node_slugs!r})"


__all__ = ["EnvelopeRouter"]
