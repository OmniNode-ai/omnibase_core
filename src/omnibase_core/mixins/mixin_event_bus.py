from collections.abc import Callable
from typing import Any, cast

from pydantic import Field

from omnibase_core.errors import OnexError
from omnibase_core.models.errors.model_onex_error import ModelOnexError

"""
Unified Event Bus Mixin for ONEX Nodes

Provides comprehensive event bus capabilities including:
- Event subscription and listening
- Event completion publishing
- Protocol-based polymorphism
- ONEX standards compliance
- Error handling and logging

This mixin replaces and unifies MixinEventListener and MixinEventBusCompletion.
"""

import threading
import uuid
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StrictStr, ValidationError

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.protocols import ProtocolEventEnvelope

# Local imports from extracted classes
from .mixin_completion_data import MixinCompletionData
from .mixin_log_data import MixinLogData


class MixinEventBus[InputStateT, OutputStateT](BaseModel):
    """
    Unified mixin for all event bus operations in ONEX nodes.

    Provides:
    - Event listening and subscription capabilities
    - Completion event publishing with proper protocols
    - ONEX standards compliance (no dictionaries, proper models)
    - Protocol-based polymorphism for event bus access
    - Error handling and structured logging
    """

    model_config = ConfigDict(
        extra="forbid",  # Strict validation, no extra fields
        arbitrary_types_allowed=True,  # Allow threading objects
    )

    # Fields following ONEX naming conventions (node_name computed if empty)
    node_name: StrictStr = Field(
        default="",  # Computed in model_post_init if empty
        description="Name of this node",
    )
    registry: object | None = Field(
        default=None,
        description="Registry with event bus access",
    )
    event_bus: object | None = Field(
        default=None,
        description="Direct event bus reference",
    )
    contract_path: StrictStr | None = Field(
        default=None,
        description="Path to contract file",
    )

    # Private fields for event listening (excluded from serialization)
    event_listener_thread: threading.Thread | None = Field(
        default=None,
        exclude=True,
    )
    stop_event: threading.Event | None = Field(default=None, exclude=True)
    event_subscriptions: list[object] = Field(default_factory=list, exclude=True)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize MixinEventBus with proper BaseModel initialization.

        This ensures __pydantic_extra__ is properly initialized before
        other mixins try to set attributes. Accepts both positional args
        (from MRO chain) and keyword args (for BaseModel fields).

        Note: We need to handle the case where this mixin is used in classes
        that inherit from both BaseModel (via this mixin) and non-Pydantic
        classes (like NodeCoreBase). We use object.__setattr__() to bypass
        Pydantic validation for fields that will be set by parent classes.
        """
        # Default node_name if not provided
        if "node_name" not in kwargs:
            kwargs["node_name"] = "UnknownNode"

        # Initialize BaseModel's internal state manually to avoid validation errors
        # for fields that are set by other parent classes (like NodeCoreBase)
        try:
            # Try normal initialization first
            super().__init__(**kwargs)
        except ValidationError:
            # If Pydantic validation fails (due to required fields from non-Pydantic parents),
            # initialize BaseModel's internals manually and let parent __init__ set fields
            emit_log_event(
                LogLevel.DEBUG,
                "Using fallback initialization for MixinEventBus due to mixed Pydantic/non-Pydantic inheritance",
                {"node_name": kwargs.get("node_name", "UnknownNode")},
            )
            object.__setattr__(self, "__pydantic_extra__", {})
            object.__setattr__(self, "__pydantic_fields_set__", set())
            object.__setattr__(self, "__pydantic_private__", {})

            # Set our own fields
            for field_name, field_value in kwargs.items():
                object.__setattr__(self, field_name, field_value)

            # Call next in MRO (skip BaseModel validation)
            # Find the next class after BaseModel in MRO
            mro = type(self).__mro__
            for i, cls in enumerate(mro):
                if cls is MixinEventBus:
                    # Skip to class after MixinMetrics (next non-Pydantic class)
                    for j in range(i + 1, len(mro)):
                        if hasattr(mro[j], "__init__") and mro[j] is not BaseModel:
                            # Call the next __init__ in chain if it exists
                            if mro[j].__init__ is not object.__init__:  # type: ignore[misc]
                                mro[j].__init__(self, *args, **kwargs)  # type: ignore[misc]
                            break
                    break

    def model_post_init(self, __context: Any) -> None:
        """Initialize threading objects after Pydantic validation."""
        # Compute node_name from class name if not provided or empty
        if not self.node_name or self.node_name == "UnknownNode":
            object.__setattr__(self, "node_name", self.__class__.__name__)

        self.event_listener_thread = None
        self.stop_event = threading.Event()
        self.event_subscriptions = []

        emit_log_event(
            LogLevel.DEBUG,
            "🏗️ MIXIN_INIT: Initializing unified MixinEventBus",
            MixinLogData(node_name=self.node_name),
        )

        # Auto-start listener if event bus is available after full initialization
        if self._has_event_bus():
            timer = threading.Timer(0.1, self._auto_start_listener)
            timer.daemon = True
            timer.start()

    # --- Node Interface Methods (to be overridden by subclasses) ------------

    def get_node_name(self) -> str:
        """Get the name of this node."""
        return self.node_name

    def get_node_id(self) -> UUID:
        """Get the UUID for this node (derived from node name)."""
        # Try to get actual node_id if available, otherwise generate from name
        if hasattr(self, "_node_id") and isinstance(self._node_id, UUID):
            return self._node_id
        # Generate deterministic UUID from node name using standard uuid5
        # Uses DNS namespace as a well-known namespace for name-based UUIDs
        return uuid.uuid5(uuid.NAMESPACE_DNS, self.node_name)

    def process(self, input_state: InputStateT) -> OutputStateT:
        """
        Process input state and return output state.

        Default implementation - override in subclasses for actual processing.
        """
        msg = "Subclasses must implement process method"
        raise NotImplementedError(msg)  # stub-ok: abstract method

    # --- Event Bus Access (Protocol-based) ----------------------------------

    def _get_event_bus(self) -> Any:
        """
        Resolve event bus using duck-typed polymorphism.

        Note: Returns Any because event bus implementations use duck-typing
        and don't conform to a single protocol interface.
        """
        # Try registry first
        if hasattr(self, "registry") and hasattr(self.registry, "event_bus"):
            return getattr(self.registry, "event_bus", None)
        # Fall back to direct event_bus attribute
        return getattr(self, "event_bus", None)

    def _has_event_bus(self) -> bool:
        """Check if event bus is available."""
        return self._get_event_bus() is not None

    # --- Event Completion Publishing ----------------------------------------

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
        """
        bus = self._get_event_bus()
        if bus is None:
            self._log_warn(
                "No event bus available for event publishing",
                pattern="event_bus.missing",
            )
            return

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

        except Exception as e:
            self._log_error(
                f"Failed to publish event: {e!r}",
                "publish_event",
                error=e,
            )

    def publish_completion_event(
        self,
        event_type: str,
        data: MixinCompletionData,
    ) -> None:
        """
        Publish completion event using synchronous event bus.

        Args:
            event_type: Event type string (e.g., "generation.health.complete")
            data: Completion data model
        """
        bus = self._get_event_bus()
        if bus is None:
            self._log_warn(
                "No event bus available in registry for completion event",
                pattern="event_bus.missing",
            )
            return

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
            if hasattr(bus, "publish"):
                bus.publish(event)
            else:
                raise OnexError(
                    message="Event bus has no synchronous 'publish' method",
                    error_code="EVENT_BUS_MISSING_SYNC_PUBLISH",
                    context={"bus_type": type(bus).__name__, "event_type": event_type},
                )
            self._log_info(f"Published completion event: {event_type}", event_type)
        except Exception as e:
            self._log_error(
                f"Failed to publish completion event: {e!r}",
                "publish_completion",
                error=e,
            )

    async def apublish_completion_event(
        self,
        event_type: str,
        data: MixinCompletionData,
    ) -> None:
        """
        Publish completion event using asynchronous event bus.

        Supports both async and sync buses for maximum compatibility.

        Args:
            event_type: Event type string (e.g., "generation.health.complete")
            data: Completion data model
        """
        bus = self._get_event_bus()
        if bus is None:
            self._log_warn(
                "No event bus available in registry for completion event",
                pattern="event_bus.missing",
            )
            return

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

        except Exception as e:
            self._log_error(
                f"Failed to publish completion event: {e!r}",
                "publish_completion",
                error=e,
            )

    def _build_event(
        self, event_type: str, data: MixinCompletionData
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

    # --- Event Listening and Subscription -----------------------------------

    def get_event_patterns(self) -> list[str]:
        """
        Get event patterns this node should listen to.

        Default implementation extracts patterns from contract file.
        Override in subclasses for custom patterns.
        """
        try:
            contract_path = getattr(self, "contract_path", None)
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

    def start_event_listener(self) -> None:
        """Start the event listener thread."""
        if not self._has_event_bus():
            self._log_warn(
                "Cannot start event listener: no event bus available",
                "event_listener",
            )
            return

        if self.event_listener_thread and self.event_listener_thread.is_alive():
            self._log_warn("Event listener already running", "event_listener")
            return

        if self.stop_event is not None:
            self.stop_event.clear()
        self.event_listener_thread = threading.Thread(
            target=self._event_listener_loop,
            daemon=True,
            name=f"EventListener-{self.get_node_name()}",
        )
        self.event_listener_thread.start()

        self._log_info("Event listener started", "event_listener")

    def stop_event_listener(self) -> None:
        """Stop the event listener thread."""
        if not self.event_listener_thread:
            return

        if self.stop_event is not None:
            self.stop_event.set()

        # Unsubscribe from all events - fail fast if bus doesn't support unsubscribe
        bus = self._get_event_bus()
        if bus:
            if not hasattr(bus, "unsubscribe"):
                raise OnexError(
                    message="Event bus does not support 'unsubscribe' method",
                    error_code="EVENT_BUS_MISSING_UNSUBSCRIBE",
                    context={"bus_type": type(bus).__name__},
                )

            for subscription in self.event_subscriptions:
                try:
                    bus.unsubscribe(subscription)
                except Exception as e:
                    self._log_error(
                        f"Failed to unsubscribe: {e!r}",
                        "event_listener",
                        error=e,
                    )

        self.event_subscriptions.clear()

        if self.event_listener_thread.is_alive():
            self.event_listener_thread.join(timeout=5.0)

        self._log_info("Event listener stopped", "event_listener")

    def _auto_start_listener(self) -> None:
        """Auto-start listener after initialization delay."""
        try:
            if self._has_event_bus():
                self.start_event_listener()
        except Exception as e:
            self._log_error(
                f"Failed to auto-start listener: {e!r}",
                "auto_start",
                error=e,
            )

    def _event_listener_loop(self) -> None:
        """Main event listener loop."""
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
                    handler = self._create_event_handler(pattern)
                    subscription = bus.subscribe(handler, event_type=pattern)
                    self.event_subscriptions.append(subscription)
                    self._log_info(f"Subscribed to pattern: {pattern}", pattern)
                except Exception as e:
                    self._log_error(
                        f"Failed to subscribe to {pattern}: {e!r}",
                        "subscribe",
                        error=e,
                    )

            # Keep thread alive
            while self.stop_event is not None and not self.stop_event.wait(1.0):
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
                completion_data = MixinCompletionData(
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
                    error_data = MixinCompletionData(
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
        """Convert ModelOnexEvent to input state for processing."""
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
                result = input_state_class.from_event(event)
                return cast("InputStateT", result)
            # Create from event data directly
            result = input_state_class(**event_data)
            return cast("InputStateT", result)

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

    # --- Logging Helpers -----------------------------------------------------

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
