"""
ProtocolMessageHandler - Protocol for category-based message handlers.

This module provides the protocol definition for category-based message handlers
used by the dispatch engine to execute envelope-based operations. Message handlers
are classified by category (EVENT, COMMAND, INTENT) and node kind (REDUCER,
ORCHESTRATOR, EFFECT).

Design:
    This protocol uses dependency inversion - Core defines the interface,
    and implementations satisfy the contract. This allows the dispatch engine
    to work with handlers without tight coupling to specific implementations.

Architecture:
    Message handlers receive a ModelEventEnvelope, process it according to their
    category and node kind, and return a ModelHandlerOutput containing any events,
    intents, or projections produced.

Usage:
    .. code-block:: python

        from omnibase_core.protocols.runtime import ProtocolMessageHandler
        from omnibase_core.enums import EnumMessageCategory, EnumNodeKind
        from omnibase_core.models.dispatch import ModelHandlerOutput

        class UserEventHandler:
            '''Handler for user-related events.'''

            @property
            def handler_id(self) -> str:
                return "user-event-handler"

            @property
            def category(self) -> EnumMessageCategory:
                return EnumMessageCategory.EVENT

            @property
            def message_types(self) -> set[str]:
                return {"UserCreated", "UserUpdated", "UserDeleted"}

            @property
            def node_kind(self) -> EnumNodeKind:
                return EnumNodeKind.REDUCER

            async def handle(
                self, envelope: ModelEventEnvelope[Any]
            ) -> ModelHandlerOutput[Any]:
                # Process the event and return handler output
                return ModelHandlerOutput.for_reducer(
                    input_envelope_id=envelope.envelope_id,
                    correlation_id=envelope.correlation_id,
                    handler_id=self.handler_id,
                    projections=(updated_projection,),
                )

        # Verify protocol compliance
        handler: ProtocolMessageHandler = UserEventHandler()
        assert isinstance(handler, ProtocolMessageHandler)

Related:
    - OMN-934: Handler registry for message dispatch engine
    - OMN-941: Standardize handler output model
    - ServiceHandlerRegistry: Registry for message handlers
    - ModelHandlerOutput: Handler output model

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = ["ProtocolMessageHandler"]

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
    from omnibase_core.enums.enum_node_kind import EnumNodeKind
    from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
    from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope


@runtime_checkable
class ProtocolMessageHandler(Protocol):
    """
    Protocol for category-based message handlers in the dispatch engine.

    Message handlers are the execution units that process messages after routing.
    Each handler is classified by:
    - category: The message category it handles (EVENT, COMMAND, INTENT)
    - message_types: Specific message types it accepts (empty = all)
    - node_kind: The ONEX node kind this handler represents

    Thread Safety:
        WARNING: Handler implementations may be invoked concurrently from the
        dispatch engine. The same handler instance may be called from multiple
        coroutines simultaneously.

        Design Requirements:
            - **Stateless Handlers (Recommended)**: Keep handlers stateless by
              extracting all needed data from the envelope. This is the safest
              approach and requires no synchronization.
            - **Stateful Handlers**: If state is required, use appropriate
              synchronization primitives (asyncio.Lock for async state).

    Example:
        .. code-block:: python

            from omnibase_core.protocols.runtime import ProtocolMessageHandler
            from omnibase_core.enums import EnumMessageCategory, EnumNodeKind
            from omnibase_core.models.dispatch import ModelHandlerOutput

            class UserEventHandler:
                '''Handler for user-related events.'''

                @property
                def handler_id(self) -> str:
                    return "user-event-handler"

                @property
                def category(self) -> EnumMessageCategory:
                    return EnumMessageCategory.EVENT

                @property
                def message_types(self) -> set[str]:
                    return {"UserCreated", "UserUpdated", "UserDeleted"}

                @property
                def node_kind(self) -> EnumNodeKind:
                    return EnumNodeKind.REDUCER

                async def handle(
                    self, envelope: ModelEventEnvelope[Any]
                ) -> ModelHandlerOutput[Any]:
                    # Process the event and return handler output
                    return ModelHandlerOutput.for_reducer(
                        input_envelope_id=envelope.envelope_id,
                        correlation_id=envelope.correlation_id,
                        handler_id=self.handler_id,
                        projections=(updated_projection,),
                    )

            # Verify protocol compliance
            handler: ProtocolMessageHandler = UserEventHandler()
            assert isinstance(handler, ProtocolMessageHandler)

    Attributes:
        handler_id: Unique identifier for this handler.
        category: The message category this handler processes.
        message_types: Specific message types this handler accepts.
            Empty set means handler accepts all message types in its category.
        node_kind: The ONEX node kind this handler represents.

    .. versionadded:: 0.4.0
    """

    @property
    def handler_id(self) -> str:
        """
        Return the unique identifier for this handler.

        The handler ID is used for:
        - Registration and lookup in the registry
        - Tracing and observability
        - Error reporting and debugging

        Returns:
            str: Unique handler identifier (e.g., "user-event-handler")

        Example:
            .. code-block:: python

                @property
                def handler_id(self) -> str:
                    return "order-processor"
        """
        ...

    @property
    def category(self) -> EnumMessageCategory:
        """
        Return the message category this handler processes.

        Handlers are classified by the category of messages they can handle:
        - EVENT: Past-tense immutable facts
        - COMMAND: Imperative action requests
        - INTENT: Goal-oriented desires

        Returns:
            EnumMessageCategory: The message category (EVENT, COMMAND, or INTENT)

        Example:
            .. code-block:: python

                @property
                def category(self) -> EnumMessageCategory:
                    return EnumMessageCategory.EVENT
        """
        ...

    @property
    def message_types(self) -> set[str]:
        """
        Return the specific message types this handler accepts.

        When empty, the handler accepts all message types within its category.
        When non-empty, only the listed message types are accepted.

        Returns:
            set[str]: Set of accepted message types, or empty for all types

        Example:
            .. code-block:: python

                @property
                def message_types(self) -> set[str]:
                    # Accept only specific event types
                    return {"UserCreated", "UserUpdated"}

                @property
                def message_types(self) -> set[str]:
                    # Accept all event types in category
                    return set()
        """
        ...

    @property
    def node_kind(self) -> EnumNodeKind:
        """
        Return the ONEX node kind this handler represents.

        The node kind determines valid execution shapes:
        - REDUCER: Handles EVENT messages for state aggregation
        - ORCHESTRATOR: Handles EVENT and COMMAND messages for coordination
        - EFFECT: Handles INTENT and COMMAND messages for external I/O

        Returns:
            EnumNodeKind: The node kind (REDUCER, ORCHESTRATOR, EFFECT, etc.)

        Example:
            .. code-block:: python

                @property
                def node_kind(self) -> EnumNodeKind:
                    return EnumNodeKind.REDUCER
        """
        ...

    async def handle(
        self,
        envelope: ModelEventEnvelope[Any],
    ) -> ModelHandlerOutput[Any]:
        """
        Handle the given envelope and return a handler output.

        This is the primary execution method. The handler receives an input
        envelope, processes it according to its category and node kind,
        and returns a ModelHandlerOutput containing any events, intents,
        or projections produced.

        The dispatch engine will aggregate ModelHandlerOutput instances from
        all handlers and construct a ModelDispatchResult for the overall
        dispatch operation.

        Args:
            envelope: The input envelope containing the message to process.
                The payload contains category-specific data.

        Returns:
            ModelHandlerOutput: The handler's output with:
                - input_envelope_id: Copied from envelope.envelope_id
                - correlation_id: Copied from envelope.correlation_id
                - handler_id: This handler's ID
                - node_kind: This handler's node kind
                - events: Event envelopes to publish (for ORCHESTRATOR, EFFECT)
                - intents: Intents for side-effect execution (for ORCHESTRATOR only)
                - projections: Projection updates (for REDUCER only)
                - result: Result value (for COMPUTE only)
                - processing_time_ms: Time taken to process

        Example:
            .. code-block:: python

                async def handle(
                    self, envelope: ModelEventEnvelope[Any]
                ) -> ModelHandlerOutput[Any]:
                    try:
                        # Process the event
                        result = await self._process_event(envelope.payload)

                        # Return output appropriate for this handler's node_kind
                        return ModelHandlerOutput.for_reducer(
                            input_envelope_id=envelope.envelope_id,
                            correlation_id=envelope.correlation_id,
                            handler_id=self.handler_id,
                            projections=(result.projection,),
                            processing_time_ms=result.duration_ms,
                        )
                    except Exception as e:
                        # Re-raise exceptions - dispatch engine handles errors
                        raise
        """
        ...
