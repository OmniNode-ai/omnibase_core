"""
ProtocolHandler - Protocol for ONEX runtime handlers.

This module provides the protocol definition for handlers used by EnvelopeRouter
to execute envelope-based operations. Handlers are the primary execution units
that process ModelOnexEnvelope instances in the ONEX runtime.

Design:
    This protocol uses dependency inversion - Core defines the interface,
    and implementations (in SPI or other packages) satisfy the contract.
    This allows EnvelopeRouter to work with handlers without importing SPI.

Architecture:
    Handlers receive a ModelOnexEnvelope, perform their operation (HTTP call,
    database query, file I/O, etc.), and return a response envelope. The
    handler_type property enables routing decisions by the runtime.

Usage:
    .. code-block:: python

        from omnibase_core.protocols.runtime import ProtocolHandler

        class HttpHandler(ProtocolHandler):
            @property
            def handler_type(self) -> EnumHandlerType:
                return EnumHandlerType.HTTP

            async def execute(
                self, envelope: ModelOnexEnvelope
            ) -> ModelOnexEnvelope:
                # Make HTTP call based on envelope payload
                response_data = await self._http_client.request(...)
                return ModelOnexEnvelope.create_response(
                    request=envelope,
                    payload=response_data,
                    success=True,
                )

            def describe(self) -> TypedDictHandlerMetadata:
                return {
                    "name": "http_handler",
                    "version": ModelSemVer(major=1, minor=0, patch=0),
                    "description": "HTTP request handler",
                    "capabilities": ["GET", "POST", "PUT", "DELETE"],
                }

Related:
    - OMN-226: ProtocolHandler interface definition
    - OMN-228: EnvelopeRouter transport-agnostic orchestrator
    - EnumHandlerType: Handler type classification enum
    - ModelOnexEnvelope: Canonical envelope format for handler I/O

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = ["ProtocolHandler"]

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.enums.enum_handler_type import EnumHandlerType
    from omnibase_core.models.core.model_onex_envelope import ModelOnexEnvelope
    from omnibase_core.types.typed_dict_handler_metadata import TypedDictHandlerMetadata


@runtime_checkable
class ProtocolHandler(Protocol):
    """
    Protocol for ONEX runtime handlers.

    Handlers are execution units that process ModelOnexEnvelope instances.
    Each handler specializes in a specific type of I/O operation (HTTP,
    database, Kafka, filesystem, etc.) and is classified by handler_type.

    The protocol defines three core methods:
    - handler_type: Property returning the handler's classification
    - execute: Async method to process an envelope and return a response
    - describe: Method returning handler metadata for discovery/registration

    Thread Safety:
        WARNING: Handler implementations are invoked from the runtime without
        synchronization. The same handler instance may be called from multiple
        coroutines concurrently.

        Design Requirements:
            - **Stateless Handlers (Recommended)**: Keep handlers stateless by
              extracting all needed data from the envelope. This is the safest
              approach and requires no synchronization.
            - **Stateful Handlers**: If state is required, use appropriate
              synchronization primitives (asyncio.Lock for async, threading.Lock
              for sync state).

        Mitigation Strategies:

        1. **Stateless Design (Recommended)**: All execution state comes from the
           envelope, no instance variables modified during execute().

           .. code-block:: python

               class StatelessHandler:
                   def __init__(self, config: Config):
                       self._config = config  # Read-only after init

                   async def execute(self, envelope: ModelOnexEnvelope) -> ModelOnexEnvelope:
                       # All state from envelope - no instance mutation
                       url = envelope.payload.get("url")
                       return await self._make_request(url)

        2. **Async Locking for Async State**: Use asyncio.Lock when handler state
           must be modified during async execution.

           .. code-block:: python

               class StatefulHandler:
                   def __init__(self):
                       self._lock = asyncio.Lock()
                       self._cache = {}

                   async def execute(self, envelope: ModelOnexEnvelope) -> ModelOnexEnvelope:
                       async with self._lock:
                           # Safe to modify self._cache
                           self._cache[envelope.envelope_id] = result
                       return response

        3. **Thread-Local Storage**: For thread-specific state without locking.

           .. code-block:: python

               import threading

               class ThreadLocalHandler:
                   def __init__(self):
                       self._local = threading.local()

                   async def execute(self, envelope: ModelOnexEnvelope) -> ModelOnexEnvelope:
                       # Thread-local state - no locking needed
                       if not hasattr(self._local, "counter"):
                           self._local.counter = 0
                       self._local.counter += 1
                       return response

        Registration vs Execution:
            - **Registration**: Handlers are registered with EnvelopeRouter. By default,
              handlers can be replaced (same handler_type overwrites previous). Use
              ``replace=False`` for strict registration that raises on duplicates.
            - **Execution**: After registration, handlers are invoked concurrently.
              The handler instance is shared across all executions for that handler_type.

        What NOT to Do:
            - **Do NOT share stateful handlers across threads without synchronization**:
              If a handler maintains mutable state (caches, counters, connections),
              sharing it across threads without proper locking will cause race conditions.
            - **Do NOT modify handler state during execute() without locking**:
              If your handler needs to update instance variables during execution,
              use asyncio.Lock (for async state) or threading.Lock (for sync state).
            - **Do NOT assume envelope processing is serialized**:
              Multiple coroutines may call the same handler instance concurrently.
              Design for concurrent access from the start.

        See Also:
            - :class:`~omnibase_core.runtime.runtime_envelope_router.EnvelopeRouter` for
              registration semantics and runtime thread safety considerations.
            - :doc:`/docs/guides/THREADING` for comprehensive thread safety guidelines
              including production checklists and synchronization patterns.

    Error Handling:
        Handlers should catch internal exceptions and return error envelopes
        using ModelOnexEnvelope.create_response with success=False and an
        appropriate error message. Unhandled exceptions will propagate to
        the runtime's error handling layer.

    Example:
        .. code-block:: python

            from omnibase_core.protocols.runtime import ProtocolHandler
            from omnibase_core.enums.enum_handler_type import EnumHandlerType
            from omnibase_core.models.core.model_onex_envelope import (
                ModelOnexEnvelope,
            )

            class DatabaseHandler:
                '''Database handler implementation.'''

                @property
                def handler_type(self) -> EnumHandlerType:
                    return EnumHandlerType.DATABASE

                async def execute(
                    self, envelope: ModelOnexEnvelope
                ) -> ModelOnexEnvelope:
                    try:
                        result = await self._execute_query(envelope.payload)
                        return ModelOnexEnvelope.create_response(
                            request=envelope,
                            payload={"result": result},
                            success=True,
                        )
                    except Exception as e:  # Example: Converting errors to envelope responses
                        return ModelOnexEnvelope.create_response(
                            request=envelope,
                            payload={},
                            success=False,
                            error=str(e),
                        )

                def describe(self) -> TypedDictHandlerMetadata:
                    return {
                        "name": "database_handler",
                        "version": ModelSemVer(major=1, minor=0, patch=0),
                        "description": "Database query handler",
                        "capabilities": ["SELECT", "INSERT", "UPDATE"],
                    }

            # Verify protocol compliance
            handler: ProtocolHandler = DatabaseHandler()
            assert isinstance(handler, ProtocolHandler)  # True with @runtime_checkable

    Attributes:
        handler_type: The handler type classification (EnumHandlerType).
            Used by the runtime for routing decisions and handler discovery.

    See Also:
        - :class:`~omnibase_core.enums.enum_handler_type.EnumHandlerType`:
          Handler type enumeration for classification
        - :class:`~omnibase_core.models.core.model_onex_envelope.ModelOnexEnvelope`:
          Canonical envelope format for handler I/O

    .. versionadded:: 0.4.0
    """

    @property
    def handler_type(self) -> EnumHandlerType:
        """
        Return the handler type classification.

        The handler type determines how the runtime routes envelopes to
        handlers and enables capability-based handler discovery.

        Returns:
            EnumHandlerType: The handler's type classification (HTTP, DATABASE,
                KAFKA, FILESYSTEM, etc.).

        Example:
            .. code-block:: python

                @property
                def handler_type(self) -> EnumHandlerType:
                    return EnumHandlerType.HTTP
        """
        ...

    async def execute(self, envelope: ModelOnexEnvelope) -> ModelOnexEnvelope:
        """
        Execute handler logic for the given envelope.

        This is the primary execution method. The handler receives an input
        envelope, performs its operation (HTTP call, database query, etc.),
        and returns a response envelope.

        Args:
            envelope: The input envelope containing the operation request.
                The payload contains operation-specific data.

        Returns:
            ModelOnexEnvelope: The response envelope containing the operation
                result. Use ModelOnexEnvelope.create_response() for proper
                causation chain tracking.

        Raises:
            Exception: Handlers may raise exceptions for unrecoverable errors.
                However, best practice is to catch exceptions and return an
                error envelope with success=False.

        Example:
            .. code-block:: python

                async def execute(
                    self, envelope: ModelOnexEnvelope
                ) -> ModelOnexEnvelope:
                    # Extract operation data from payload
                    url = envelope.payload.get("url")
                    method = envelope.payload.get("method", "GET")

                    # Perform operation
                    response = await self._http_client.request(method, url)

                    # Return response envelope
                    return ModelOnexEnvelope.create_response(
                        request=envelope,
                        payload={"status": response.status, "body": response.body},
                        success=response.status < 400,
                    )
        """
        ...

    def describe(self) -> TypedDictHandlerMetadata:
        """
        Return handler metadata for registration and discovery.

        This method provides metadata about the handler for use in:
        - Handler registry registration
        - Runtime capability discovery
        - Monitoring and observability
        - Documentation generation

        Returns:
            TypedDictHandlerMetadata: Handler metadata TypedDict with:
                Required fields:
                    - name (str): Human-readable handler name
                    - version (ModelSemVer): Handler version
                Optional fields:
                    - description (str): Brief handler description
                    - capabilities (list[str]): Supported operations/features

        Example:
            .. code-block:: python

                def describe(self) -> TypedDictHandlerMetadata:
                    return {
                        "name": "kafka_handler",
                        "version": ModelSemVer(major=1, minor=0, patch=0),
                        "description": "Apache Kafka message handler",
                        "capabilities": ["produce", "consume", "admin"],
                    }
        """
        ...
