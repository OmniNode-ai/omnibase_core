# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Unified Event Bus Mixin for ONEX Nodes

Provides comprehensive event bus capabilities including:
- Event subscription and listening
- Event completion publishing
- Protocol-based polymorphism
- ONEX standards compliance
- Error handling and logging

This mixin uses composition with ModelEventBusRuntimeState and
ModelEventBusListenerHandle for state management, avoiding BaseModel
inheritance to prevent MRO conflicts in multi-inheritance scenarios.

Thread Safety:
    This mixin is NOT thread-safe. Each node instance should have its own
    mixin instance. Do not share instances across threads without external
    synchronization.
"""

import threading
import uuid
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast
from uuid import UUID

# Generic type parameters for typed event processing
InputStateT = TypeVar("InputStateT")
OutputStateT = TypeVar("OutputStateT")

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.events.model_topic_naming import (
    validate_message_topic_alignment,
)
from omnibase_core.models.mixins.model_completion_data import ModelCompletionData
from omnibase_core.models.mixins.model_log_data import ModelLogData
from omnibase_core.protocols import ProtocolEventEnvelope
from omnibase_core.protocols.event_bus import (
    ProtocolEventBus,
    ProtocolEventBusRegistry,
)

if TYPE_CHECKING:
    from omnibase_core.models.event_bus import (
        ModelEventBusListenerHandle,
        ModelEventBusRuntimeState,
    )


class MixinEventBus(Generic[InputStateT, OutputStateT]):
    """
    Unified mixin for all event bus operations in ONEX nodes.

    Provides:
    - Event listening and subscription capabilities
    - Completion event publishing with proper protocols
    - ONEX standards compliance (no dictionaries, proper models)
    - Protocol-based polymorphism for event bus access
    - Error handling and structured logging
    - Type-safe event processing via generic type parameters

    Design:
    - NO BaseModel inheritance (avoids MRO conflicts)
    - NO __init__ method (uses lazy state accessors)
    - Explicit binding required before publishing (fail-fast)
    - Composition with ModelEventBusRuntimeState and ModelEventBusListenerHandle
    - Generic[InputStateT, OutputStateT] for type-safe event processing

    Type Parameters:
        InputStateT: The type of input state for event processing
        OutputStateT: The type of output state returned from processing

    Usage:
        class MyNode(MixinEventBus[MyInputState, MyOutputState], SomeOtherBase):
            def __init__(self, event_bus: ProtocolEventBus):
                super().__init__()
                self.bind_event_bus(event_bus)

            def process(self, input_state: MyInputState) -> MyOutputState:
                # Type-safe processing
                return MyOutputState(...)
    """

    # --- Lazy State Accessors (avoid MRO hazards) ---

    @property
    def _event_bus_runtime_state(self) -> "ModelEventBusRuntimeState":
        """Lazy accessor for runtime state - creates on first access."""
        from omnibase_core.models.event_bus import ModelEventBusRuntimeState

        attr_name = "_mixin_event_bus_state"
        # TODO(v1.0): Remove hasattr fallback after migration stabilizes.
        # This fallback handles lazy initialization for mixins that don't call
        # bind_*() in __init__. It supports composition patterns where the mixin
        # is mixed into classes that may not initialize state immediately. Once
        # all consumers have migrated to explicit binding in __init__, this
        # fallback can be removed in favor of requiring bind_*() calls.
        if not hasattr(self, attr_name):
            state = ModelEventBusRuntimeState.create_unbound()
            object.__setattr__(self, attr_name, state)
        return cast(ModelEventBusRuntimeState, object.__getattribute__(self, attr_name))

    @property
    def _event_bus_listener_handle(self) -> "ModelEventBusListenerHandle | None":
        """Lazy accessor for listener handle - may be None if never started."""
        from omnibase_core.models.event_bus import ModelEventBusListenerHandle

        attr_name = "_mixin_event_bus_listener"
        # TODO(v1.0): Remove hasattr fallback after migration stabilizes.
        # This fallback returns None for uninitialized listener handle. The
        # listener handle is only created when start_event_listener() is called,
        # not during bind. Once all consumers have migrated to explicit lifecycle
        # management, this fallback can be removed.
        if not hasattr(self, attr_name):
            return None
        return cast(
            ModelEventBusListenerHandle | None,
            object.__getattribute__(self, attr_name),
        )

    # --- Explicit Binding Methods ---

    def bind_event_bus(self, event_bus: ProtocolEventBus) -> None:
        """Explicitly bind an event bus instance to this mixin.

        This method must be called before any event publishing operations.
        The event bus is stored as a private attribute and used for all
        subsequent publish operations.

        Args:
            event_bus: The event bus instance implementing ProtocolEventBus.
                Must support publish() or publish_async() methods.

        Note:
            After binding, is_bound flag is set to True on the runtime state.
            Use _has_event_bus() to check if binding was successful.

        Example:
            >>> node = MyNode()
            >>> node.bind_event_bus(event_bus)
            >>> node.publish_completion_event("complete", data)  # Now works
        """
        object.__setattr__(self, "_bound_event_bus", event_bus)
        self._event_bus_runtime_state.is_bound = True

        emit_log_event(
            LogLevel.DEBUG,
            "MIXIN_BIND: Event bus bound to mixin",
            ModelLogData(node_name=self.get_node_name()),
        )

    def bind_registry(self, registry: ProtocolEventBusRegistry) -> None:
        """Bind a registry that provides event bus access.

        Alternative to bind_event_bus() for cases where the event bus is
        accessed through a registry pattern. The registry's event_bus property
        will be used for all publishing operations.

        Args:
            registry: A registry implementing ProtocolEventBusRegistry.
                Must have an event_bus property that returns ProtocolEventBus.

        Note:
            If registry.event_bus is not None, is_bound flag is set to True.
            The registry is stored and its event_bus is resolved on each publish.

        Example:
            >>> node = MyNode()
            >>> node.bind_registry(my_registry)
            >>> # Event bus is accessed via registry.event_bus
        """
        object.__setattr__(self, "_bound_registry", registry)
        if registry.event_bus is not None:
            self._event_bus_runtime_state.is_bound = True

        emit_log_event(
            LogLevel.DEBUG,
            "MIXIN_BIND: Registry bound to mixin",
            ModelLogData(node_name=self.get_node_name()),
        )

    def bind_contract_path(self, contract_path: str) -> None:
        """Bind the contract path used to derive event patterns.

        The contract path is used by get_event_patterns() to determine
        which event types this node should listen to and publish.

        Args:
            contract_path: Absolute or relative path to the ONEX contract
                YAML file that defines this node's event patterns. An empty
                string is treated as "no contract" and will cause
                get_event_patterns() to return an empty list with a warning.

        Note:
            The contract file is not loaded immediately; it is read when
            get_event_patterns() is called.

        Empty String Handling:
            Passing an empty string ("") is semantically equivalent to not
            binding a contract path at all. The get_event_patterns() method
            uses `if not contract_path:` to check for both None and empty
            string, treating both as "no contract configured". If you want
            to explicitly clear a previously bound contract path, pass an
            empty string.
        """
        self._event_bus_runtime_state.contract_path = contract_path

    def bind_node_name(self, node_name: str) -> None:
        """Bind the node name used for event publishing and logging.

        The node name is included in published events and log messages
        for identification and tracing purposes. If not bound, the
        class name is used as a fallback.

        Args:
            node_name: The human-readable name of this node. Should be
                unique within the system for proper event correlation.
                An empty string is treated as "not bound" and will cause
                get_node_name() to return the class name as a fallback.

        Note:
            This affects get_node_name() return value and all log output.
        """
        self._event_bus_runtime_state.node_name = node_name

    # --- Fail-Fast Event Bus Access ---

    def _require_event_bus(self) -> ProtocolEventBus:
        """Get event bus or raise ModelOnexError if not bound.

        Returns:
            The bound event bus instance.

        Raises:
            ModelOnexError: If no event bus is bound.
        """
        bus = self._get_event_bus()
        if bus is None:
            raise ModelOnexError(
                message=f"Event bus not bound on {self.__class__.__name__}. "
                "Call bind_event_bus() or bind_registry() before publishing.",
                error_code=EnumCoreErrorCode.INVALID_STATE,
                context={"class_name": self.__class__.__name__},
            )
        return bus

    def _get_event_bus(self) -> ProtocolEventBus | None:
        """
        Resolve event bus using protocol-based polymorphism.

        Returns:
            The event bus instance or None if not bound.
        """
        # TODO(v1.0): Remove hasattr fallbacks after migration stabilizes.
        # These checks support lazy binding patterns where bind_*() may not have
        # been called yet. This enables flexible composition where event bus can
        # be bound at any point in the lifecycle. Once all consumers have migrated
        # to explicit binding in __init__, these fallbacks can be removed.
        # Try direct event_bus binding first
        if hasattr(self, "_bound_event_bus"):
            bus = object.__getattribute__(self, "_bound_event_bus")
            if bus is not None:
                return cast(ProtocolEventBus, bus)

        # Try registry binding
        if hasattr(self, "_bound_registry"):
            registry = object.__getattribute__(self, "_bound_registry")
            if hasattr(registry, "event_bus"):
                event_bus = getattr(registry, "event_bus", None)
                if event_bus is not None:
                    return cast(ProtocolEventBus, event_bus)

        return None

    def _has_event_bus(self) -> bool:
        """Check if an event bus is currently available for publishing.

        Use this method to check availability before attempting operations that
        require an event bus. This is useful for optional event publishing where
        you want to gracefully skip rather than raise an error.

        For operations that require an event bus, prefer _require_event_bus()
        which will raise ModelOnexError with a descriptive message.

        Returns:
            True if an event bus is bound and available, False otherwise.

        Example:
            >>> if self._has_event_bus():
            ...     self.publish_completion_event("done", data)
            ... else:
            ...     self._log_warn("Skipping event - no bus", "publish")
        """
        return self._get_event_bus() is not None

    # --- Node Interface Methods (to be overridden by subclasses) ---

    def get_node_name(self) -> str:
        """Get the name of this node for event publishing and logging.

        Returns the bound node name if set via bind_node_name(), otherwise
        falls back to the class name. The node name is used in event
        correlation, logging context, and listener thread naming.

        Returns:
            The node name string. Either the explicitly bound name or
            the class name as a fallback.
        """
        state = self._event_bus_runtime_state
        if state.node_name:
            return state.node_name
        return self.__class__.__name__

    def get_node_id(self) -> UUID:
        """Get the unique identifier for this node.

        Returns the node's UUID for event attribution. If a _node_id
        attribute exists on the instance, that value is returned.
        Otherwise, generates a deterministic UUID v5 from the node name
        using the DNS namespace.

        Returns:
            A UUID identifying this node instance. The same node name
            will always generate the same UUID across invocations.
        """
        # Try to get actual node_id if available, otherwise generate from name
        if hasattr(self, "_node_id") and isinstance(
            object.__getattribute__(self, "_node_id"), UUID
        ):
            return cast(UUID, object.__getattribute__(self, "_node_id"))
        # Generate deterministic UUID from node name using standard uuid5
        # Uses DNS namespace as a well-known namespace for name-based UUIDs
        return uuid.uuid5(uuid.NAMESPACE_DNS, self.get_node_name())

    def process(self, input_state: InputStateT) -> OutputStateT:
        """
        Process input state and return output state.

        Default implementation - override in subclasses for actual processing.

        Args:
            input_state: The typed input state to process.

        Returns:
            The typed output state after processing.

        Raises:
            NotImplementedError: If not overridden in subclass.
        """
        msg = "Subclasses must implement process method"
        raise NotImplementedError(msg)  # stub-ok: abstract method

    # --- Topic Validation ---

    def _validate_topic_alignment(
        self,
        topic: str,
        envelope: Any,
    ) -> None:
        """
        Validate that envelope's message category matches the topic.

        This method enforces message-topic alignment at runtime, ensuring that
        events are published to the correct topic type (e.g., events to .events
        topics, commands to .commands topics).

        Args:
            topic: Target Kafka topic
            envelope: Event envelope being published (must have message_category property)

        Raises:
            ModelOnexError: If message category doesn't match topic

        Example:
            >>> envelope = ModelEventEnvelope(payload=UserCreatedEvent(...))
            >>> self._validate_topic_alignment("dev.user.events.v1", envelope)  # OK
            >>> self._validate_topic_alignment("dev.user.commands.v1", envelope)  # Raises
        """
        # Only validate if envelope has message_category property
        if not hasattr(envelope, "message_category"):
            self._log_warn(
                f"Envelope type {type(envelope).__name__} does not have message_category property, skipping topic alignment validation",
                pattern="topic_alignment",
            )
            return

        message_category: EnumMessageCategory = envelope.message_category
        message_type_name = (
            type(envelope.payload).__name__
            if hasattr(envelope, "payload")
            else type(envelope).__name__
        )
        validate_message_topic_alignment(topic, message_category, message_type_name)

    # --- Event Completion Publishing ---

    async def publish_event(
        self,
        event_type: str,
        payload: ModelOnexEvent | None = None,
        correlation_id: UUID | None = None,
    ) -> None:
        """
        Publish an event via the event bus.

        This is a simple wrapper that publishes events directly to the event bus.

        Args:
            event_type: Type of event to publish
            payload: Event payload data (ModelOnexEvent or None for a new event)
            correlation_id: Optional correlation ID for tracking

        Raises:
            ModelOnexError: If event bus is not bound.
        """
        bus = self._require_event_bus()

        try:
            # Build event using ModelOnexEvent or use provided payload
            event = payload or ModelOnexEvent.create_core_event(
                event_type=event_type,
                node_id=self.get_node_id(),
                correlation_id=correlation_id,
            )

            # Publish via event bus - fail fast if no publish method
            # Note: hasattr checks support legacy event bus implementations with
            # non-standard interfaces. Cast to Any for duck-typed method calls.
            if hasattr(bus, "publish_async"):
                # Wrap in envelope for async publishing
                from omnibase_core.models.events.model_event_envelope import (
                    ModelEventEnvelope,
                )

                envelope: ModelEventEnvelope[ModelOnexEvent] = ModelEventEnvelope(
                    payload=event
                )
                # TODO: Add topic validation when topic-based publishing is implemented
                # When the event bus supports explicit topic routing, validate here:
                # self._validate_topic_alignment(topic, envelope)
                await cast(Any, bus).publish_async(envelope)
            elif hasattr(bus, "publish"):
                cast(Any, bus).publish(event)  # Synchronous method - no await
            else:
                raise ModelOnexError(
                    message="Event bus does not support publishing (missing 'publish_async' and 'publish' methods)",
                    error_code=EnumCoreErrorCode.EVENT_BUS_ERROR,
                    context={"bus_type": type(bus).__name__, "event_type": event_type},
                )

            self._log_info(f"Published event: {event_type}", event_type)

        except ModelOnexError:
            raise  # Re-raise binding errors from _require_event_bus
        except Exception as e:
            self._log_error(
                f"Failed to publish event: {e!r}",
                "publish_event",
                error=e,
            )

    def publish_completion_event(
        self,
        event_type: str,
        data: ModelCompletionData,
    ) -> None:
        """
        Publish completion event using synchronous event bus.

        Args:
            event_type: Event type string (e.g., "generation.health.complete")
            data: Completion data model

        Raises:
            ModelOnexError: If event bus is not bound.
        """
        bus = self._require_event_bus()

        # Check if bus is async-only (has async methods but not sync methods)
        has_async = hasattr(bus, "apublish") or hasattr(bus, "apublish_async")
        has_sync = hasattr(bus, "publish") or hasattr(bus, "publish_async")

        if has_async and not has_sync:
            self._log_error(
                "registry.event_bus is async-only; call 'await apublish_completion_event(...)' instead",
                pattern="event_bus.async_only",
            )
            return

        try:
            event = self._build_event(event_type, data)
            # Use synchronous publish method only (this is a sync method) - fail fast if missing
            # TODO: Add topic validation when topic-based publishing is implemented
            # Sync publish doesn't use envelope, so validation would need to wrap event first:
            # envelope = ModelEventEnvelope(payload=event)
            # self._validate_topic_alignment(topic, envelope)
            # Note: hasattr check supports legacy event bus with non-standard interface
            if hasattr(bus, "publish"):
                cast(Any, bus).publish(event)
            else:
                raise ModelOnexError(
                    message="Event bus has no synchronous 'publish' method",
                    error_code=EnumCoreErrorCode.EVENT_BUS_ERROR,
                    context={"bus_type": type(bus).__name__, "event_type": event_type},
                )
            self._log_info(f"Published completion event: {event_type}", event_type)
        except ModelOnexError:
            raise  # Re-raise binding errors from _require_event_bus
        except Exception as e:
            self._log_error(
                f"Failed to publish completion event: {e!r}",
                "publish_completion",
                error=e,
            )

    async def apublish_completion_event(
        self,
        event_type: str,
        data: ModelCompletionData,
    ) -> None:
        """
        Publish completion event using asynchronous event bus.

        Supports both async and sync buses for maximum compatibility.

        Args:
            event_type: Event type string (e.g., "generation.health.complete")
            data: Completion data model

        Raises:
            ModelOnexError: If event bus is not bound.
        """
        bus = self._require_event_bus()

        try:
            event = self._build_event(event_type, data)

            # Prefer async publishing if available - fail fast if no publish method
            # Note: hasattr checks support legacy event bus implementations with
            # non-standard interfaces. Cast to Any for duck-typed method calls.
            if hasattr(bus, "publish_async"):
                # Wrap event in envelope for async publishing
                from omnibase_core.models.events.model_event_envelope import (
                    ModelEventEnvelope,
                )

                envelope: ModelEventEnvelope[ModelOnexEvent] = ModelEventEnvelope(
                    payload=event
                )
                # TODO: Add topic validation when topic-based publishing is implemented
                # When the event bus supports explicit topic routing, validate here:
                # self._validate_topic_alignment(topic, envelope)
                await cast(Any, bus).publish_async(envelope)
            # Fallback to sync method
            elif hasattr(bus, "publish"):
                cast(Any, bus).publish(event)  # Synchronous method - no await
            else:
                raise ModelOnexError(
                    message="Event bus has no publish method (missing 'publish_async' and 'publish')",
                    error_code=EnumCoreErrorCode.EVENT_BUS_ERROR,
                    context={"bus_type": type(bus).__name__, "event_type": event_type},
                )

            self._log_info(f"Published completion event: {event_type}", event_type)

        except ModelOnexError:
            raise  # Re-raise binding errors from _require_event_bus
        except Exception as e:
            self._log_error(
                f"Failed to publish completion event: {e!r}",
                "publish_completion",
                error=e,
            )

    def _build_event(
        self, event_type: str, data: ModelCompletionData
    ) -> ModelOnexEvent:
        """Build a ModelOnexEvent from completion data.

        Constructs a properly formatted ONEX event using the completion
        data's event kwargs, the node's ID, and optional correlation ID.

        Args:
            event_type: The event type string (e.g., "generation.health.complete").
            data: Completion data model containing message, success flag,
                tags, and optional correlation_id.

        Returns:
            A ModelOnexEvent instance ready for publishing via the event bus.

        Note:
            The correlation_id from data is extracted and passed separately
            to create_core_event() to ensure proper type handling.
        """
        # Extract kwargs and handle correlation_id explicitly
        event_kwargs = data.to_event_kwargs()
        correlation_id = event_kwargs.pop("correlation_id", None)

        return ModelOnexEvent.create_core_event(
            event_type=event_type,
            node_id=self.get_node_id(),
            correlation_id=correlation_id if isinstance(correlation_id, UUID) else None,
            **event_kwargs,
        )

    # --- Event Listening and Subscription ---

    def get_event_patterns(self) -> list[str]:
        """Get event patterns this node should subscribe to and listen for.

        Default implementation generates patterns based on the node name.
        Override in subclasses for custom event subscription patterns.

        Returns:
            A list of event pattern strings that this node should subscribe to.
            Patterns follow the format "domain.node_name.action" (e.g.,
            "generation.mynode.start", "coordination.mynode.execute").

        Raises:
            ModelOnexError: If pattern generation fails due to configuration
                or contract parsing errors.

        Note:
            If contract_path is not bound, a warning is logged and an empty
            list is returned. Bind contract_path via bind_contract_path()
            before calling if you need contract-based patterns.

        Example:
            >>> node.bind_contract_path("/path/to/contract.yaml")
            >>> patterns = node.get_event_patterns()
            >>> # Returns ["generation.mynode.start", "generation.mynode.process", ...]
        """
        try:
            contract_path = self._event_bus_runtime_state.contract_path
            if not contract_path:
                self._log_warn(
                    "No contract_path found, cannot determine event patterns",
                    "event_patterns",
                )
                return []

            # Extract event patterns from contract (simplified implementation)
            # Parse the YAML contract to extract event patterns
            node_name = self.get_node_name().lower()

            # Generate common patterns based on node name
            return [
                f"generation.{node_name}.start",
                f"generation.{node_name}.process",
                f"coordination.{node_name}.execute",
            ]

        except Exception as e:
            self._log_error(
                f"Failed to get event patterns: {e!r}",
                "event_patterns",
                error=e,
            )
            raise ModelOnexError(
                f"Failed to get event patterns: {e!s}",
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
            ) from e

    def get_completion_event_type(self, input_event_type: str) -> str:
        """Get the completion event type for a given input event.

        Maps input event types to their corresponding completion event types
        using a predefined mapping table. This enables proper event-driven
        workflows where processing completion is signaled.

        Args:
            input_event_type: The input event type string to map
                (e.g., "generation.tool.start").

        Returns:
            The corresponding completion event type string
            (e.g., "generation.tool.complete").

        Raises:
            ModelOnexError: If event type mapping fails due to invalid format.

        Example:
            >>> event_type = node.get_completion_event_type("generation.tool.start")
            >>> # Returns "generation.tool.complete"
            >>> event_type = node.get_completion_event_type("custom.event")
            >>> # Returns "custom.complete" (default: replaces last part)
        """
        try:
            # input_event_type is already typed as str
            event_str = input_event_type

            # Extract domain and event suffix
            parts = event_str.split(".")
            if len(parts) < 3:
                return f"{event_str}.complete"

            domain = parts[0]  # e.g., "generation"
            event_suffix = ".".join(parts[1:])  # e.g., "tool.start"

            # Map input events to completion events
            completion_mappings = {
                "health.check": "health.complete",
                "contract.validate": "contract.complete",
                "tool.start": "tool.complete",
                "tool.process": "tool.complete",
                "ast.generate": "ast.complete",
                "render.files": "render.complete",
                "validate.files": "validate.complete",
            }

            # Find matching pattern
            for pattern, completion in completion_mappings.items():
                if event_suffix.endswith(pattern.split(".")[-1]):
                    return f"{domain}.{completion}"

            # Default: replace last part with "complete"
            parts[-1] = "complete"
            return ".".join(parts)

        except Exception as e:
            self._log_error(
                f"Failed to determine completion event type: {e!r}",
                "completion_event_type",
                error=e,
            )
            raise ModelOnexError(
                f"Failed to determine completion event type: {e!s}",
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
            ) from e

    def start_event_listener(self) -> "ModelEventBusListenerHandle":
        """Start the event listener thread for processing incoming events.

        Creates a background daemon thread that subscribes to event patterns
        returned by get_event_patterns() and dispatches incoming events to
        the process() method. This method is idempotent - calling it when
        a listener is already running returns the existing handle.

        Returns:
            A ModelEventBusListenerHandle for managing the listener lifecycle.
            Use the handle's stop() method or stop_event_listener() to terminate.

        Raises:
            ModelOnexError: If no event bus is bound. Call bind_event_bus()
                or bind_registry() before starting the listener.

        Note:
            The listener thread is a daemon thread, meaning it will be
            automatically terminated when the main program exits.

        Example:
            >>> node.bind_event_bus(event_bus)
            >>> handle = node.start_event_listener()
            >>> # ... process events ...
            >>> node.stop_event_listener(handle)
        """
        from omnibase_core.models.event_bus import ModelEventBusListenerHandle

        # Return existing handle if already running
        existing = self._event_bus_listener_handle
        if existing is not None and existing.is_active():
            self._log_warn("Event listener already running", "event_listener")
            return existing

        if not self._has_event_bus():
            raise ModelOnexError(
                message=f"Cannot start event listener on {self.__class__.__name__}: "
                "no event bus available. Call bind_event_bus() or bind_registry() first.",
                error_code=EnumCoreErrorCode.INVALID_STATE,
                context={"class_name": self.__class__.__name__},
            )

        # Create new handle
        handle = ModelEventBusListenerHandle(
            stop_event=threading.Event(),
            is_running=True,
        )

        # Create and start thread
        handle.listener_thread = threading.Thread(
            target=self._event_listener_loop,
            args=(handle,),
            daemon=True,
            name=f"EventListener-{self.get_node_name()}",
        )
        handle.listener_thread.start()

        # Store handle
        object.__setattr__(self, "_mixin_event_bus_listener", handle)

        self._log_info("Event listener started", "event_listener")
        return handle

    def stop_event_listener(
        self, handle: "ModelEventBusListenerHandle | None" = None
    ) -> bool:
        """Stop the event listener and unsubscribe from all events.

        Gracefully terminates the event listener thread and removes all
        event subscriptions from the event bus. This method is safe to
        call multiple times - it will not raise errors if the listener
        is already stopped or was never started.

        Thread Safety:
            This method ensures target.stop() is always called, even if
            unsubscription errors occur. This prevents resource leaks from
            leaving listener threads running.

        Args:
            handle: Optional listener handle to stop. If None, stops the
                current listener associated with this mixin instance.

        Returns:
            True if the listener was stopped cleanly within the timeout
            period or if there was no active listener. False if the
            listener thread did not terminate within the timeout.

        Raises:
            ModelOnexError: If the event bus does not support unsubscribe().
                Note: Even when this is raised, the listener thread is still
                stopped to prevent resource leaks.

        Note:
            Unsubscription errors are logged but do not prevent stopping
            the listener thread. Check logs for any failed unsubscriptions.
        """
        target = handle or self._event_bus_listener_handle
        if target is None:
            return True  # Nothing to stop

        unsubscribe_error: ModelOnexError | None = None

        # Unsubscribe from all events - fail fast if bus doesn't support unsubscribe
        # but still call target.stop() to prevent resource leaks
        bus = self._get_event_bus()
        if bus and target.subscriptions:
            if not hasattr(bus, "unsubscribe"):
                # Capture error but continue to stop the listener thread
                unsubscribe_error = ModelOnexError(
                    message="Event bus does not support 'unsubscribe' method",
                    error_code=EnumCoreErrorCode.EVENT_BUS_ERROR,
                    context={"bus_type": type(bus).__name__},
                )
            else:
                for subscription in target.subscriptions:
                    try:
                        # Cast to Any for legacy event bus interface
                        cast(Any, bus).unsubscribe(subscription)
                    except Exception as e:
                        self._log_error(
                            f"Failed to unsubscribe: {e!r}",
                            "event_listener",
                            error=e,
                        )

        # Always stop the listener thread, even if unsubscription failed
        result = target.stop()
        self._log_info("Event listener stopped", "event_listener")

        # Re-raise unsubscribe error after ensuring listener is stopped
        if unsubscribe_error is not None:
            raise unsubscribe_error

        return result

    def dispose_event_bus_resources(self) -> None:
        """Clean up all event bus resources. Call on shutdown.

        This method is idempotent and safe to call multiple times. It will not
        raise exceptions for already-disposed resources.

        Error Handling:
            All cleanup errors are collected and logged. If any errors occur
            during cleanup, a ModelOnexError is raised after all cleanup steps
            complete, containing details of all failures. This ensures:

            1. All cleanup steps are attempted even if earlier steps fail
            2. Errors are not silently swallowed
            3. Callers are notified of cleanup failures via structured errors

        Raises:
            ModelOnexError: If any cleanup step fails. The error context contains
                a list of all errors encountered during cleanup.
        """
        cleanup_errors: list[str] = []

        # Phase 1: Stop listener handle
        handle = self._event_bus_listener_handle
        if handle is not None:
            try:
                stopped = handle.stop()
                if not stopped:
                    cleanup_errors.append(
                        "Event listener did not stop within timeout"
                    )
            except Exception as e:
                cleanup_errors.append(f"Failed to stop event listener: {e!r}")
                emit_log_event(
                    LogLevel.ERROR,
                    f"MIXIN_DISPOSE: Failed to stop event listener: {e!r}",
                    ModelLogData(node_name=self.get_node_name()),
                )

        # Phase 2: Clear bindings - delete private instance attributes
        for attr in (
            "_bound_event_bus",
            "_bound_registry",
            "_mixin_event_bus_listener",
        ):
            if hasattr(self, attr):
                try:
                    object.__delattr__(self, attr)
                except AttributeError:
                    # AttributeError is EXPECTED during cleanup for two reasons:
                    # 1. Race condition: attribute deleted between hasattr() and delattr()
                    # 2. Idempotent cleanup: dispose() called multiple times
                    #
                    # We log at DEBUG (not WARNING) because this is expected behavior.
                    emit_log_event(
                        LogLevel.DEBUG,
                        f"MIXIN_DISPOSE: Attribute {attr} already deleted during cleanup",
                        ModelLogData(node_name=self.get_node_name()),
                    )
                except Exception as e:
                    # Unexpected error during attribute deletion
                    cleanup_errors.append(f"Failed to delete {attr}: {e!r}")
                    emit_log_event(
                        LogLevel.ERROR,
                        f"MIXIN_DISPOSE: Unexpected error deleting {attr}: {e!r}",
                        ModelLogData(node_name=self.get_node_name()),
                    )

        # Phase 3: Reset runtime state
        try:
            self._event_bus_runtime_state.reset()
        except Exception as e:
            cleanup_errors.append(f"Failed to reset runtime state: {e!r}")
            emit_log_event(
                LogLevel.ERROR,
                f"MIXIN_DISPOSE: Failed to reset runtime state: {e!r}",
                ModelLogData(node_name=self.get_node_name()),
            )

        # Log successful completion
        emit_log_event(
            LogLevel.DEBUG,
            "MIXIN_DISPOSE: Event bus resources disposed",
            ModelLogData(node_name=self.get_node_name()),
        )

        # Raise collected errors as structured ModelOnexError
        if cleanup_errors:
            raise ModelOnexError(
                message=f"Event bus cleanup completed with {len(cleanup_errors)} error(s)",
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                context={
                    "node_name": self.get_node_name(),
                    "error_count": len(cleanup_errors),
                    "errors": cleanup_errors,
                },
            )

    def _event_listener_loop(self, handle: "ModelEventBusListenerHandle") -> None:
        """Run the main event listener loop in a background thread.

        Subscribes to all event patterns from get_event_patterns() and waits
        for incoming events. The loop runs until the handle's stop_event is
        set or an unrecoverable error occurs.

        Args:
            handle: The listener handle containing the stop event and
                subscription list. Subscriptions are stored in the handle
                for cleanup during stop_event_listener().

        Note:
            This method is intended to be run in a daemon thread started
            by start_event_listener(). It should not be called directly.
            Subscription failures are logged but do not stop the loop.
        """
        try:
            patterns = self.get_event_patterns()
            if not patterns:
                self._log_warn("No event patterns to listen to", "event_listener")
                return

            bus = self._get_event_bus()
            if not bus:
                raise ModelOnexError(
                    message="No event bus available for subscription",
                    error_code=EnumCoreErrorCode.EVENT_BUS_ERROR,
                    context={"node_name": self.get_node_name()},
                )

            if not hasattr(bus, "subscribe"):
                raise ModelOnexError(
                    message="Event bus does not support 'subscribe' method",
                    error_code=EnumCoreErrorCode.EVENT_BUS_ERROR,
                    context={
                        "bus_type": type(bus).__name__,
                        "node_name": self.get_node_name(),
                    },
                )

            # Subscribe to all patterns
            # Note: Cast to Any for legacy event bus interface
            for pattern in patterns:
                try:
                    event_handler = self._create_event_handler(pattern)
                    subscription = cast(Any, bus).subscribe(
                        event_handler, event_type=pattern
                    )
                    handle.subscriptions.append(subscription)
                    self._log_info(f"Subscribed to pattern: {pattern}", pattern)
                except Exception as e:
                    self._log_error(
                        f"Failed to subscribe to {pattern}: {e!r}",
                        "subscribe",
                        error=e,
                    )

            # Keep thread alive
            while handle.stop_event is not None and not handle.stop_event.wait(1.0):
                pass

        except Exception as e:
            self._log_error(
                f"Event listener loop failed: {e!r}",
                "event_listener",
                error=e,
            )

    def _create_event_handler(self, pattern: str) -> Callable[..., Any]:
        """Create an event handler closure for a specific event pattern.

        Generates a handler function that extracts events from envelopes,
        converts them to typed input state, processes them via process(),
        and publishes completion events.

        Args:
            pattern: The event pattern string this handler will process
                (e.g., "generation.mynode.start"). Used for logging and
                error context.

        Returns:
            A callable handler function that accepts ProtocolEventEnvelope
            and processes the contained event. The handler manages its own
            error handling and publishes error completion events on failure.

        Note:
            The returned handler captures the pattern in its closure for
            logging and error reporting. Each pattern should have its own
            handler instance.
        """

        def handler(envelope: ProtocolEventEnvelope[ModelOnexEvent]) -> None:
            """Handle incoming event envelope."""
            # Extract event from envelope - fail fast if missing
            if not hasattr(envelope, "payload"):
                raise ModelOnexError(
                    message=f"Envelope missing required 'payload' attribute for pattern {pattern}",
                    error_code=EnumCoreErrorCode.VALIDATION_FAILED,
                    context={
                        "pattern": pattern,
                        "envelope_type": type(envelope).__name__,
                    },
                )

            event: ModelOnexEvent = envelope.payload

            # Validate event has required attributes - fail fast if missing
            if not hasattr(event, "event_type"):
                raise ModelOnexError(
                    message=f"Event missing required 'event_type' attribute for pattern {pattern}",
                    error_code=EnumCoreErrorCode.VALIDATION_FAILED,
                    context={"pattern": pattern, "event_type": type(event).__name__},
                )

            try:
                self._log_info(
                    f"Processing event: {event.event_type}",
                    str(event.event_type),
                )

                # Convert event to input state
                input_state = self._event_to_input_state(event)

                # Process through the node
                self.process(input_state)

                # Publish completion event
                completion_event_type = self.get_completion_event_type(
                    str(event.event_type)
                )
                completion_data = ModelCompletionData(
                    message=f"Processing completed for {event.event_type}",
                    success=True,
                    tags=["processed", "completed"],
                )

                self.publish_completion_event(completion_event_type, completion_data)

                self._log_info(
                    f"Event processing completed: {event.event_type}",
                    str(event.event_type),
                )

            except Exception as e:
                self._log_error(f"Event processing failed: {e!r}", pattern, error=e)

                # Publish error completion event
                try:
                    completion_event_type = self.get_completion_event_type(
                        str(event.event_type),
                    )
                    error_data = ModelCompletionData(
                        message=f"Processing failed: {e!s}",
                        success=False,
                        tags=["error", "failed"],
                    )
                    self.publish_completion_event(completion_event_type, error_data)
                except Exception as publish_error:
                    self._log_error(
                        f"Failed to publish error event: {publish_error!r}",
                        "publish_error",
                        error=publish_error,
                    )

        return handler

    def _event_to_input_state(self, event: ModelOnexEvent) -> InputStateT:
        """Convert ModelOnexEvent to typed input state for processing.

        Args:
            event: The incoming event to convert.

        Returns:
            The typed input state extracted from the event.

        Raises:
            ModelOnexError: If input state class cannot be determined.
        """
        try:
            input_state_class = self._get_input_state_class()
            if not input_state_class:
                msg = "Cannot determine input state class for event conversion"
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.VALIDATION_FAILED,
                )

            # Extract data from event - convert to dict if ModelEventData
            event_data_raw = event.data
            if event_data_raw is None:
                event_data: dict[str, object] = {}
            elif hasattr(event_data_raw, "model_dump"):
                event_data = event_data_raw.model_dump()
            else:
                event_data = {}

            # Try to create input state from event data
            if hasattr(input_state_class, "from_event"):
                result: InputStateT = input_state_class.from_event(event)
                return result
            # Create from event data directly
            return cast(InputStateT, input_state_class(**event_data))

        except Exception as e:
            self._log_error(
                f"Failed to convert event to input state: {e!r}",
                "event_conversion",
                error=e,
            )
            raise

    def _get_input_state_class(self) -> type | None:
        """Extract the input state class from generic type parameters.

        Uses Python's type introspection to find the InputStateT type
        argument from the class's generic bases. This enables type-safe
        event-to-state conversion in _event_to_input_state().

        Returns:
            The input state class (first generic type argument) or None
            if the class was not parameterized with concrete types.

        Raises:
            ModelOnexError: If type introspection fails due to unexpected
                AttributeError, TypeError, or IndexError.

        Example:
            >>> class MyNode(MixinEventBus[MyInputState, MyOutputState]): ...
            >>> node = MyNode()
            >>> node._get_input_state_class()  # Returns MyInputState
        """
        try:
            # Get the generic type arguments
            orig_bases = getattr(self.__class__, "__orig_bases__", ())
            for base in orig_bases:
                if hasattr(base, "__args__") and len(base.__args__) >= 1:
                    cls: type | None = base.__args__[0]
                    return cls
            return None
        except (AttributeError, TypeError, IndexError) as e:
            # Fail fast on unexpected errors during type introspection
            raise ModelOnexError(
                message=f"Failed to extract input state class from generic type parameters: {e!s}",
                error_code=EnumCoreErrorCode.INTERNAL_ERROR,
                context={
                    "node_name": self.get_node_name(),
                    "class_name": self.__class__.__name__,
                    "error_type": type(e).__name__,
                },
            ) from e

    # --- Logging Helpers ---

    def _log_info(self, msg: str, pattern: str) -> None:
        """Emit a structured INFO log with event pattern context.

        Args:
            msg: The log message to emit.
            pattern: Event pattern or operation identifier for context
                (e.g., "event_listener", "publish_completion", topic name).
        """
        emit_log_event(
            LogLevel.INFO,
            msg,
            context={"pattern": pattern, "node_name": self.get_node_name()},
        )

    def _log_warn(self, msg: str, pattern: str) -> None:
        """Emit a structured WARNING log with event pattern context.

        Args:
            msg: The warning message to emit.
            pattern: Event pattern or operation identifier for context.
        """
        emit_log_event(
            LogLevel.WARNING,
            msg,
            context={"pattern": pattern, "node_name": self.get_node_name()},
        )

    def _log_error(
        self,
        msg: str,
        pattern: str,
        error: BaseException | None = None,
    ) -> None:
        """Emit a structured ERROR log with event pattern and exception context.

        Args:
            msg: The error message to emit.
            pattern: Event pattern or operation identifier for context.
            error: Optional exception that caused the error. If provided,
                its repr() is included in the log context for debugging.
        """
        emit_log_event(
            LogLevel.ERROR,
            msg,
            context={
                "pattern": pattern,
                "node_name": self.get_node_name(),
                "error": None if error is None else repr(error),
            },
        )
