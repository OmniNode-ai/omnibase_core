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

import inspect
import threading
from collections.abc import Callable
from typing import (
    Generic,
    Protocol,
    TypeVar,
    runtime_checkable,
)

from omnibase.protocols.types import LogLevel
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr

from omnibase_core.core.core_error_codes import CoreErrorCode
from omnibase_core.core.core_structured_logging import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.exceptions import OnexError
from omnibase_core.model.core.model_onex_event import OnexEvent

# Generic type variables for input and output states
InputStateT = TypeVar("InputStateT")
OutputStateT = TypeVar("OutputStateT")


# --- Protocols ---------------------------------------------------------------


@runtime_checkable
class ProtocolEventBus(Protocol):
    """Protocol for synchronous event bus."""

    def publish(self, event: OnexEvent) -> None: ...

    def publish_event(self, event: OnexEvent) -> None: ...


@runtime_checkable
class AsyncProtocolEventBus(Protocol):
    """Protocol for asynchronous event bus."""

    async def publish(self, event: OnexEvent) -> None: ...

    async def publish_event(self, event: OnexEvent) -> None: ...


class RegistryWithBus(Protocol):
    """Protocol for registry that provides event bus."""

    event_bus: ProtocolEventBus | AsyncProtocolEventBus | None


class LogEmitter(Protocol):
    """Protocol for log emission."""

    def emit_log_event(
        self,
        level: LogLevel,
        message: str,
        data: "ModelLogData",
    ) -> None: ...


# --- Canonical Completion Data Model ----------------------------------------


class ModelCompletionData(BaseModel):
    """
    Canonical payload for completion events following ONEX naming conventions.

    Fields are optional so producers can send only relevant data.
    Uses Strict* types to prevent silent type coercion.
    """

    model_config = ConfigDict(
        extra="forbid",  # Catch typos early
        frozen=True,  # Immutable instances for safer passing
    )

    message: StrictStr | None = Field(
        default=None,
        description="Human-readable completion message",
    )
    success: StrictBool | None = Field(
        default=None,
        description="Whether the operation succeeded",
    )
    code: StrictInt | None = Field(
        default=None,
        description="Numeric status or error code",
    )
    tags: list[StrictStr] | None = Field(
        default=None,
        description="Labels for search/filtering",
    )

    def to_event_kwargs(self) -> dict[str, str | bool | int | list[str]]:
        """Convert to kwargs for OnexEvent creation, excluding None values."""
        return self.model_dump(exclude_none=True)


# --- Log Data Model ----------------------------------------------------------


class ModelLogData(BaseModel):
    """Log data model for structured logging in event bus operations."""

    error: str | None = None
    pattern: str | None = None
    event_type: str | None = None
    node_name: str | None = None


# --- Unified Event Bus Mixin ------------------------------------------------


class MixinEventBus(BaseModel, Generic[InputStateT, OutputStateT]):
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
        extra="forbid",
        arbitrary_types_allowed=True,  # Allow threading objects
    )

    # Required fields following ONEX naming conventions
    node_name: StrictStr = Field(description="Name of this node")
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

    def model_post_init(self, __context):
        """Initialize threading objects after Pydantic validation."""
        self.event_listener_thread = None
        self.stop_event = threading.Event()
        self.event_subscriptions = []

        emit_log_event(
            LogLevel.DEBUG,
            "🏗️ MIXIN_INIT: Initializing unified MixinEventBus",
            ModelLogData(node_name=self.node_name),
        )

        # Auto-start listener if event bus is available after full initialization
        if self._has_event_bus():
            threading.Timer(0.1, self._auto_start_listener).start()

    # --- Node Interface Methods (to be overridden by subclasses) ------------

    def get_node_name(self) -> str:
        """Get the name of this node."""
        return self.node_name

    def process(self, input_state: InputStateT) -> OutputStateT:
        """
        Process input state and return output state.

        Default implementation - override in subclasses for actual processing.
        """
        msg = "Subclasses must implement process method"
        raise NotImplementedError(msg)

    # --- Event Bus Access (Protocol-based) ----------------------------------

    def _get_event_bus(
        self,
    ) -> ProtocolEventBus | AsyncProtocolEventBus | None:
        """Resolve event bus using protocol-based polymorphism."""
        # Try registry first
        if hasattr(self, "registry") and hasattr(self.registry, "event_bus"):
            return getattr(self.registry, "event_bus", None)
        # Fall back to direct event_bus attribute
        return getattr(self, "event_bus", None)

    def _has_event_bus(self) -> bool:
        """Check if event bus is available."""
        return self._get_event_bus() is not None

    # --- Event Completion Publishing ----------------------------------------

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
        """
        bus = self._get_event_bus()
        if bus is None:
            self._log_warn(
                "No event bus available in registry for completion event",
                event_type,
            )
            return

        if isinstance(bus, AsyncProtocolEventBus) and not isinstance(
            bus,
            ProtocolEventBus,
        ):
            self._log_error(
                "registry.event_bus is async-only; call 'await apublish_completion_event(...)' instead",
                event_type,
            )
            return

        if not isinstance(bus, ProtocolEventBus):
            self._log_error(
                f"registry.event_bus does not satisfy ProtocolEventBus (got {type(bus).__name__})",
                event_type,
            )
            return

        try:
            event = self._build_event(event_type, data)
            # Try publish_event first (preferred), then publish
            if hasattr(bus, "publish_event"):
                bus.publish_event(event)
            else:
                bus.publish(event)
            self._log_info(f"Published completion event: {event_type}", event_type)
        except Exception as e:
            self._log_error(
                f"Failed to publish completion event: {e!r}",
                event_type,
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
        """
        bus = self._get_event_bus()
        if bus is None:
            self._log_warn(
                "No event bus available in registry for completion event",
                event_type,
            )
            return

        try:
            event = self._build_event(event_type, data)

            if isinstance(bus, AsyncProtocolEventBus):
                if hasattr(bus, "publish_event"):
                    await bus.publish_event(event)
                else:
                    await bus.publish(event)
            elif isinstance(bus, ProtocolEventBus):
                if hasattr(bus, "publish_event"):
                    bus.publish_event(event)
                else:
                    bus.publish(event)
            else:
                # Fallback for poorly-typed buses using duck typing
                publish = getattr(bus, "publish_event", None) or getattr(
                    bus,
                    "publish",
                    None,
                )
                if publish is None:
                    self._log_error(
                        f"registry.event_bus has no 'publish' or 'publish_event' method (got {type(bus).__name__})",
                        event_type,
                    )
                    return
                if inspect.iscoroutinefunction(publish):
                    await publish(event)
                else:
                    publish(event)

            self._log_info(f"Published completion event: {event_type}", event_type)

        except Exception as e:
            self._log_error(
                f"Failed to publish completion event: {e!r}",
                event_type,
                error=e,
            )

    def _build_event(self, event_type: str, data: ModelCompletionData) -> OnexEvent:
        """Build OnexEvent from completion data."""
        return OnexEvent.create_core_event(
            event_type=event_type,
            node_id=self.get_node_name(),
            **data.to_event_kwargs(),
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
            return []

    def get_completion_event_type(self, input_event_type: str) -> str:
        """
        Get completion event type for a given input event.

        Maps input events to their corresponding completion events.
        """
        try:
            if isinstance(input_event_type, str):
                event_str = input_event_type
            else:
                event_str = str(input_event_type)

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
            return f"{input_event_type}.complete"

    def start_event_listener(self):
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

        self.stop_event.clear()
        self.event_listener_thread = threading.Thread(
            target=self._event_listener_loop,
            daemon=True,
            name=f"EventListener-{self.get_node_name()}",
        )
        self.event_listener_thread.start()

        self._log_info("Event listener started", "event_listener")

    def stop_event_listener(self):
        """Stop the event listener thread."""
        if not self.event_listener_thread:
            return

        self.stop_event.set()

        # Unsubscribe from all events
        bus = self._get_event_bus()
        if bus and hasattr(bus, "unsubscribe"):
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

    def _auto_start_listener(self):
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

    def _event_listener_loop(self):
        """Main event listener loop."""
        try:
            patterns = self.get_event_patterns()
            if not patterns:
                self._log_warn("No event patterns to listen to", "event_listener")
                return

            bus = self._get_event_bus()
            if not bus or not hasattr(bus, "subscribe"):
                self._log_error(
                    "Event bus does not support subscription",
                    "event_listener",
                )
                return

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
                        pattern,
                        error=e,
                    )

            # Keep thread alive
            while not self.stop_event.wait(1.0):
                pass

        except Exception as e:
            self._log_error(
                f"Event listener loop failed: {e!r}",
                "event_listener",
                error=e,
            )

    def _create_event_handler(self, pattern: str) -> Callable:
        """Create event handler for a specific pattern."""

        def handler(event: OnexEvent):
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
                completion_event_type = self.get_completion_event_type(event.event_type)
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
                        event.event_type,
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
                        pattern,
                        error=publish_error,
                    )

        return handler

    def _event_to_input_state(self, event: OnexEvent) -> InputStateT:
        """Convert OnexEvent to input state for processing."""
        try:
            input_state_class = self._get_input_state_class()
            if not input_state_class:
                msg = "Cannot determine input state class for event conversion"
                raise OnexError(
                    msg,
                    error_code=CoreErrorCode.VALIDATION_FAILED,
                )

            # Extract data from event
            event_data = event.data or {}

            # Try to create input state from event data
            if hasattr(input_state_class, "from_event"):
                return input_state_class.from_event(event)
            # Create from event data directly
            return input_state_class(**event_data)

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
                    return base.__args__[0]
            return None
        except Exception:
            return None

    # --- Logging Helpers -----------------------------------------------------

    def _log_info(self, msg: str, pattern: str) -> None:
        """Log info message with pattern."""
        emit_log_event(
            LogLevel.INFO,
            msg,
            ModelLogData(pattern=pattern, node_name=self.get_node_name()),
        )

    def _log_warn(self, msg: str, pattern: str) -> None:
        """Log warning message with pattern."""
        emit_log_event(
            LogLevel.WARNING,
            msg,
            ModelLogData(pattern=pattern, node_name=self.get_node_name()),
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
            ModelLogData(
                pattern=pattern,
                node_name=self.get_node_name(),
                error=None if error is None else repr(error),
            ),
        )
