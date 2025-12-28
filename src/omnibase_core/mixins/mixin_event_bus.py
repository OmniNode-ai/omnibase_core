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
from omnibase_core.errors import OnexError
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
        if not hasattr(self, attr_name):
            state = ModelEventBusRuntimeState.create_unbound()
            object.__setattr__(self, attr_name, state)
        return cast(ModelEventBusRuntimeState, object.__getattribute__(self, attr_name))

    @property
    def _event_bus_listener_handle(self) -> "ModelEventBusListenerHandle | None":
        """Lazy accessor for listener handle - may be None if never started."""
        from omnibase_core.models.event_bus import ModelEventBusListenerHandle

        attr_name = "_mixin_event_bus_listener"
        if not hasattr(self, attr_name):
            return None
        return cast(
            ModelEventBusListenerHandle | None,
            object.__getattribute__(self, attr_name),
        )

    # --- Explicit Binding Methods ---

    def bind_event_bus(self, event_bus: ProtocolEventBus) -> None:
        """Explicitly bind an event bus. Required before publishing.

        Args:
            event_bus: The event bus instance to bind.
        """
        object.__setattr__(self, "_bound_event_bus", event_bus)
        self._event_bus_runtime_state.is_bound = True

        emit_log_event(
            LogLevel.DEBUG,
            "MIXIN_BIND: Event bus bound to mixin",
            ModelLogData(node_name=self.get_node_name()),
        )

    def bind_registry(self, registry: ProtocolEventBusRegistry) -> None:
        """Bind a registry that has event_bus access.

        Args:
            registry: A registry implementing ProtocolEventBusRegistry.
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
        """Bind contract path for event patterns.

        Args:
            contract_path: Path to the contract YAML file.
        """
        self._event_bus_runtime_state.contract_path = contract_path

    def bind_node_name(self, node_name: str) -> None:
        """Bind the node name for event publishing.

        Args:
            node_name: The name of this node.
        """
        self._event_bus_runtime_state.node_name = node_name

    # --- Fail-Fast Event Bus Access ---

    def _require_event_bus(self) -> Any:
        """Get event bus or raise RuntimeError if not bound.

        Note:
            Returns Any because event bus implementations use duck-typing.
            The protocol types (ProtocolEventBus, etc.) are used for binding,
            but runtime behavior relies on hasattr checks for method availability.

        Returns:
            The bound event bus instance.

        Raises:
            RuntimeError: If no event bus is bound.
        """
        bus = self._get_event_bus()
        if bus is None:
            raise RuntimeError(
                f"Event bus not bound on {self.__class__.__name__}. "
                "Call bind_event_bus() or bind_registry() before publishing."
            )
        return bus

    def _get_event_bus(self) -> Any:
        """
        Resolve event bus using duck-typed polymorphism.

        Note: Returns Any because event bus implementations use duck-typing
        and don't conform to a single protocol interface.

        Returns:
            The event bus instance or None if not bound.
        """
        # Try direct event_bus binding first
        if hasattr(self, "_bound_event_bus"):
            bus = object.__getattribute__(self, "_bound_event_bus")
            if bus is not None:
                return bus

        # Try registry binding
        if hasattr(self, "_bound_registry"):
            registry = object.__getattribute__(self, "_bound_registry")
            if hasattr(registry, "event_bus"):
                return getattr(registry, "event_bus", None)

        return None

    def _has_event_bus(self) -> bool:
        """Check if event bus is available."""
        return self._get_event_bus() is not None

    # --- Node Interface Methods (to be overridden by subclasses) ---

    def get_node_name(self) -> str:
        """Get the name of this node."""
        state = self._event_bus_runtime_state
        if state.node_name:
            return state.node_name
        return self.__class__.__name__

    def get_node_id(self) -> UUID:
        """Get the UUID for this node (derived from node name)."""
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
            RuntimeError: If event bus is not bound.
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
                await bus.publish_async(envelope)
            elif hasattr(bus, "publish"):
                bus.publish(event)  # Synchronous method - no await
            else:
                raise OnexError(
                    message="Event bus does not support publishing (missing 'publish_async' and 'publish' methods)",
                    error_code="EVENT_BUS_MISSING_PUBLISH_METHOD",
                    context={"bus_type": type(bus).__name__, "event_type": event_type},
                )

            self._log_info(f"Published event: {event_type}", event_type)

        except RuntimeError:
            raise  # Re-raise RuntimeError from _require_event_bus
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
            RuntimeError: If event bus is not bound.
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
            if hasattr(bus, "publish"):
                bus.publish(event)
            else:
                raise OnexError(
                    message="Event bus has no synchronous 'publish' method",
                    error_code="EVENT_BUS_MISSING_SYNC_PUBLISH",
                    context={"bus_type": type(bus).__name__, "event_type": event_type},
                )
            self._log_info(f"Published completion event: {event_type}", event_type)
        except RuntimeError:
            raise  # Re-raise RuntimeError from _require_event_bus
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
            RuntimeError: If event bus is not bound.
        """
        bus = self._require_event_bus()

        try:
            event = self._build_event(event_type, data)

            # Prefer async publishing if available - fail fast if no publish method
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
                await bus.publish_async(envelope)
            # Fallback to sync method
            elif hasattr(bus, "publish"):
                bus.publish(event)  # Synchronous method - no await
            else:
                raise OnexError(
                    message="Event bus has no publish method (missing 'publish_async' and 'publish')",
                    error_code="EVENT_BUS_MISSING_PUBLISH_METHOD",
                    context={"bus_type": type(bus).__name__, "event_type": event_type},
                )

            self._log_info(f"Published completion event: {event_type}", event_type)

        except RuntimeError:
            raise  # Re-raise RuntimeError from _require_event_bus
        except Exception as e:
            self._log_error(
                f"Failed to publish completion event: {e!r}",
                "publish_completion",
                error=e,
            )

    def _build_event(
        self, event_type: str, data: ModelCompletionData
    ) -> ModelOnexEvent:
        """Build ModelOnexEvent from completion data."""
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
        """
        Get event patterns this node should listen to.

        Default implementation extracts patterns from contract file.
        Override in subclasses for custom patterns.
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
        """
        Get completion event type for a given input event.

        Maps input events to their corresponding completion events.
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
        """Start event listener. Returns handle for lifecycle management.

        Idempotent - returns existing handle if already running.

        Returns:
            Handle for managing the listener lifecycle.

        Raises:
            RuntimeError: If no event bus is available.
        """
        from omnibase_core.models.event_bus import ModelEventBusListenerHandle

        # Return existing handle if already running
        existing = self._event_bus_listener_handle
        if existing is not None and existing.is_active():
            self._log_warn("Event listener already running", "event_listener")
            return existing

        if not self._has_event_bus():
            raise RuntimeError(
                f"Cannot start event listener on {self.__class__.__name__}: "
                "no event bus available. Call bind_event_bus() or bind_registry() first."
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
        """Stop event listener. Safe to call multiple times.

        Args:
            handle: Optional handle. If None, stops current listener.

        Returns:
            True if stopped cleanly, False if timeout or no listener.
        """
        target = handle or self._event_bus_listener_handle
        if target is None:
            return True  # Nothing to stop

        # Unsubscribe from all events - fail fast if bus doesn't support unsubscribe
        bus = self._get_event_bus()
        if bus and target.subscriptions:
            if not hasattr(bus, "unsubscribe"):
                raise OnexError(
                    message="Event bus does not support 'unsubscribe' method",
                    error_code="EVENT_BUS_MISSING_UNSUBSCRIBE",
                    context={"bus_type": type(bus).__name__},
                )

            for subscription in target.subscriptions:
                try:
                    bus.unsubscribe(subscription)
                except Exception as e:
                    self._log_error(
                        f"Failed to unsubscribe: {e!r}",
                        "event_listener",
                        error=e,
                    )

        result = target.stop()
        self._log_info("Event listener stopped", "event_listener")
        return result

    def dispose_event_bus_resources(self) -> None:
        """Clean up all event bus resources. Call on shutdown."""
        handle = self._event_bus_listener_handle
        if handle is not None:
            handle.stop()

        # Clear bindings
        for attr in (
            "_bound_event_bus",
            "_bound_registry",
            "_mixin_event_bus_listener",
        ):
            if hasattr(self, attr):
                try:
                    object.__delattr__(self, attr)
                except AttributeError:
                    pass  # Already deleted

        self._event_bus_runtime_state.reset()

        emit_log_event(
            LogLevel.DEBUG,
            "MIXIN_DISPOSE: Event bus resources disposed",
            ModelLogData(node_name=self.get_node_name()),
        )

    def _event_listener_loop(self, handle: "ModelEventBusListenerHandle") -> None:
        """Main event listener loop.

        Args:
            handle: The listener handle for this loop.
        """
        try:
            patterns = self.get_event_patterns()
            if not patterns:
                self._log_warn("No event patterns to listen to", "event_listener")
                return

            bus = self._get_event_bus()
            if not bus:
                raise OnexError(
                    message="No event bus available for subscription",
                    error_code="EVENT_BUS_NOT_AVAILABLE",
                    context={"node_name": self.get_node_name()},
                )

            if not hasattr(bus, "subscribe"):
                raise OnexError(
                    message="Event bus does not support 'subscribe' method",
                    error_code="EVENT_BUS_MISSING_SUBSCRIBE",
                    context={
                        "bus_type": type(bus).__name__,
                        "node_name": self.get_node_name(),
                    },
                )

            # Subscribe to all patterns
            for pattern in patterns:
                try:
                    event_handler = self._create_event_handler(pattern)
                    subscription = bus.subscribe(event_handler, event_type=pattern)
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
        """Create event handler for a specific pattern."""

        def handler(envelope: ProtocolEventEnvelope[ModelOnexEvent]) -> None:
            """Handle incoming event envelope."""
            # Extract event from envelope - fail fast if missing
            if not hasattr(envelope, "payload"):
                raise OnexError(
                    message=f"Envelope missing required 'payload' attribute for pattern {pattern}",
                    error_code="EVENT_BUS_INVALID_ENVELOPE",
                    context={
                        "pattern": pattern,
                        "envelope_type": type(envelope).__name__,
                    },
                )

            event: ModelOnexEvent = envelope.payload

            # Validate event has required attributes - fail fast if missing
            if not hasattr(event, "event_type"):
                raise OnexError(
                    message=f"Event missing required 'event_type' attribute for pattern {pattern}",
                    error_code="EVENT_BUS_INVALID_EVENT",
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
        """Get the input state class from generic type parameters."""
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
            raise OnexError(
                message=f"Failed to extract input state class from generic type parameters: {e!s}",
                error_code="EVENT_BUS_TYPE_INTROSPECTION_FAILED",
                context={
                    "node_name": self.get_node_name(),
                    "class_name": self.__class__.__name__,
                },
            ) from e

    # --- Logging Helpers ---

    def _log_info(self, msg: str, pattern: str) -> None:
        """Log info message with pattern."""
        emit_log_event(
            LogLevel.INFO,
            msg,
            context={"pattern": pattern, "node_name": self.get_node_name()},
        )

    def _log_warn(self, msg: str, pattern: str) -> None:
        """Log warning message with pattern."""
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
        """Log error message with pattern and optional error details."""
        emit_log_event(
            LogLevel.ERROR,
            msg,
            context={
                "pattern": pattern,
                "node_name": self.get_node_name(),
                "error": None if error is None else repr(error),
            },
        )
