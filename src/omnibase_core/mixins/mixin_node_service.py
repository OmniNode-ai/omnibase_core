# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-01-05T16:00:00.000000'
# description: Canonical mixin for persistent node service capabilities
# entrypoint: python://mixin_node_service
# lifecycle: active
# meta_type: mixin
# metadata_version: 0.1.0
# name: mixin_node_service.py
# namespace: python://omnibase.mixin.mixin_node_service
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# version: 1.0.0
# === /OmniNode:Metadata ===

"""
Node Service Mixin.

Canonical mixin for persistent node service capabilities. Enables nodes to run
as persistent services that respond to TOOL_INVOCATION events, providing
tool-as-a-service functionality for MCP, GraphQL, and other integrations.
"""

import asyncio
import signal
import time
import types
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, cast
from uuid import UUID, uuid4

from omnibase_core.constants import TIMEOUT_DEFAULT_MS
from omnibase_core.constants.constants_event_types import TOOL_INVOCATION
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS
from omnibase_core.logging.logging_structured import emit_log_event_sync
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
from omnibase_core.types import TypedDictServiceHealth
from omnibase_core.types.type_json import JsonType

# Component identifier for logging
_COMPONENT_NAME = Path(__file__).stem

# Service lookup errors for container.get_service() calls.
# Uses centralized PYDANTIC_MODEL_ERRORS (AttributeError, TypeError, ValidationError, ValueError)
# plus RuntimeError for service availability issues.
# Defined at module level with explicit tuple concatenation to satisfy mypy
# (mypy cannot handle tuple unpacking in except clauses).
#
# RuntimeError covers: service not registered, container not initialized, circular
# dependencies, or other container-level service resolution failures.
_SERVICE_LOOKUP_ERRORS: tuple[type[Exception], ...] = PYDANTIC_MODEL_ERRORS + (
    RuntimeError,  # init-errors-ok: service not available or container issues
)

# Tool execution errors for handle_tool_invocation().
# Uses centralized PYDANTIC_MODEL_ERRORS plus additional exceptions specific to tool execution.
# Defined at module level with explicit tuple concatenation to satisfy mypy
# (mypy cannot handle tuple unpacking in except clauses).
#
# Additional exceptions beyond PYDANTIC_MODEL_ERRORS:
# - KeyError: state/parameter access errors (dict key lookup failures)
# - ModelOnexError: ONEX framework errors (structured domain errors)
# - OSError: I/O and connection errors (includes ConnectionError)
# - RuntimeError: execution environment errors (async context, resource limits)
# - TimeoutError: async operation timeouts (task cancellation due to timeout)
_TOOL_EXECUTION_ERRORS: tuple[type[Exception], ...] = PYDANTIC_MODEL_ERRORS + (
    KeyError,
    ModelOnexError,
    OSError,
    RuntimeError,
    TimeoutError,
)


class MixinNodeService:
    """
    Canonical mixin for persistent node service capabilities.

    Enables nodes to run as persistent services that:
    - Respond to TOOL_INVOCATION events
    - Convert events to input states and call node.run()
    - Emit TOOL_RESPONSE events with results
    - Provide health monitoring and graceful shutdown
    - Support asyncio event loop for concurrent operations

    Thread Safety:
        All service instances must run within the same asyncio event loop.
        The _shutdown_event (asyncio.Event) is only safe for coordination within
        a single event loop. For multi-threaded scenarios with separate event
        loops, use threading.Event instead.
    """

    # Type annotations for attributes set via object.__setattr__()
    _service_running: bool
    _service_task: asyncio.Task[None] | None
    _health_task: asyncio.Task[None] | None
    _active_invocations: set["UUID"]
    _total_invocations: int
    _successful_invocations: int
    _failed_invocations: int
    _start_time: float | None
    _shutdown_requested: bool
    _shutdown_callbacks: list[Callable[[], None]]
    _shutdown_event: asyncio.Event | None

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialize the service mixin."""
        # Pass all arguments through to super() for proper MRO
        super().__init__(*args, **kwargs)

        # Use object.__setattr__() to bypass Pydantic validation for internal state
        # Service state
        object.__setattr__(self, "_service_running", False)
        object.__setattr__(self, "_service_task", None)
        object.__setattr__(self, "_health_task", None)
        object.__setattr__(self, "_active_invocations", set())

        # Performance tracking
        object.__setattr__(self, "_total_invocations", 0)
        object.__setattr__(self, "_successful_invocations", 0)
        object.__setattr__(self, "_failed_invocations", 0)
        object.__setattr__(self, "_start_time", None)

        # Shutdown handling
        object.__setattr__(self, "_shutdown_requested", False)
        object.__setattr__(self, "_shutdown_callbacks", [])
        # Shutdown event for immediate task cancellation (created lazily in start_service_mode)
        object.__setattr__(self, "_shutdown_event", None)

    async def start_service_mode(self) -> None:
        """
        Start the node in persistent service mode.

        This method:
        1. Publishes introspection on startup
        2. Subscribes to TOOL_INVOCATION events
        3. Starts health monitoring
        4. Enters async event loop
        """
        if self._service_running:
            self._log_warning("Service already running, ignoring start request")
            return

        try:
            self._service_running = True
            self._start_time = time.time()

            # Create shutdown event for immediate task cancellation
            # This allows health monitor and service loops to wake up immediately
            # when shutdown is requested instead of waiting for sleep to complete
            self._shutdown_event = asyncio.Event()

            # Publish introspection for service discovery
            self._publish_introspection_event()

            # Subscribe to tool invocation events
            await self._subscribe_to_tool_invocations()

            # Start health monitoring
            self._health_task = asyncio.create_task(self._health_monitor_loop())

            # Register shutdown signal handlers
            self._register_signal_handlers()

            self._log_info("Service started successfully")

            # Main service event loop
            await self._service_event_loop()

        except asyncio.CancelledError:
            # CRITICAL: Re-raise CancelledError to honor task cancellation.
            # Cleanup is handled by stop_service_mode() which caller should invoke.
            raise
        # fallback-ok: service startup requires cleanup on any error
        except Exception as e:
            self._log_error(f"Failed to start service: {e}")
            await self.stop_service_mode()
            raise

    async def stop_service_mode(self) -> None:
        """
        Stop the service mode gracefully.

        This method:
        1. Emits NODE_SHUTDOWN event
        2. Cancels health monitoring
        3. Waits for active invocations to complete
        4. Cleanup resources
        """
        if not self._service_running:
            return

        self._log_info("Stopping service mode...")
        self._shutdown_requested = True

        # Signal shutdown event to wake up any sleeping tasks immediately
        # This allows health monitor loop to respond to cancellation without
        # waiting for the full sleep interval (30 seconds)
        if self._shutdown_event is not None:
            self._shutdown_event.set()

        try:
            # Emit shutdown event
            await self._emit_shutdown_event()

            # Cancel health monitoring with robust cleanup
            await self._cleanup_health_task()

            # Wait for active invocations to complete (with timeout)
            await self._wait_for_active_invocations(timeout_ms=TIMEOUT_DEFAULT_MS)

            # Run shutdown callbacks
            for callback in self._shutdown_callbacks:
                try:
                    callback()
                except Exception as e:
                    # fallback-ok: user callbacks must not crash shutdown
                    self._log_error(f"Shutdown callback failed: {e}")

            # Cleanup event handlers if available
            if hasattr(self, "cleanup_event_handlers"):
                self.cleanup_event_handlers()

            self._service_running = False
            self._log_info("Service stopped successfully")

        except asyncio.CancelledError:
            # CRITICAL: Re-raise CancelledError to honor task cancellation.
            # Set service as not running before propagating cancellation.
            self._service_running = False
            raise
        except Exception as e:
            # cleanup-resilience-ok: shutdown must complete even if cleanup fails
            self._log_error(f"Error during service shutdown: {e}")
            self._service_running = False

    async def aclose(self) -> None:
        """
        Async cleanup method for proper resource cleanup.

        This method ensures all async resources are properly cleaned up,
        especially the health monitor task. Can be called directly by tests
        or used as an async context manager exit.
        """
        # Signal shutdown event to wake up any sleeping tasks immediately
        if self._shutdown_event is not None:
            self._shutdown_event.set()

        # Cancel health monitoring task if it exists
        await self._cleanup_health_task()

        # Stop service if it's running
        if self._service_running:
            await self.stop_service_mode()

    async def handle_tool_invocation(self, event: ModelToolInvocationEvent) -> None:
        """
        Handle a TOOL_INVOCATION event.

        This method:
        1. Validates the target is this node
        2. Converts event to input state
        3. Calls node.run() with proper context
        4. Emits TOOL_RESPONSE event with results

        Args:
            event: The tool invocation event to handle
        """
        start_time = time.time()
        correlation_id = event.correlation_id

        # Track active invocation
        self._active_invocations.add(correlation_id)
        self._total_invocations += 1

        try:
            # Validate target
            if not self._is_target_node(event):
                self._log_warning(
                    f"Ignoring invocation for different target: {event.target_node_id}",
                )
                return

            self._log_info(
                f"Handling tool invocation: {event.tool_name}.{event.action} (correlation: {correlation_id})",
            )

            # Convert event to input state
            input_state = await self._convert_event_to_input_state(event)

            # Execute the tool via node.run()
            result = await self._execute_tool(input_state, event)

            # Create success response
            execution_time_ms = int((time.time() - start_time) * 1000)
            response_event = ModelToolResponseEvent.create_success_response(
                correlation_id=correlation_id,
                source_node_id=getattr(
                    self, "node_id", getattr(self, "_node_id", uuid4())
                ),
                source_node_name=self._extract_node_name(),
                tool_name=event.tool_name,
                action=event.action,
                result=self._serialize_result(result),
                execution_time_ms=execution_time_ms,
                target_node_id=event.requester_node_id,
                requester_id=event.requester_id,
                execution_priority=event.priority,
            )

            # Emit response
            await self._emit_tool_response(response_event)

            self._successful_invocations += 1
            self._log_info(
                f"Tool invocation completed successfully in {execution_time_ms}ms",
            )

        except _TOOL_EXECUTION_ERRORS as e:
            # boundary-ok: tool invocation boundary must return error response, not crash.
            # Uses centralized _TOOL_EXECUTION_ERRORS (see module-level definition).
            execution_time_ms = int((time.time() - start_time) * 1000)
            response_event = ModelToolResponseEvent.create_error_response(
                correlation_id=correlation_id,
                source_node_id=getattr(
                    self, "node_id", getattr(self, "_node_id", uuid4())
                ),
                source_node_name=self._extract_node_name(),
                tool_name=event.tool_name,
                action=event.action,
                error=str(e),
                error_code="TOOL_EXECUTION_ERROR",
                execution_time_ms=execution_time_ms,
                target_node_id=event.requester_node_id,
                requester_id=event.requester_id,
                execution_priority=event.priority,
            )

            await self._emit_tool_response(response_event)

            self._failed_invocations += 1
            self._log_error(f"Tool invocation failed: {e}")

        except asyncio.CancelledError:
            # CRITICAL: Re-raise CancelledError to honor task cancellation.
            # The finally block will still clean up active_invocations.
            raise

        # fallback-ok: service must emit error response for any failure
        # Fallback for truly unexpected exceptions not covered above.
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            response_event = ModelToolResponseEvent.create_error_response(
                correlation_id=correlation_id,
                source_node_id=getattr(
                    self, "node_id", getattr(self, "_node_id", uuid4())
                ),
                source_node_name=self._extract_node_name(),
                tool_name=event.tool_name,
                action=event.action,
                error=str(e),
                error_code="UNEXPECTED_ERROR",
                execution_time_ms=execution_time_ms,
                target_node_id=event.requester_node_id,
                requester_id=event.requester_id,
                execution_priority=event.priority,
            )

            await self._emit_tool_response(response_event)

            self._failed_invocations += 1
            self._log_error(f"Unexpected error during tool invocation: {e}")

        finally:
            # Remove from active invocations
            self._active_invocations.discard(correlation_id)

    def get_service_health(self) -> TypedDictServiceHealth:
        """
        Get current service health status.

        Returns:
            Dictionary containing health metrics and status
        """
        uptime_seconds = 0
        if self._start_time:
            uptime_seconds = int(time.time() - self._start_time)

        return TypedDictServiceHealth(
            status=(
                "healthy"
                if self._service_running and not self._shutdown_requested
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
            node_id=getattr(self, "_node_id", "unknown"),
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

    # Private methods

    def _try_get_event_bus_from_container(self) -> Any:
        """
        Try to get event bus from container using multiple strategies.

        This helper consolidates the event bus lookup logic used across
        subscription, response emission, and shutdown event methods.

        Returns:
            The event bus object if found, None otherwise. Return type is Any
            to allow duck-typed access to subscribe/publish methods.
        """
        event_bus = None

        # Strategy 1: Try _get_event_bus() method if available (from MixinEventBus)
        if hasattr(self, "_get_event_bus"):
            event_bus = self._get_event_bus()

        # Strategy 2: Try direct event_bus attribute
        if not event_bus:
            event_bus = getattr(self, "event_bus", None)

        # Strategy 3: Try container.get_service()
        if not event_bus and hasattr(self, "container"):
            try:
                container = self.container
                if hasattr(container, "get_service"):
                    event_bus = container.get_service("event_bus")
            except _SERVICE_LOOKUP_ERRORS:
                # fallback-ok: service lookup failure returns None
                pass

        return event_bus

    async def _subscribe_to_tool_invocations(self) -> None:
        """Subscribe to TOOL_INVOCATION events."""
        event_bus = self._try_get_event_bus_from_container()

        # Raise error if no event bus found
        if not event_bus:
            raise ModelOnexError(
                message="Event bus not available for subscription",
                error_code=EnumCoreErrorCode.SERVICE_UNAVAILABLE,
                node_type=type(self).__name__,
                subscription_topic=TOOL_INVOCATION,
            )

        # Subscribe to tool invocation events
        event_bus.subscribe(self.handle_tool_invocation, TOOL_INVOCATION)

        self._log_info("Subscribed to TOOL_INVOCATION events")

    async def _service_event_loop(self) -> None:
        """Main service event loop."""
        try:
            while self._service_running and not self._shutdown_requested:
                # Process any pending events (depending on event bus implementation)
                # Use shutdown event for interruptible sleep to allow immediate shutdown
                if self._shutdown_event is not None:
                    try:
                        await asyncio.wait_for(self._shutdown_event.wait(), timeout=0.1)
                        # If we get here, shutdown was signaled
                        break
                    except TimeoutError:
                        # Normal timeout - continue event loop
                        pass
                else:
                    await asyncio.sleep(0.1)  # Small delay to prevent busy waiting

        except asyncio.CancelledError:
            # CRITICAL: Do not log here - file handles may be closed during teardown
            # Re-raise immediately without any I/O operations
            raise
        except (OSError, RuntimeError, ValueError) as e:
            # boundary-ok: event loop must log and propagate non-fatal errors
            # OSError: I/O errors during event processing
            # RuntimeError: async context errors (e.g., loop closed)
            # ValueError: invalid state during event processing
            self._log_error(f"Service event loop error: {e}")
            raise

    async def _health_monitor_loop(self) -> None:
        """Health monitoring loop."""
        while self._service_running and not self._shutdown_requested:
            try:
                # Perform health checks
                health = self.get_service_health()

                # Log health status periodically
                if self._total_invocations % 100 == 0 and self._total_invocations > 0:
                    self._log_info(
                        f"Health: {health['active_invocations']} active, {health['success_rate']:.2%} success rate",
                    )

                # Wait before next health check, but allow immediate wakeup on shutdown
                # This prevents the "Task was destroyed but it is pending!" warning
                # by responding immediately to shutdown signals instead of sleeping
                if self._shutdown_event is not None:
                    try:
                        # Wait for shutdown event with timeout (health check interval)
                        await asyncio.wait_for(self._shutdown_event.wait(), timeout=30)
                        # If we get here, shutdown was signaled
                        break
                    except TimeoutError:
                        # Normal timeout - continue health monitoring
                        pass
                else:
                    # Fallback to simple sleep if no shutdown event (shouldn't happen)
                    await asyncio.sleep(30)

            except asyncio.CancelledError:
                # CRITICAL: Do not log here - file handles may be closed during teardown
                # Re-raise immediately without any I/O operations
                raise
            except (OSError, RuntimeError, ValueError) as e:
                # boundary-ok: health monitor must log errors and exit gracefully
                # OSError: I/O errors during health check
                # RuntimeError: async context errors (e.g., loop closed)
                # ValueError: invalid state during health monitoring
                self._log_error(f"Health monitor error: {e}")
                break  # Exit loop on exception

    def _is_target_node(self, event: ModelToolInvocationEvent) -> bool:
        """Check if this node is the target of the invocation."""
        node_id = getattr(self, "node_id", getattr(self, "_node_id", uuid4()))
        return (
            event.target_node_id == node_id
            or event.target_node_name == self._extract_node_name()
            or event.target_node_id == f"{self._extract_node_name()}_service"
        )

    async def _convert_event_to_input_state(
        self,
        event: ModelToolInvocationEvent,
    ) -> object:
        """
        Convert tool invocation event to node input state.

        This method attempts to create the appropriate input state model
        for the node based on the event parameters.
        """
        # This is a simplified implementation - in practice, you'd want to
        # inspect the node's input state model and create it properly

        # Try to get the input state class
        input_state_class = getattr(self, "_input_state_class", None)
        if not input_state_class:
            # Try to infer from method signatures or contracts
            input_state_class = self._infer_input_state_class()

        if input_state_class:
            # Create input state with action and parameters
            # Parameters may be dict or have get_parameter_dict method; runtime duck-typing
            params_dict: dict[str, object] = (
                event.parameters.get_parameter_dict()
                if hasattr(event.parameters, "get_parameter_dict")
                else event.parameters  # type: ignore[assignment]  # Duck-typed: parameters may be dict or model
            )
            state_data: dict[str, object] = {"action": event.action, **params_dict}
            return input_state_class(**state_data)
        # Fallback to generic state object
        from types import SimpleNamespace

        # Parameters may be dict or have get_parameter_dict method; runtime duck-typing
        params_dict = (
            event.parameters.get_parameter_dict()
            if hasattr(event.parameters, "get_parameter_dict")
            else event.parameters  # type: ignore[assignment]  # Duck-typed: parameters may be dict or model
        )
        return SimpleNamespace(action=event.action, **params_dict)

    def _infer_input_state_class(self) -> type | None:
        """Attempt to infer the input state class for this node."""
        # Look for common patterns in the node class
        for attr_name in dir(self):
            if "InputState" in attr_name:
                attr = getattr(self, attr_name, None)
                if isinstance(attr, type):
                    return attr
        return None

    async def _execute_tool(
        self,
        input_state: object,
        event: ModelToolInvocationEvent,
    ) -> object:
        """Execute the tool via the node's run method."""
        # STRICT: Node must have run() method for service to work
        if not hasattr(self, "run"):
            raise ModelOnexError(
                message="Node does not have a 'run' method for tool execution",
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
        # Run synchronous method in executor to avoid blocking
        return await asyncio.get_running_loop().run_in_executor(
            None,
            run_method,
            input_state,
        )

    def _serialize_result(self, result: object) -> dict[str, JsonType]:
        """Serialize the execution result to a dictionary."""
        # None results are not allowed - raise validation error
        if result is None:
            raise ModelOnexError(
                message="Tool execution returned None - nodes must return a valid result",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                node_type=type(self).__name__,
                node_name=self._extract_node_name(),
            )

        if hasattr(result, "model_dump"):
            # Pydantic v2 model - use mode='json' for JSON-serializable output
            serialized: dict[str, JsonType] = result.model_dump(mode="json")
            return serialized
        if hasattr(result, "__dict__"):
            # Regular object - cast to JsonType since __dict__ values should be JSON-serializable
            obj_dict: dict[str, JsonType] = cast(dict[str, JsonType], result.__dict__)
            return obj_dict
        if isinstance(result, dict):
            # Cast to JsonType since we expect JSON-serializable values
            return cast(dict[str, JsonType], result)
        # Primitive or other types
        return {"result": cast(JsonType, result)}

    async def _emit_tool_response(self, response_event: ModelToolResponseEvent) -> None:
        """Emit a tool response event."""
        event_bus = self._try_get_event_bus_from_container()

        # Emit event if bus available
        if event_bus:
            await event_bus.publish(response_event)
        else:
            self._log_error("Cannot emit tool response - event bus not available")

    async def _emit_shutdown_event(self) -> None:
        """Emit a node shutdown event."""
        try:
            shutdown_event = ModelNodeShutdownEvent.create_graceful_shutdown(
                node_id=getattr(self, "node_id", getattr(self, "_node_id", uuid4())),
                node_name=self._extract_node_name(),
            )

            event_bus = self._try_get_event_bus_from_container()

            if event_bus:
                await event_bus.publish(shutdown_event)

        except (ModelOnexError, RuntimeError, ValueError) as e:
            # cleanup-resilience-ok: shutdown event emission failure must not crash shutdown
            # ModelOnexError: ONEX framework errors during event creation/emission
            # RuntimeError: event bus or async context issues
            # ValueError: invalid event data
            self._log_error(f"Failed to emit shutdown event: {e}")

    async def _cleanup_health_task(self) -> None:
        """
        Cleanup the health monitor task.

        This method ensures the health monitor task is properly cancelled
        and awaited to prevent "Task was destroyed but it is pending!" warnings.

        Note: The task reference is preserved after cleanup so tests can verify
        cancellation status.
        """
        # Check if the health task attribute exists and has a task
        if not hasattr(self, "_health_task"):
            return

        health_task = self._health_task
        if health_task is None:
            return

        # Only cancel if not already done
        # Add try-except to handle edge cases where task is already being cancelled
        try:
            if not health_task.done():
                health_task.cancel()
        except RuntimeError:
            # cleanup-resilience-ok: task cancellation race condition or event loop closed
            # RuntimeError can occur if task is already being cancelled concurrently
            # or if the event loop has been closed during shutdown
            pass

        # Always await to ensure proper cleanup
        try:
            await health_task
        except asyncio.CancelledError:
            # Distinguish between expected cancellation (we cancelled the health_task)
            # vs external cancellation (someone cancelled _cleanup_health_task itself)
            if health_task.cancelled():
                # Expected - we initiated this cancellation, cleanup is complete
                self._log_info("Health task cleanup completed (task was cancelled)")
            else:
                # External cancellation - re-raise for proper propagation
                self._log_info("Cleanup interrupted by external cancellation")
                raise
        except Exception as e:  # fallback-ok: cleanup must complete even on error
            # Uses Exception (not BaseException) to allow KeyboardInterrupt/SystemExit to propagate
            self._log_error(f"Unexpected error during health task cleanup: {e}")

        # DO NOT set _health_task to None here - keep the reference
        # so tests can verify the task was cancelled

    async def _wait_for_active_invocations(
        self, timeout_ms: int = TIMEOUT_DEFAULT_MS
    ) -> None:
        """Wait for active invocations to complete."""
        if not self._active_invocations:
            return

        self._log_info(
            f"Waiting for {len(self._active_invocations)} active invocations to complete...",
        )

        timeout_seconds = timeout_ms / 1000
        start_time = time.time()

        while self._active_invocations and (time.time() - start_time) < timeout_seconds:
            await asyncio.sleep(0.1)

        if self._active_invocations:
            self._log_warning(
                f"Timeout waiting for invocations, {len(self._active_invocations)} still active",
            )

    def _register_signal_handlers(self) -> None:
        """Register signal handlers for graceful shutdown."""
        try:

            def signal_handler(signum: int, _frame: types.FrameType | None) -> None:
                self._log_info(
                    f"Received signal {signum}, initiating graceful shutdown",
                )
                self._shutdown_requested = True
                # Signal shutdown event to wake up any sleeping tasks immediately
                # Use call_soon_threadsafe since signal handlers run in main thread
                # but asyncio.Event.set() should be called from the event loop thread
                if self._shutdown_event is not None:
                    try:
                        loop = asyncio.get_running_loop()
                        loop.call_soon_threadsafe(self._shutdown_event.set)
                    except RuntimeError:
                        # No running loop - set directly (may be during shutdown)
                        self._shutdown_event.set()

            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)

        except (OSError, RuntimeError, ValueError) as e:
            # fallback-ok: signal handler registration is optional (may fail in threads)
            # OSError: signal registration not allowed (e.g., not main thread)
            # RuntimeError: event loop issues during handler setup
            # ValueError: invalid signal number
            self._log_warning(f"Could not register signal handlers: {e}")

    def _extract_node_name(self) -> str:
        """Extract node name from class name."""
        # Try common methods first
        if hasattr(self, "get_node_name"):
            node_name: str = self.get_node_name()
            return node_name
        # Fallback to class name
        return self.__class__.__name__

    def _publish_introspection_event(self) -> None:
        """Publish introspection event if available."""
        # Try to use existing introspection publisher from other mixins
        try:
            # Check if there's a method from another mixin in the MRO
            for cls in self.__class__.__mro__[1:]:  # Skip this class
                if (
                    hasattr(cls, "_publish_introspection_event")
                    and cls != MixinNodeService
                ):
                    method = cls._publish_introspection_event
                    if callable(method):
                        method(self)
                        break
        except (AttributeError, TypeError):
            # fallback-ok: introspection publishing is optional
            # AttributeError: mixin method not available in MRO
            # TypeError: method not callable or wrong signature
            pass

    def _log_info(self, message: str) -> None:
        """Log info message with context."""
        # Get node_id (could be node_id or _node_id depending on implementation)
        node_id = getattr(self, "node_id", getattr(self, "_node_id", uuid4()))
        context = ModelLogContext(
            calling_module=_COMPONENT_NAME,
            calling_function="service",
            calling_line=1,  # Required field
            timestamp=datetime.now().isoformat(),
            node_id=node_id,
        )
        emit_log_event_sync(LogLevel.INFO, message, context=context)

    def _log_warning(self, message: str) -> None:
        """Log warning message with context."""
        # Get node_id (could be node_id or _node_id depending on implementation)
        node_id = getattr(self, "node_id", getattr(self, "_node_id", uuid4()))
        context = ModelLogContext(
            calling_module=_COMPONENT_NAME,
            calling_function="service",
            calling_line=1,  # Required field
            timestamp=datetime.now().isoformat(),
            node_id=node_id,
        )
        emit_log_event_sync(LogLevel.WARNING, message, context=context)

    def _log_error(self, message: str) -> None:
        """Log error message with context."""
        # Get node_id (could be node_id or _node_id depending on implementation)
        node_id = getattr(self, "node_id", getattr(self, "_node_id", uuid4()))
        context = ModelLogContext(
            calling_module=_COMPONENT_NAME,
            calling_function="service",
            calling_line=1,  # Required field
            timestamp=datetime.now().isoformat(),
            node_id=node_id,
        )
        emit_log_event_sync(LogLevel.ERROR, message, context=context)
