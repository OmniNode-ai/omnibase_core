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
import contextlib
import signal
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from omnibase_core.constants.event_types import TOOL_INVOCATION
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.structured import emit_log_event_sync
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

if TYPE_CHECKING:
    from uuid import UUID

from uuid import uuid4

# Component identifier for logging
_COMPONENT_NAME = Path(__file__).stem


class MixinNodeService:
    """
    Canonical mixin for persistent node service capabilities.

    Enables nodes to run as persistent services that:
    - Respond to TOOL_INVOCATION events
    - Convert events to input states and call node.run()
    - Emit TOOL_RESPONSE events with results
    - Provide health monitoring and graceful shutdown
    - Support asyncio event loop for concurrent operations
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

    def __init__(self, *args: Any, **kwargs: Any) -> None:
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

        try:
            # Emit shutdown event
            await self._emit_shutdown_event()

            # Cancel health monitoring
            if self._health_task and not self._health_task.done():
                self._health_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._health_task

            # Wait for active invocations to complete (with timeout)
            await self._wait_for_active_invocations(timeout_ms=30000)

            # Run shutdown callbacks
            for callback in self._shutdown_callbacks:
                try:
                    callback()
                except Exception as e:
                    self._log_error(f"Shutdown callback failed: {e}")

            # Cleanup event handlers if available
            if hasattr(self, "cleanup_event_handlers"):
                self.cleanup_event_handlers()

            self._service_running = False
            self._log_info("Service stopped successfully")

        except Exception as e:
            self._log_error(f"Error during service shutdown: {e}")
            self._service_running = False

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

        except Exception as e:
            # Create error response
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

        finally:
            # Remove from active invocations
            self._active_invocations.discard(correlation_id)

    def get_service_health(self) -> dict[str, Any]:
        """
        Get current service health status.

        Returns:
            Dictionary containing health metrics and status
        """
        uptime_seconds = 0
        if self._start_time:
            uptime_seconds = int(time.time() - self._start_time)

        return {
            "status": (
                "healthy"
                if self._service_running and not self._shutdown_requested
                else "unhealthy"
            ),
            "uptime_seconds": uptime_seconds,
            "active_invocations": len(self._active_invocations),
            "total_invocations": self._total_invocations,
            "successful_invocations": self._successful_invocations,
            "failed_invocations": self._failed_invocations,
            "success_rate": (
                self._successful_invocations / self._total_invocations
                if self._total_invocations > 0
                else 1.0
            ),
            "node_id": getattr(self, "_node_id", "unknown"),
            "node_name": self._extract_node_name(),
            "shutdown_requested": self._shutdown_requested,
        }

    def add_shutdown_callback(self, callback: Callable[[], None]) -> None:
        """
        Add a callback to be called during shutdown.

        Args:
            callback: Function to call during shutdown
        """
        self._shutdown_callbacks.append(callback)

    # Private methods

    async def _subscribe_to_tool_invocations(self) -> None:
        """Subscribe to TOOL_INVOCATION events."""
        # Try multiple strategies to get event bus (similar to MixinEventBus._get_event_bus)
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
            except Exception:
                pass

        # Raise error if no event bus found
        if not event_bus:
            raise ModelOnexError(
                message="Event bus not available for subscription",
                error_code=EnumCoreErrorCode.SERVICE_UNAVAILABLE,
            )

        # Subscribe to tool invocation events
        event_bus.subscribe(self.handle_tool_invocation, TOOL_INVOCATION)

        self._log_info("Subscribed to TOOL_INVOCATION events")

    async def _service_event_loop(self) -> None:
        """Main service event loop."""
        try:
            while self._service_running and not self._shutdown_requested:
                # Process any pending events (depending on event bus implementation)
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting

        except asyncio.CancelledError:
            self._log_info("Service event loop cancelled")
        except Exception as e:
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

                # Wait before next health check
                await asyncio.sleep(30)

            except asyncio.CancelledError:
                self._log_info("Health monitor cancelled")
                break  # Exit loop on cancellation
            except Exception as e:
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
    ) -> Any:
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
            params_dict: dict[str, Any] = (
                event.parameters.get_parameter_dict()
                if hasattr(event.parameters, "get_parameter_dict")
                else event.parameters  # type: ignore[assignment]
            )
            state_data = {"action": event.action, **params_dict}
            return input_state_class(**state_data)
        # Fallback to generic state object
        from types import SimpleNamespace

        params_dict = (
            event.parameters.get_parameter_dict()
            if hasattr(event.parameters, "get_parameter_dict")
            else event.parameters  # type: ignore[assignment]
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
        input_state: Any,
        event: ModelToolInvocationEvent,
    ) -> Any:
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
        return await asyncio.get_event_loop().run_in_executor(
            None,
            run_method,
            input_state,
        )

    def _serialize_result(self, result: Any) -> dict[str, Any]:
        """Serialize the execution result to a dictionary."""
        # None results are not allowed - raise validation error
        if result is None:
            raise ModelOnexError(
                message="Tool execution returned None - nodes must return a valid result",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        if hasattr(result, "model_dump"):
            # Pydantic v2 model - use mode='json' for JSON-serializable output
            serialized: dict[str, Any] = result.model_dump(mode="json")
            return serialized
        if hasattr(result, "dict"):
            # Pydantic v1 model (fallback)
            result_dict: dict[str, Any] = result.dict()
            return result_dict
        if hasattr(result, "__dict__"):
            # Regular object
            obj_dict: dict[str, Any] = result.__dict__
            return obj_dict
        if isinstance(result, dict):
            return result
        # Primitive or other types
        return {"result": result}

    async def _emit_tool_response(self, response_event: ModelToolResponseEvent) -> None:
        """Emit a tool response event."""
        # Try multiple strategies to get event bus (similar to _subscribe_to_tool_invocations)
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
            except Exception:
                pass

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

            # Try multiple strategies to get event bus
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
                except Exception:
                    pass

            if event_bus:
                await event_bus.publish(shutdown_event)

        except Exception as e:
            self._log_error(f"Failed to emit shutdown event: {e}")

    async def _wait_for_active_invocations(self, timeout_ms: int = 30000) -> None:
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

            def signal_handler(signum: int, frame: Any) -> None:
                self._log_info(
                    f"Received signal {signum}, initiating graceful shutdown",
                )
                self._shutdown_requested = True

            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)

        except Exception as e:
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
            # No introspection available, that's okay
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
