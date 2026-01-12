"""
Event Listener Mixin for ONEX Tool Nodes.

Provides event-driven execution capabilities to tool nodes by:
- Subscribing to events based on tool's contract
- Converting events to tool input state
- Executing tool's process method
- Publishing completion events
- Managing event lifecycle and error handling

Security:
    This mixin uses importlib.import_module() to dynamically load input state
    model classes from node modules. Security is enforced via namespace validation:

    **Namespace Allowlist** (_get_input_state_from_node_module):
        Dynamic imports are restricted to modules matching these prefixes:
        - omnibase_core.*
        - omnibase_spi.*
        - omnibase.*

        Attempts to import modules outside these namespaces are blocked with
        a warning log and return None instead of raising an exception.

    **Event Content**:
        Event payloads are treated as UNTRUSTED data. They are:
        - Validated against Pydantic models before processing
        - Converted to strongly-typed input state classes
        - Errors during validation are caught and logged

    Trust Model:
        - Module namespace: Validated against allowlist (TRUSTED namespaces only)
        - Event bus: Assumed to be from trusted infrastructure
        - Event payload: UNTRUSTED (validated via Pydantic)
        - Contract file content: Validated via load_and_validate_yaml_model

    See Also:
        - MixinIntrospectFromContract: Similar namespace validation pattern
        - util_safe_yaml_loader.py: YAML parsing security for contracts
"""

from __future__ import annotations

import asyncio
import inspect
import re
import threading
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, cast
from uuid import UUID

from pydantic import ValidationError

from omnibase_core.constants import THREAD_JOIN_TIMEOUT_SECONDS

if TYPE_CHECKING:
    from omnibase_core.protocols.event_bus import ProtocolEventBusListener
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS
from omnibase_core.logging.logging_structured import (
    emit_log_event_sync as emit_log_event,
)
from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.validation.validator_contracts import load_and_validate_yaml_model

# Note: Event bus uses duck-typing interface, not a formal protocol
# The omnibase_spi ProtocolEventBus is Kafka-based and incompatible with this interface


class MixinEventListener[InputStateT, OutputStateT]:
    """
    Mixin that provides event listening capabilities to tool nodes.

    Tools that inherit from this mixin can automatically:
    - Listen for events matching their contract patterns
    - Process events through their standard process() method
    - Publish completion events with results

    Usage:
        class MyTool(MixinEventListener, ProtocolReducer):
            def __init__(self, event_bus=None, **kwargs):
                super().__init__(**kwargs)
                self.event_bus = event_bus
                # Start listening if event bus provided
                if event_bus:
                    self.start_event_listener()
    """

    def __init__(self, **kwargs: object) -> None:
        """Initialize the event listener mixin."""
        super().__init__(**kwargs)
        self._event_listener_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._event_subscriptions: list[tuple[str, object]] = []

        emit_log_event(
            LogLevel.DEBUG,
            "🏗️ MIXIN_INIT: Initializing MixinEventListener",
            {
                "mixin_class": self.__class__.__name__,
                "has_event_bus_attr": hasattr(self, "event_bus"),
                "event_bus_available": hasattr(self, "event_bus")
                and getattr(self, "event_bus", None) is not None,
            },
        )

        # Auto-start listener if event bus is available after full initialization
        # This is deferred to allow the concrete class to finish initialization
        if hasattr(self, "event_bus") and self.event_bus:
            emit_log_event(
                LogLevel.INFO,
                "⏰ MIXIN_INIT: Scheduling auto-start of event listener",
                {
                    "node_class": self.__class__.__name__,
                    "event_bus_type": type(self.event_bus).__name__,
                    "delay_seconds": 0.1,
                },
            )
            # Use a timer to start after init completes
            timer = threading.Timer(0.1, self.start_event_listener)
            timer.daemon = True
            timer.start()
        else:
            emit_log_event(
                LogLevel.DEBUG,
                "⏭️ MIXIN_INIT: No event bus available, skipping auto-start",
                {
                    "node_class": self.__class__.__name__,
                    "has_event_bus_attr": hasattr(self, "event_bus"),
                },
            )

    def get_node_name(self) -> str:
        """Get the node name from the implementing class."""
        if hasattr(self, "node_name"):
            node_name: str = self.node_name
            return node_name
        # Fallback: derive from class name
        class_name = self.__class__.__name__
        # Convert CamelCase to snake_case
        return re.sub(r"(?<!^)(?=[A-Z])", "_", class_name).lower()

    @property
    def event_bus(self) -> ProtocolEventBusListener | None:
        """Get event bus instance from implementing class."""
        return getattr(self, "_event_bus", None)

    @event_bus.setter
    def event_bus(self, value: ProtocolEventBusListener | None) -> None:
        """Set event bus instance."""
        self._event_bus = value

    def process(self, input_state: InputStateT) -> OutputStateT:
        """Process method that should be implemented by the tool."""
        msg = "Tool must implement process method"
        raise ModelOnexError(msg, EnumCoreErrorCode.METHOD_NOT_IMPLEMENTED)

    def get_event_patterns(self) -> list[str]:
        """
        Get event patterns this tool should listen for.

        By default, derives from contract or node name.
        Override this method to customize event patterns.

        Returns:
            List of event patterns to subscribe to
        """
        # First try to read event_subscriptions from contract YAML
        if hasattr(self, "contract_path"):
            try:
                contract_path = Path(self.contract_path)
                if contract_path.exists():
                    with open(contract_path) as f:
                        # Load and validate YAML using Pydantic model
                        content = f.read()
                        yaml_model = load_and_validate_yaml_model(content)
                        contract = yaml_model.model_dump()

                    event_subscriptions = contract.get("event_subscriptions", [])
                    if event_subscriptions:
                        # ModelEventSubscription uses 'event_pattern' field
                        event_patterns = [
                            sub.get("event_pattern")
                            for sub in event_subscriptions
                            if sub.get("event_pattern")
                        ]
                        if event_patterns:
                            emit_log_event(
                                LogLevel.INFO,
                                "📋 EVENT_PATTERNS: Found event_subscriptions in contract",
                                {
                                    "node_name": self.get_node_name(),
                                    "event_patterns": event_patterns,
                                    "subscription_count": len(event_patterns),
                                },
                            )
                            return event_patterns

                    # If no event_subscriptions, try legacy pattern derivation
                    emit_log_event(
                        LogLevel.DEBUG,
                        "📋 EVENT_PATTERNS: No event_subscriptions in contract, using legacy patterns",
                        {"node_name": self.get_node_name()},
                    )

                    # Extract domain from path (e.g., "generation" from tools/generation/...)
                    parts = contract_path.parts
                    if "tools" in parts:
                        tool_idx = parts.index("tools")
                        if tool_idx + 1 < len(parts):
                            domain = parts[tool_idx + 1]

                            # Map node name to event pattern
                            # e.g., tool_contract_validator -> contract.validate
                            node_type = (
                                self.get_node_name()
                                .replace("tool_", "")
                                .replace("_", ".")
                            )

                            # Special mappings for known tools
                            event_mappings = {
                                "contract.validator": "contract.validate",
                                "ast.generator": "ast.generate",
                                "ast.renderer": "ast.render",
                                "scenario.generator": "scenario.generate",
                            }

                            event_type = event_mappings.get(node_type, node_type)
                            return [f"{domain}.{event_type}"]
            except (ValidationError, ValueError) as e:
                # FAIL-FAST: Re-raise validation errors immediately to crash the service
                emit_log_event(
                    LogLevel.ERROR,
                    f"💥 FAIL-FAST: Contract validation failed: {e}",
                    {"node_name": self.get_node_name()},
                )
                raise  # Re-raise to crash the service
            except (AttributeError, KeyError, OSError, RuntimeError) as e:
                emit_log_event(
                    LogLevel.WARNING,
                    f"Failed to read event patterns from contract: {e}",
                    {"node_name": self.get_node_name()},
                )
            except (
                Exception
            ) as e:  # fallback-ok: YAML parsing errors should not crash event listener
                emit_log_event(
                    LogLevel.WARNING,
                    f"Unexpected error reading event patterns from contract: {e}",
                    {"node_name": self.get_node_name()},
                )

        # Fallback: use node name
        return [f"*.{self.get_node_name()}"]

    def get_completion_event_type(self, input_event_type: str) -> str:
        """
        Get completion event type for a given input event.

        Args:
            input_event_type: The input event type (e.g., "generation.contract.validate")

        Returns:
            Completion event type (e.g., "generation.validation.complete")
        """
        # Map input events to completion events
        completion_mappings = {
            "contract.validate": "validation.complete",
            "ast.generate": "ast_batch.generated",
            "ast.render": "files.rendered",
            "scenario.generate": "scenarios.generated",
        }

        # Extract event suffix (e.g., "contract.validate" from "generation.contract.validate")
        parts = input_event_type.split(".")
        if len(parts) >= 2:
            event_suffix = ".".join(parts[-2:])
            if event_suffix in completion_mappings:
                domain = ".".join(parts[:-2])
                return f"{domain}.{completion_mappings[event_suffix]}"

        # Default: append .complete
        return f"{input_event_type}.complete"

    def start_event_listener(self) -> None:
        """Start listening for events in a background thread if event bus available."""
        emit_log_event(
            LogLevel.INFO,
            "🔄 EVENT_LISTENER_START: Starting event listener",
            {
                "node_name": self.get_node_name(),
                "event_bus_available": bool(self.event_bus),
                "event_bus_type": (
                    type(self.event_bus).__name__ if self.event_bus else None
                ),
            },
        )

        if not self.event_bus:
            emit_log_event(
                LogLevel.WARNING,
                "❌ EVENT_LISTENER_START: No event bus available, running in CLI-only mode",
                {"node_name": self.get_node_name()},
            )
            return

        if self._event_listener_thread and self._event_listener_thread.is_alive():
            emit_log_event(
                LogLevel.WARNING,
                "⚠️ EVENT_LISTENER_START: Event listener already running",
                {
                    "node_name": self.get_node_name(),
                    "existing_thread": self._event_listener_thread.name,
                },
            )
            return

        self._stop_event.clear()
        self._event_listener_thread = threading.Thread(
            target=self._event_listener_loop,
            name=f"{self.get_node_name()}_event_listener",
        )
        self._event_listener_thread.daemon = True
        self._event_listener_thread.start()

        emit_log_event(
            LogLevel.INFO,
            "✅ EVENT_LISTENER_START: Event listener started successfully",
            {
                "node_name": self.get_node_name(),
                "thread_name": self._event_listener_thread.name,
                "thread_alive": self._event_listener_thread.is_alive(),
                "patterns_to_subscribe": self.get_event_patterns(),
            },
        )

    def stop_event_listener(self) -> None:
        """Stop the event listener thread."""
        if self._event_listener_thread and self._event_listener_thread.is_alive():
            emit_log_event(
                LogLevel.INFO,
                "Stopping event listener",
                {"node_name": self.get_node_name()},
            )

            self._stop_event.set()

            # Unsubscribe from all events
            for pattern, subscription in self._event_subscriptions:
                try:
                    if self.event_bus is not None:
                        self.event_bus.unsubscribe(subscription)
                except (AttributeError, KeyError, RuntimeError, ValueError) as e:
                    emit_log_event(
                        LogLevel.WARNING,
                        f"Failed to unsubscribe from {pattern}: {e}",
                        {"node_name": self.get_node_name()},
                    )

            self._event_subscriptions.clear()

            # Wait for thread to finish
            self._event_listener_thread.join(timeout=THREAD_JOIN_TIMEOUT_SECONDS)

            emit_log_event(
                LogLevel.INFO,
                "Event listener stopped",
                {"node_name": self.get_node_name()},
            )

    def _event_listener_loop(self) -> None:
        """Main event listener loop running in background thread."""
        emit_log_event(
            LogLevel.INFO,
            "🚀 EVENT_LISTENER_LOOP: Starting main event listener loop",
            {"node_name": self.get_node_name()},
        )

        try:
            # Get event patterns to subscribe to
            patterns = self.get_event_patterns()

            emit_log_event(
                LogLevel.INFO,
                "📋 EVENT_LISTENER_LOOP: Subscribing to event patterns",
                {
                    "node_name": self.get_node_name(),
                    "patterns": patterns,
                    "pattern_count": len(patterns),
                },
            )

            # Subscribe to each pattern
            for i, pattern in enumerate(patterns):
                emit_log_event(
                    LogLevel.DEBUG,
                    f"🔗 EVENT_LISTENER_LOOP: Subscribing to pattern {i + 1}/{len(patterns)}",
                    {
                        "node_name": self.get_node_name(),
                        "pattern": pattern,
                        "subscription_index": i,
                    },
                )

                handler = self._create_event_handler(pattern)
                emit_log_event(
                    LogLevel.INFO,
                    f"🔗 EVENT_LISTENER_LOOP: Creating handler for pattern {pattern}",
                    {
                        "node_name": self.get_node_name(),
                        "pattern": pattern,
                        "handler_function": (
                            handler.__name__
                            if hasattr(handler, "__name__")
                            else str(handler)
                        ),
                    },
                )

                if self.event_bus is not None:
                    # Duck-typed event bus interface
                    subscription = self.event_bus.subscribe(handler, event_type=pattern)
                    self._event_subscriptions.append((pattern, subscription))

                emit_log_event(
                    LogLevel.INFO,
                    f"✅ EVENT_LISTENER_LOOP: Successfully subscribed to pattern {i + 1}/{len(patterns)}",
                    {
                        "node_name": self.get_node_name(),
                        "pattern": pattern,
                        "total_subscriptions": len(self._event_subscriptions),
                        "event_bus_type": type(self.event_bus).__name__,
                    },
                )

            emit_log_event(
                LogLevel.INFO,
                "🎯 EVENT_LISTENER_LOOP: All subscriptions complete, starting event wait loop",
                {
                    "node_name": self.get_node_name(),
                    "total_subscriptions": len(self._event_subscriptions),
                    "subscribed_patterns": self._event_subscriptions,
                },
            )

            # Keep thread alive
            loop_count = 0
            while not self._stop_event.is_set():
                loop_count += 1
                if loop_count % 60 == 0:  # Log every minute
                    emit_log_event(
                        LogLevel.DEBUG,
                        "💓 EVENT_LISTENER_LOOP: Heartbeat - still listening for events",
                        {
                            "node_name": self.get_node_name(),
                            "loop_count": loop_count,
                            "active_subscriptions": len(self._event_subscriptions),
                        },
                    )
                time.sleep(1)

            emit_log_event(
                LogLevel.INFO,
                "🛑 EVENT_LISTENER_LOOP: Stop event received, ending event listener loop",
                {"node_name": self.get_node_name(), "total_loops": loop_count},
            )

        except Exception as e:
            # boundary-ok: event listener loop must log errors but not crash; KeyboardInterrupt/SystemExit propagate
            emit_log_event(
                LogLevel.ERROR,
                f"❌ EVENT_LISTENER_LOOP: Critical error in event listener: {e}",
                {
                    "node_name": self.get_node_name(),
                    "error_type": type(e).__name__,
                    "error_details": str(e),
                },
            )

    def _create_event_handler(self, pattern: str) -> Callable[[object], None]:
        """Create an event handler for a specific pattern."""
        emit_log_event(
            LogLevel.DEBUG,
            "🎯 CREATE_EVENT_HANDLER: Creating event handler for pattern",
            {"node_name": self.get_node_name(), "pattern": pattern},
        )

        def handler(envelope: object) -> None:
            """Handle incoming event envelope."""
            # Handle both envelope and direct event for current standards
            if hasattr(envelope, "payload"):
                # This is a ModelEventEnvelope
                event = envelope.payload
                emit_log_event(
                    LogLevel.INFO,
                    "📨 EVENT_RECEIVED: Received event envelope for processing",
                    {
                        "node_name": self.get_node_name(),
                        "envelope_id": getattr(envelope, "envelope_id", "unknown"),
                        "event_type": getattr(event, "event_type", "unknown"),
                        "event_id": getattr(event, "event_id", "unknown"),
                        "correlation_id": getattr(event, "correlation_id", "unknown"),
                        "pattern_matched": pattern,
                        "event_source": getattr(event, "node_id", "unknown"),
                        "envelope_type": type(envelope).__name__,
                        "event_data_type": type(event).__name__,
                    },
                )
            else:
                # Direct event (legacy compatibility)
                event = envelope
                emit_log_event(
                    LogLevel.INFO,
                    "📨 EVENT_RECEIVED: Received direct event for processing",
                    {
                        "node_name": self.get_node_name(),
                        "event_type": getattr(event, "event_type", "unknown"),
                        "event_id": getattr(event, "event_id", "unknown"),
                        "correlation_id": getattr(event, "correlation_id", "unknown"),
                        "pattern_matched": pattern,
                        "event_source": getattr(event, "node_id", "unknown"),
                        "event_data_type": type(event).__name__,
                    },
                )

            # Check for specific event handler methods (e.g., handle_ast_batch_event)
            event_type = getattr(event, "event_type", pattern)
            specific_handler_name = (
                f"handle_{event_type.replace('.', '_').replace('-', '_')}_event"
            )

            if hasattr(self, specific_handler_name):
                emit_log_event(
                    LogLevel.INFO,
                    f"🎯 EVENT_ROUTING: Found specific handler {specific_handler_name}",
                    {
                        "node_name": self.get_node_name(),
                        "event_type": event_type,
                        "handler_method": specific_handler_name,
                    },
                )
                try:
                    specific_handler = getattr(self, specific_handler_name)
                    # Pass the original envelope if it was an envelope, otherwise the event
                    handler_param = envelope if hasattr(envelope, "payload") else event
                    specific_handler(handler_param)
                    emit_log_event(
                        LogLevel.INFO,
                        f"✅ EVENT_ROUTING: Successfully processed via {specific_handler_name}",
                        {"node_name": self.get_node_name(), "event_type": event_type},
                    )
                    return
                except Exception as e:
                    # fallback-ok: specific handler failure falls through to generic processing
                    emit_log_event(
                        LogLevel.ERROR,
                        f"❌ EVENT_ROUTING: Specific handler {specific_handler_name} failed: {e}",
                        {"node_name": self.get_node_name(), "event_type": event_type},
                    )
                    # Fall through to generic processing

            emit_log_event(
                LogLevel.DEBUG,
                f"🔄 EVENT_ROUTING: Using generic processing for {event_type}",
                {"node_name": self.get_node_name(), "event_type": event_type},
            )

            try:
                # Convert event to input state
                emit_log_event(
                    LogLevel.DEBUG,
                    "🔄 EVENT_PROCESSING: Converting event to input state",
                    {
                        "node_name": self.get_node_name(),
                        "event_type": event.event_type,
                        "event_id": event.event_id,
                    },
                )

                input_state = self._event_to_input_state(event)

                emit_log_event(
                    LogLevel.DEBUG,
                    "✅ EVENT_PROCESSING: Successfully converted event to input state",
                    {
                        "node_name": self.get_node_name(),
                        "event_id": event.event_id,
                        "input_state_type": type(input_state).__name__,
                    },
                )

                # Process using tool's process method
                emit_log_event(
                    LogLevel.INFO,
                    "⚙️ EVENT_PROCESSING: Starting tool processing",
                    {
                        "node_name": self.get_node_name(),
                        "event_id": event.event_id,
                        "input_state_type": type(input_state).__name__,
                    },
                )

                output_state = self.process(input_state)

                emit_log_event(
                    LogLevel.INFO,
                    "✅ EVENT_PROCESSING: Tool processing completed successfully",
                    {
                        "node_name": self.get_node_name(),
                        "event_id": event.event_id,
                        "output_state_type": type(output_state).__name__,
                    },
                )

                # Publish completion event
                emit_log_event(
                    LogLevel.DEBUG,
                    "📤 EVENT_PUBLISHING: Publishing completion event",
                    {
                        "node_name": self.get_node_name(),
                        "event_id": event.event_id,
                        "correlation_id": event.correlation_id,
                    },
                )

                self._publish_completion_event(event, output_state)

                emit_log_event(
                    LogLevel.INFO,
                    "🎉 EVENT_COMPLETE: Event processing and publishing completed",
                    {
                        "node_name": self.get_node_name(),
                        "event_id": event.event_id,
                        "correlation_id": event.correlation_id,
                    },
                )

            except Exception as e:
                # boundary-ok: event processing errors emit error event instead of crashing
                emit_log_event(
                    LogLevel.ERROR,
                    "❌ EVENT_PROCESSING: Failed to process event",
                    {
                        "node_name": self.get_node_name(),
                        "event_type": event.event_type,
                        "event_id": event.event_id,
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                    },
                )

                # Publish error completion event
                self._publish_error_event(event, str(e))

        return handler

    def _event_to_input_state(self, event: ModelOnexEvent) -> InputStateT:
        """
        Convert event to tool's input state.

        Override this method to customize event to input state conversion.

        Args:
            event: Incoming ONEX event

        Returns:
            Input state for tool's process method
        """
        emit_log_event(
            LogLevel.DEBUG,
            "🔍 EVENT_TO_INPUT_STATE: Starting event data conversion",
            {
                "node_name": self.get_node_name(),
                "event_type": event.event_type,
                "event_id": event.event_id,
                "event_data_type": type(event.data).__name__,
            },
        )

        # Get input state class
        input_state_class = self._get_input_state_class()

        emit_log_event(
            LogLevel.DEBUG,
            "🏗️ EVENT_TO_INPUT_STATE: Retrieved input state class",
            {
                "node_name": self.get_node_name(),
                "input_state_class": (
                    input_state_class.__name__ if input_state_class else None
                ),
                "class_found": bool(input_state_class),
            },
        )

        # Extract data from event
        event_data = event.data
        emit_log_event(
            LogLevel.DEBUG,
            "📋 EVENT_TO_INPUT_STATE: Extracting data from event",
            {
                "node_name": self.get_node_name(),
                "event_data_type": type(event_data).__name__,
                "has_payload": hasattr(event_data, "payload"),
            },
        )

        if (
            event_data is not None
            and hasattr(event_data, "payload")
            and event_data.payload is not None
            and hasattr(event_data.payload, "data")
        ):
            data = event_data.payload.data
            emit_log_event(
                LogLevel.DEBUG,
                "📦 EVENT_TO_INPUT_STATE: Using payload.data from event",
                {
                    "node_name": self.get_node_name(),
                    "data_type": type(data).__name__,
                    "data_preview": str(data)[:200] if data else None,
                },
            )
        else:
            data = event_data
            emit_log_event(
                LogLevel.DEBUG,
                "📦 EVENT_TO_INPUT_STATE: Using direct event data",
                {
                    "node_name": self.get_node_name(),
                    "data_type": type(data).__name__,
                    "data_preview": str(data)[:200] if data else None,
                },
            )

        # Create input state instance
        if input_state_class:
            try:
                emit_log_event(
                    LogLevel.DEBUG,
                    "🏗️ EVENT_TO_INPUT_STATE: Creating input state instance",
                    {
                        "node_name": self.get_node_name(),
                        "target_class": input_state_class.__name__,
                        "data_is_dict": isinstance(data, dict),
                    },
                )

                # Convert event data to input state
                if isinstance(data, dict):
                    result = input_state_class(**data)
                    emit_log_event(
                        LogLevel.DEBUG,
                        "✅ EVENT_TO_INPUT_STATE: Created input state from dict",
                        {
                            "node_name": self.get_node_name(),
                            "result_type": type(result).__name__,
                        },
                    )
                    return cast("InputStateT", result)
                # Try to extract dict from model
                if data is not None and hasattr(data, "model_dump"):
                    dict_data = data.model_dump()
                    result = input_state_class(**dict_data)
                    emit_log_event(
                        LogLevel.DEBUG,
                        "✅ EVENT_TO_INPUT_STATE: Created input state from model_dump",
                        {"node_name": self.get_node_name()},
                    )
                    return cast("InputStateT", result)
                result = input_state_class(data=data)
                emit_log_event(
                    LogLevel.DEBUG,
                    "✅ EVENT_TO_INPUT_STATE: Created input state with data wrapper",
                    {"node_name": self.get_node_name()},
                )
                return cast("InputStateT", result)
            except PYDANTIC_MODEL_ERRORS as e:
                emit_log_event(
                    LogLevel.ERROR,
                    "❌ EVENT_TO_INPUT_STATE: Failed to create input state from event",
                    {
                        "node_name": self.get_node_name(),
                        "error_type": type(e).__name__,
                        "error_details": str(e),
                        "data_type": type(data).__name__,
                        "target_class": input_state_class.__name__,
                    },
                )
                msg = f"Failed to convert event data to input state: {e}"
                raise ModelOnexError(msg, EnumCoreErrorCode.VALIDATION_ERROR) from e
        else:
            # No input state class found - this is a critical error
            emit_log_event(
                LogLevel.ERROR,
                "❌ EVENT_TO_INPUT_STATE: No input state class found",
                {"node_name": self.get_node_name()},
            )
            msg = (
                f"Could not find input state class for {self.get_node_name()}. "
                f"Event listener requires proper type conversion."
            )
            raise ModelOnexError(
                msg,
                EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH,
            )

    def _get_input_state_class(self) -> type | None:
        """Get the input state class for this tool."""
        # Try to find input state class from type hints
        if hasattr(self.process, "__annotations__"):
            annotations = self.process.__annotations__
            if "input_state" in annotations:
                state_cls: type | None = annotations["input_state"]
                return state_cls

        # Try common patterns
        module_name = self.__class__.__module__
        if ".tools." in module_name:
            # Try to import from models
            try:
                # Module path is like: omnibase.tools.generation.tool_contract_validator.v1_0_0.node
                # We need: omnibase.tools.generation.tool_contract_validator.v1_0_0.models.model_input_state
                base_module = module_name.rsplit(".", 1)[0]  # Remove .node
                models_module = f"{base_module}.models.model_input_state"

                emit_log_event(
                    LogLevel.DEBUG,
                    f"Looking for input state in: {models_module}",
                    {"node_name": self.get_node_name()},
                )

                import importlib

                # Security: validate module is within allowed namespaces
                allowed_prefixes = [
                    "omnibase_core.",
                    "omnibase_spi.",
                    "omnibase.",
                    # Add other trusted prefixes as needed
                ]
                if not any(
                    models_module.startswith(prefix) for prefix in allowed_prefixes
                ):
                    emit_log_event(
                        LogLevel.WARNING,
                        f"Skipping model import: module not in allowed namespace: {models_module}",
                        {"node_name": self.get_node_name()},
                    )
                    return None

                module = importlib.import_module(models_module)

                # Look for input state class
                for attr_name in dir(module):
                    if "InputState" in attr_name and attr_name.startswith("Model"):
                        emit_log_event(
                            LogLevel.DEBUG,
                            f"Found input state class: {attr_name}",
                            {"node_name": self.get_node_name()},
                        )
                        cls: type | None = getattr(module, attr_name)
                        return cls

            except (AttributeError, ImportError, ModuleNotFoundError, TypeError) as e:
                emit_log_event(
                    LogLevel.WARNING,
                    f"Failed to import input state module: {e}",
                    {"node_name": self.get_node_name(), "module": models_module},
                )

        return None

    def _publish_event(self, envelope: object) -> None:
        """
        Publish event, handling both sync and async event buses.

        This helper ensures async publish_async() calls are properly scheduled,
        preventing event loop hangs during pytest-asyncio cleanup.

        Args:
            envelope: Event envelope to publish
        """
        if self.event_bus is None:
            return

        # Call the async method
        result = self.event_bus.publish_async(envelope)

        # Check if it returned a coroutine
        if inspect.iscoroutine(result):
            try:
                # Get the running event loop
                loop = asyncio.get_running_loop()
                # Schedule the coroutine as a fire-and-forget task
                # Store reference to prevent garbage collection
                _task = loop.create_task(result)
            except RuntimeError:
                # No running event loop - skip async operation to prevent blocking
                # In test contexts or synchronous code, event_bus is likely a Mock
                # and calling asyncio.run() would block for 30+ seconds waiting
                # for Mock timeouts or coroutine completion.
                result.close()  # Close the coroutine to prevent ResourceWarning

    def _publish_completion_event(
        self,
        input_event: ModelOnexEvent,
        output_state: OutputStateT,
    ) -> None:
        """Publish completion event with results."""
        emit_log_event(
            LogLevel.INFO,
            "📤 PUBLISH_COMPLETION: Starting completion event publishing",
            {
                "node_name": self.get_node_name(),
                "input_event_type": input_event.event_type,
                "input_event_id": input_event.event_id,
                "correlation_id": input_event.correlation_id,
                "output_state_type": type(output_state).__name__,
            },
        )

        # Convert event_type to str (handles both str and ModelEventType)
        event_type_str = (
            str(input_event.event_type)
            if not isinstance(input_event.event_type, str)
            else input_event.event_type
        )
        completion_event_type = self.get_completion_event_type(event_type_str)

        emit_log_event(
            LogLevel.DEBUG,
            "🔄 PUBLISH_COMPLETION: Determined completion event type",
            {
                "node_name": self.get_node_name(),
                "input_event_type": input_event.event_type,
                "completion_event_type": completion_event_type,
            },
        )

        # Create completion event data
        completion_data = {
            "status": "success",
            "node_name": self.get_node_name(),
            "correlation_id": input_event.correlation_id,
            "input_event_id": input_event.event_id,
        }

        emit_log_event(
            LogLevel.DEBUG,
            "📋 PUBLISH_COMPLETION: Created base completion data",
            {
                "node_name": self.get_node_name(),
                "completion_data_keys": list(completion_data.keys()),
            },
        )

        # Add output state data
        if output_state:
            emit_log_event(
                LogLevel.DEBUG,
                "📦 PUBLISH_COMPLETION: Adding output state to completion data",
                {
                    "node_name": self.get_node_name(),
                    "output_state_type": type(output_state).__name__,
                    "has_model_dump": hasattr(output_state, "model_dump"),
                    "has_dict": hasattr(output_state, "dict"),
                },
            )

            if hasattr(output_state, "model_dump"):
                completion_data["result"] = output_state.model_dump()
                emit_log_event(
                    LogLevel.DEBUG,
                    "✅ PUBLISH_COMPLETION: Added output state via model_dump",
                    {"node_name": self.get_node_name()},
                )
            else:
                completion_data["result"] = str(output_state)
                emit_log_event(
                    LogLevel.DEBUG,
                    "✅ PUBLISH_COMPLETION: Added output state as string",
                    {"node_name": self.get_node_name()},
                )

        # Create completion event
        emit_log_event(
            LogLevel.DEBUG,
            "🏗️ PUBLISH_COMPLETION: Creating completion event object",
            {
                "node_name": self.get_node_name(),
                "completion_event_type": completion_event_type,
                "data_size": len(str(completion_data)),
            },
        )

        # Convert node name to UUID (try parse, fallback to uuid5)
        node_name = self.get_node_name()
        try:
            node_uuid = UUID(node_name)
        except (AttributeError, ValueError):
            # Generate deterministic UUID from node name
            node_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, node_name)

        completion_event = ModelOnexEvent(
            event_type=completion_event_type,
            node_id=node_uuid,
            correlation_id=input_event.correlation_id,
            data=completion_data,  # type: ignore[arg-type]  # Event data field accepts dict for completion protocol; validated at runtime
        )

        emit_log_event(
            LogLevel.DEBUG,
            "✅ PUBLISH_COMPLETION: Completion event object created",
            {
                "node_name": self.get_node_name(),
                "completion_event_id": completion_event.event_id,
                "completion_event_type": completion_event.event_type,
            },
        )

        # Wrap in envelope and publish
        emit_log_event(
            LogLevel.INFO,
            "🚀 PUBLISH_COMPLETION: Publishing completion event to event bus",
            {
                "node_name": self.get_node_name(),
                "completion_event_id": completion_event.event_id,
                "completion_event_type": completion_event_type,
                "event_bus_type": type(self.event_bus).__name__,
            },
        )

        # Create envelope
        envelope = ModelEventEnvelope.create_broadcast(
            payload=completion_event,
            source_node_id=node_uuid,
            correlation_id=input_event.correlation_id,
        )

        # Publish envelope
        if self.event_bus is not None:
            self._publish_event(envelope)

        emit_log_event(
            LogLevel.INFO,
            "🎉 PUBLISH_COMPLETION: Successfully published completion event",
            {
                "node_name": self.get_node_name(),
                "completion_event_type": completion_event_type,
                "completion_event_id": completion_event.event_id,
                "correlation_id": input_event.correlation_id,
                "input_event_id": input_event.event_id,
            },
        )

    def _publish_error_event(
        self, input_event: ModelOnexEvent, error_message: str
    ) -> None:
        """Publish error completion event."""
        # Convert event_type to str (handles both str and ModelEventType)
        event_type_str = (
            str(input_event.event_type)
            if not isinstance(input_event.event_type, str)
            else input_event.event_type
        )
        completion_event_type = self.get_completion_event_type(event_type_str)

        # Create error event data
        error_data = {
            "status": "error",
            "node_name": self.get_node_name(),
            "correlation_id": input_event.correlation_id,
            "input_event_id": input_event.event_id,
            "error": error_message,
        }

        # Convert node name to UUID (try parse, fallback to uuid5)
        node_name = self.get_node_name()
        try:
            node_uuid = UUID(node_name)
        except (AttributeError, ValueError):
            # Generate deterministic UUID from node name
            node_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, node_name)

        # Create error event
        error_event = ModelOnexEvent(
            event_type=completion_event_type,
            node_id=node_uuid,
            correlation_id=input_event.correlation_id,
            data=error_data,  # type: ignore[arg-type]  # Event data field accepts dict for error protocol; validated at runtime
        )

        # Wrap in envelope and publish
        envelope = ModelEventEnvelope.create_broadcast(
            payload=error_event,
            source_node_id=node_uuid,
            correlation_id=input_event.correlation_id,
        )

        if self.event_bus is not None:
            self._publish_event(envelope)

        emit_log_event(
            LogLevel.ERROR,
            f"Published error event: {completion_event_type}",
            {
                "node_name": self.get_node_name(),
                "correlation_id": input_event.correlation_id,
                "error": error_message,
            },
        )
