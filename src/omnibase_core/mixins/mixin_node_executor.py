import types
from collections.abc import Callable
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
    from omnibase_core.types.type_serializable_value import SerializedDict
    from omnibase_core.types.typed_dict_mixin_types import TypedDictNodeExecutorHealth

import asyncio
import contextlib
import signal
import time
from datetime import datetime
from pathlib import Path
from uuid import UUID

from omnibase_core.constants import TIMEOUT_DEFAULT_MS
from omnibase_core.constants.constants_event_types import TOOL_INVOCATION
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.logging_structured import emit_log_event_sync
from omnibase_core.mixins.mixin_event_driven_node import MixinEventDrivenNode
from omnibase_core.models.core.model_log_context import ModelLogContext
from omnibase_core.models.discovery.model_node_shutdown_event import (
    ModelNodeShutdownEvent,
)
from omnibase_core.models.discovery.model_tool_invocation_event import (
    ModelToolInvocationEvent,
)
from omnibase_core.models.discovery.model_tool_response_event import (
    ModelToolResponseEvent,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError

_COMPONENT_NAME = Path(__file__).stem


class MixinNodeExecutor(MixinEventDrivenNode):
    """
    Canonical mixin for persistent node executor capabilities.

    Enables nodes to run as persistent executors that:
    - Respond to TOOL_INVOCATION events
    - Convert events to input states and call node.run()
    - Emit TOOL_RESPONSE events with results
    - Provide health monitoring and graceful shutdown
    - Support asyncio event loop for concurrent operations
    """

    _node_id: UUID

    def __init__(self, **kwargs: object) -> None:
        """Initialize the executor mixin."""
        super().__init__(**kwargs)  # type: ignore[arg-type]  # Cooperative MRO super() call; kwargs passed to next class in chain
        self._executor_running = False
        self._executor_task: asyncio.Task[None] | None = None
        self._health_task: asyncio.Task[None] | None = None
        self._active_invocations: set[UUID] = set()
        self._total_invocations = 0
        self._successful_invocations = 0
        self._failed_invocations = 0
        self._start_time: float | None = None
        self._shutdown_requested = False
        self._shutdown_callbacks: list[Callable[[], None]] = []

    async def start_executor_mode(self) -> None:
        """
        Start the node in persistent executor mode.

        This method:
        1. Publishes introspection on startup
        2. Subscribes to TOOL_INVOCATION events
        3. Starts health monitoring
        4. Enters async event loop
        """
        if self._executor_running:
            self._log_warning("Executor already running, ignoring start request")
            return
        try:
            self._executor_running = True
            self._start_time = time.time()
            self._publish_introspection_event()
            await self._subscribe_to_tool_invocations()
            self._health_task = asyncio.create_task(self._health_monitor_loop())
            self._register_signal_handlers()
            self._log_info("Executor started successfully")
            await self._executor_event_loop()
        except Exception as e:  # fallback-ok: cleanup during executor startup
            # Uses Exception (not BaseException) to allow KeyboardInterrupt/SystemExit to propagate
            self._log_error(f"Failed to start executor: {e}")
            await self.stop_executor_mode()
            raise

    async def stop_executor_mode(self) -> None:
        """
        Stop the executor mode gracefully.

        This method:
        1. Emits NODE_SHUTDOWN event
        2. Cancels health monitoring
        3. Waits for active invocations to complete
        4. Cleanup resources
        """
        if not self._executor_running:
            return
        self._log_info("Stopping executor mode...")
        self._shutdown_requested = True
        try:
            await self._emit_shutdown_event()
            if self._health_task and (not self._health_task.done()):
                self._health_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._health_task
            await self._wait_for_active_invocations(timeout_ms=TIMEOUT_DEFAULT_MS)
            for callback in self._shutdown_callbacks:
                try:
                    callback()
                except (
                    Exception
                ) as e:  # fallback-ok: user callbacks must not crash shutdown
                    # Uses Exception (not BaseException) to allow KeyboardInterrupt/SystemExit to propagate
                    self._log_error(f"Shutdown callback failed: {e}")
            self.cleanup_event_handlers()
            self._executor_running = False
            self._log_info("Executor stopped successfully")
        except (
            Exception
        ) as e:  # fallback-ok: shutdown must complete even if cleanup fails
            # Uses Exception (not BaseException) to allow KeyboardInterrupt/SystemExit to propagate
            self._log_error(f"Error during executor shutdown: {e}")
            self._executor_running = False

    async def handle_tool_invocation(
        self, envelope: "ModelEventEnvelope[object]"
    ) -> None:
        """
        Handle a TOOL_INVOCATION event.

        This method:
        1. Validates the target is this node
        2. Converts event to input state
        3. Calls node.run() with proper context
        4. Emits TOOL_RESPONSE event with results

        Args:
            envelope: The event envelope containing the tool invocation event
        """
        # STRICT: Envelope must have payload attribute
        if not hasattr(envelope, "payload"):
            raise ModelOnexError(
                "Envelope missing required 'payload' attribute",
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
                context={"envelope_type": type(envelope).__name__},
            )

        extracted_event = envelope.payload
        if not isinstance(extracted_event, ModelToolInvocationEvent):
            self._log_warning(f"Unexpected event type: {type(extracted_event)}")
            return
        event: ModelToolInvocationEvent = extracted_event
        start_time = time.time()
        correlation_id = event.correlation_id
        self._active_invocations.add(correlation_id)
        self._total_invocations += 1
        try:
            if not self._is_target_node(event):
                self._log_warning(
                    f"Ignoring invocation for different target: {event.target_node_id}"
                )
                return
            self._log_info(
                f"Handling tool invocation: {event.tool_name}.{event.action} (correlation: {correlation_id})"
            )
            input_state = await self._convert_event_to_input_state(event)
            result = await self._execute_tool(input_state, event)
            execution_time_ms = int((time.time() - start_time) * 1000)
            response_event = ModelToolResponseEvent.create_success_response(
                correlation_id=correlation_id,
                source_node_id=self._node_id,
                source_node_name=self._extract_node_name(),
                tool_name=event.tool_name,
                action=event.action,
                result=self._serialize_result(result),
                execution_time_ms=execution_time_ms,
                target_node_id=(
                    str(event.requester_node_id)
                    if isinstance(event.requester_node_id, UUID)
                    else event.requester_node_id
                ),
                requester_id=event.requester_id,
                execution_priority=event.priority,
            )
            await self._emit_tool_response(response_event)
            self._successful_invocations += 1
            self._log_info(
                f"Tool invocation completed successfully in {execution_time_ms}ms"
            )
        except (ModelOnexError, RuntimeError, TypeError, ValueError) as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            response_event = ModelToolResponseEvent.create_error_response(
                correlation_id=correlation_id,
                source_node_id=self._node_id,
                source_node_name=self._extract_node_name(),
                tool_name=event.tool_name,
                action=event.action,
                error=str(e),
                error_code="TOOL_EXECUTION_ERROR",
                execution_time_ms=execution_time_ms,
                target_node_id=(
                    str(event.requester_node_id)
                    if isinstance(event.requester_node_id, UUID)
                    else event.requester_node_id
                ),
                requester_id=event.requester_id,
                execution_priority=event.priority,
            )
            await self._emit_tool_response(response_event)
            self._failed_invocations += 1
            self._log_error(f"Tool invocation failed: {e}")
        finally:
            self._active_invocations.discard(correlation_id)

    def get_executor_health(self) -> "TypedDictNodeExecutorHealth":
        """
        Get current executor health status.

        Returns:
            Typed dictionary containing health metrics and status
        """
        from omnibase_core.types.typed_dict_mixin_types import (
            TypedDictNodeExecutorHealth,
        )

        uptime_seconds = 0
        if self._start_time:
            uptime_seconds = int(time.time() - self._start_time)
        return TypedDictNodeExecutorHealth(
            status=(
                "healthy"
                if self._executor_running and (not self._shutdown_requested)
                else "unhealthy"
            ),
            uptime_seconds=uptime_seconds,
            active_invocations=len(self._active_invocations),
            total_invocations=self._total_invocations,
            successful_invocations=self._successful_invocations,
            failed_invocations=self._failed_invocations,
            success_rate=(
                self._successful_invocations / self._total_invocations
                if self._total_invocations > 0
                else 1.0
            ),
            node_id=str(getattr(self, "_node_id", "unknown")),
            node_name=self._extract_node_name(),
            shutdown_requested=self._shutdown_requested,
        )

    def add_shutdown_callback(self, callback: Callable[[], None]) -> None:
        """
        Add a callback to be called during shutdown.

        Args:
            callback: Function to call during shutdown
        """
        self._shutdown_callbacks.append(callback)

    async def _subscribe_to_tool_invocations(self) -> None:
        """Subscribe to TOOL_INVOCATION events."""
        event_bus = getattr(self, "event_bus", None)
        if not event_bus:
            msg = "Event bus not available for subscription"
            raise ModelOnexError(msg, EnumCoreErrorCode.SERVICE_UNAVAILABLE)
        event_bus.subscribe(self.handle_tool_invocation, TOOL_INVOCATION)
        self._log_info("Subscribed to TOOL_INVOCATION events")

    async def _executor_event_loop(self) -> None:
        """Main executor event loop."""
        try:
            while self._executor_running and (not self._shutdown_requested):
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            self._log_info("Executor event loop cancelled")
        except (OSError, RuntimeError, ValueError) as e:
            self._log_error(f"Executor event loop error: {e}")
            raise

    async def _health_monitor_loop(self) -> None:
        """Health monitoring loop."""
        try:
            while self._executor_running and (not self._shutdown_requested):
                health = self.get_executor_health()
                if self._total_invocations % 100 == 0 and self._total_invocations > 0:
                    self._log_info(
                        f"Health: {health['active_invocations']} active, {health['success_rate']:.2%} success rate"
                    )
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            self._log_info("Health monitor cancelled")
        except (OSError, RuntimeError, ValueError) as e:
            self._log_error(f"Health monitor error: {e}")

    def _is_target_node(self, event: ModelToolInvocationEvent) -> bool:
        """Check if this node is the target of the invocation."""
        return (
            event.target_node_id == self._node_id
            or event.target_node_name == self._extract_node_name()
            or event.target_node_id == f"{self._extract_node_name()}_service"
        )

    async def _convert_event_to_input_state(
        self, event: ModelToolInvocationEvent
    ) -> object:
        """
        Convert tool invocation event to node input state.

        This method attempts to create the appropriate input state model
        for the node based on the event parameters.
        """
        input_state_class = getattr(self, "_input_state_class", None)
        if not input_state_class:
            input_state_class = self._infer_input_state_class()
        if input_state_class:
            params_dict = (
                event.parameters.get_parameter_dict()
                if hasattr(event.parameters, "get_parameter_dict")
                else {}
            )
            state_data = {"action": event.action, **params_dict}
            return input_state_class(**state_data)
        from types import SimpleNamespace

        params_dict = (
            event.parameters.get_parameter_dict()
            if hasattr(event.parameters, "get_parameter_dict")
            else {}
        )
        return SimpleNamespace(action=event.action, **params_dict)

    def _infer_input_state_class(self) -> type | None:
        """Attempt to infer the input state class for this node."""
        for attr_name in dir(self):
            if "InputState" in attr_name:
                attr = getattr(self, attr_name, None)
                if isinstance(attr, type):
                    return attr
        return None

    async def _execute_tool(
        self, input_state: object, event: ModelToolInvocationEvent
    ) -> object:
        """Execute the tool via the node's run method."""
        # STRICT: Node must have run() method for executor to work
        if not hasattr(self, "run"):
            raise ModelOnexError(
                "Node does not have a 'run' method for tool execution",
                error_code=EnumCoreErrorCode.METHOD_NOT_IMPLEMENTED,
                context={
                    "node_type": type(self).__name__,
                    "tool_name": event.tool_name,
                    "action": event.action,
                },
            )

        run_method = self.run
        if asyncio.iscoroutinefunction(run_method):
            return await run_method(input_state)
        return await asyncio.get_running_loop().run_in_executor(
            None, run_method, input_state
        )

    def _serialize_result(self, result: object) -> "SerializedDict":
        """Serialize the execution result to a dictionary."""
        from omnibase_core.types.type_serializable_value import SerializedDict

        if hasattr(result, "model_dump"):
            serialized: SerializedDict = result.model_dump()
            return serialized
        if hasattr(result, "__dict__"):
            # Cast __dict__ to SerializedDict as we expect serializable values
            dict_result: SerializedDict = result.__dict__
            return dict_result
        if isinstance(result, dict):
            return result
        # Cast result to JsonType - _serialize_result handles conversion of execution
        # results which should be JSON-serializable by node contract
        from omnibase_core.types.type_json import JsonType

        return {"result": cast(JsonType, result)}

    async def _emit_tool_response(self, response_event: ModelToolResponseEvent) -> None:
        """Emit a tool response event."""
        from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope

        event_bus = getattr(self, "event_bus", None)
        if event_bus:
            envelope = ModelEventEnvelope.create_broadcast(
                payload=response_event,
                source_node_id=self._node_id,
                correlation_id=response_event.correlation_id,
            )
            await event_bus.publish(envelope)
        else:
            self._log_error("Cannot emit tool response - event bus not available")

    async def _emit_shutdown_event(self) -> None:
        """Emit a node shutdown event."""
        from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope

        try:
            shutdown_event = ModelNodeShutdownEvent.create_graceful_shutdown(
                node_id=self._node_id,
                node_name=self._extract_node_name(),
            )
            event_bus = getattr(self, "event_bus", None)
            if event_bus:
                envelope = ModelEventEnvelope.create_broadcast(
                    payload=shutdown_event,
                    source_node_id=self._node_id,
                    correlation_id=shutdown_event.correlation_id,
                )
                await event_bus.publish(envelope)
        except (ModelOnexError, RuntimeError, ValueError) as e:
            self._log_error(f"Failed to emit shutdown event: {e}")

    async def _wait_for_active_invocations(
        self, timeout_ms: int = TIMEOUT_DEFAULT_MS
    ) -> None:
        """Wait for active invocations to complete."""
        if not self._active_invocations:
            return
        self._log_info(
            f"Waiting for {len(self._active_invocations)} active invocations to complete..."
        )
        timeout_seconds = timeout_ms / 1000
        start_time = time.time()
        while self._active_invocations and time.time() - start_time < timeout_seconds:
            await asyncio.sleep(0.1)
        if self._active_invocations:
            self._log_warning(
                f"Timeout waiting for invocations, {len(self._active_invocations)} still active"
            )

    def _register_signal_handlers(self) -> None:
        """Register signal handlers for graceful shutdown."""
        try:

            def signal_handler(signum: int, _frame: types.FrameType | None) -> None:
                self._log_info(
                    f"Received signal {signum}, initiating graceful shutdown"
                )
                self._shutdown_requested = True

            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)
        except (OSError, RuntimeError, ValueError) as e:
            self._log_warning(f"Could not register signal handlers: {e}")

    def _log_info(self, message: str) -> None:
        """Log info message with context."""
        node_id_raw = getattr(
            self, "_node_id", UUID("00000000-0000-0000-0000-000000000000")
        )
        context = ModelLogContext(
            calling_module=_COMPONENT_NAME,
            calling_function="executor",
            calling_line=1,
            timestamp=datetime.now().isoformat(),
            node_id=UUID(node_id_raw) if isinstance(node_id_raw, str) else node_id_raw,
        )
        emit_log_event_sync(LogLevel.INFO, message, context=context)

    def _log_warning(self, message: str) -> None:
        """Log warning message with context."""
        node_id_raw = getattr(
            self, "_node_id", UUID("00000000-0000-0000-0000-000000000000")
        )
        context = ModelLogContext(
            calling_module=_COMPONENT_NAME,
            calling_function="executor",
            calling_line=1,
            timestamp=datetime.now().isoformat(),
            node_id=UUID(node_id_raw) if isinstance(node_id_raw, str) else node_id_raw,
        )
        emit_log_event_sync(LogLevel.WARNING, message, context=context)

    def _log_error(self, message: str) -> None:
        """Log error message with context."""
        node_id_raw = getattr(
            self, "_node_id", UUID("00000000-0000-0000-0000-000000000000")
        )
        context = ModelLogContext(
            calling_module=_COMPONENT_NAME,
            calling_function="executor",
            calling_line=1,
            timestamp=datetime.now().isoformat(),
            node_id=UUID(node_id_raw) if isinstance(node_id_raw, str) else node_id_raw,
        )
        emit_log_event_sync(LogLevel.ERROR, message, context=context)
