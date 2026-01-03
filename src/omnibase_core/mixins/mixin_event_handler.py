from typing import TYPE_CHECKING
from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

if TYPE_CHECKING:
    from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
    from omnibase_core.models.mixins.model_node_introspection_data import (
        ModelNodeIntrospectionData,
    )

# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-07-04T02:30:00.000000'
# description: Event handling mixin for event-driven nodes
# entrypoint: python://mixin_event_handler
# lifecycle: active
# meta_type: mixin
# metadata_version: 0.1.0
# name: mixin_event_handler.py
# namespace: python://omnibase.mixin.mixin_event_handler
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# version: 1.0.0
# === /OmniNode:Metadata ===

"""
Event Handler Mixin.

This mixin handles:
- Setting up event handlers for introspection and discovery requests
- Handling incoming NODE_INTROSPECTION_REQUEST events
- Handling incoming NODE_DISCOVERY_REQUEST events
- Filtering and responding to requests
"""

import asyncio
import fnmatch
import inspect
from datetime import datetime
from pathlib import Path

# Import protocol to avoid circular dependencies
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.logging_structured import emit_log_event_sync
from omnibase_core.models.core.model_event_type import (
    create_event_type_from_registry,
    is_event_equal,
)
from omnibase_core.models.core.model_log_context import ModelLogContext
from omnibase_core.models.core.model_onex_event import OnexEvent

# Component identifier for logging
_COMPONENT_NAME = Path(__file__).stem

# Background tasks set to prevent garbage collection of fire-and-forget tasks
_background_tasks: set[asyncio.Task[None]] = set()


class MixinEventHandler:
    """
    Mixin for event handling capabilities.

    Provides methods to set up and handle incoming events for introspection
    and discovery requests. Uses getattr() for all host class attribute access.
    """

    def _setup_event_handlers(self) -> None:
        """Set up event handlers for this node. Supports both sync and async event buses."""
        event_bus = getattr(self, "event_bus", None)
        if not event_bus:
            return

        # Prefer async subscribe if available
        subscribe_async = getattr(event_bus, "subscribe_async", None)
        if subscribe_async and inspect.iscoroutinefunction(subscribe_async):
            # Schedule async subscription in the event loop
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    # Create background tasks and store references to prevent garbage collection
                    task1 = asyncio.create_task(
                        subscribe_async(self._handle_introspection_request),
                    )
                    task2 = asyncio.create_task(
                        subscribe_async(self._handle_node_discovery_request),
                    )
                    # Keep references to prevent premature cleanup
                    _background_tasks.add(task1)
                    _background_tasks.add(task2)
                    task1.add_done_callback(_background_tasks.discard)
                    task2.add_done_callback(_background_tasks.discard)
                else:
                    loop.run_until_complete(
                        subscribe_async(self._handle_introspection_request),
                    )
                    loop.run_until_complete(
                        subscribe_async(self._handle_node_discovery_request),
                    )
            except RuntimeError:
                # No event loop, fallback to sync
                event_bus.subscribe(self._handle_introspection_request)
                event_bus.subscribe(self._handle_node_discovery_request)
        else:
            # Only call subscribe if it is not a coroutine function
            event_bus.subscribe(self._handle_introspection_request)
            event_bus.subscribe(self._handle_node_discovery_request)

            node_id = getattr(self, "_node_id", None) or "<unset>"
            context = ModelLogContext(
                calling_module=_COMPONENT_NAME,
                calling_function="_setup_event_handlers",
                calling_line=67,
                timestamp=datetime.now().isoformat(),
                node_id=(
                    UUID(node_id)
                    if isinstance(node_id, str) and node_id != "<unset>"
                    else None
                ),
            )
            emit_log_event_sync(
                LogLevel.DEBUG,
                f"Event handlers set up for node {node_id}",
                context=context,
            )

    async def start_async_event_handlers(self) -> None:
        """Set up event handlers for async event buses. Must be called from an event loop."""
        event_bus = getattr(self, "event_bus", None)
        if not event_bus:
            return

        if inspect.iscoroutinefunction(getattr(event_bus, "subscribe", None)):
            await event_bus.subscribe(self._handle_introspection_request)
            await event_bus.subscribe(self._handle_node_discovery_request)
        else:
            self._setup_event_handlers()

    def _handle_introspection_request(
        self, envelope: "ModelEventEnvelope[OnexEvent] | OnexEvent"
    ) -> None:
        """
        Handle NODE_INTROSPECTION_REQUEST events.

        Responds with node capabilities when requested.

        Args:
            envelope: Event envelope containing the introspection request
        """
        # STRICT: Envelope must have payload attribute
        if not hasattr(envelope, "payload"):
            raise ModelOnexError(
                "Envelope missing required 'payload' attribute",
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
                context={"envelope_type": type(envelope).__name__},
            )

        # Extract event from envelope
        event = envelope.payload

        # Check if this event is an introspection request
        try:
            introspection_request_type = create_event_type_from_registry(
                "NODE_INTROSPECTION_REQUEST",
            )

            if not is_event_equal(event.event_type, introspection_request_type):
                return

        except (AttributeError, KeyError, RuntimeError, ValueError) as e:
            # Cannot create event type - raise error instead of silently skipping
            raise ModelOnexError(
                f"Failed to create introspection request event type: {e!s}",
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
            ) from e

        # Check if we should respond to this request
        if not self._should_respond_to_request(event):
            return

        try:
            # Get introspection data
            if hasattr(self, "_gather_introspection_data"):
                introspection_data = self._gather_introspection_data()
            else:
                # Fallback introspection data
                introspection_data = {
                    "node_name": self.__class__.__name__.lower(),
                    "actions": ["health_check"],
                    "protocols": ["event_bus"],
                    "metadata": {"description": "Event-driven ONEX node"},
                    "tags": ["event_driven"],
                }

            # Filter data based on request
            requested_types = (
                getattr(event.metadata, "requested_types", None)
                if event.metadata
                else None
            )
            if requested_types:
                introspection_data = self._filter_introspection_data(
                    introspection_data, requested_types
                )

            # Emit response event (simplified - would need full implementation)
            node_id = getattr(self, "_node_id", None) or "<unset>"
            context = ModelLogContext(
                calling_module=_COMPONENT_NAME,
                calling_function="_handle_introspection_request",
                calling_line=124,
                timestamp=datetime.now().isoformat(),
                node_id=(
                    UUID(node_id)
                    if isinstance(node_id, str) and node_id != "<unset>"
                    else None
                ),
            )
            emit_log_event_sync(
                LogLevel.DEBUG,
                f"Handled introspection request for node {node_id}",
                context=context,
            )

        except Exception as e:  # catch-all-ok: introspection request handling errors are logged but shouldn't crash
            node_id = getattr(self, "_node_id", None) or "<unset>"
            context = ModelLogContext(
                calling_module=_COMPONENT_NAME,
                calling_function="_handle_introspection_request",
                calling_line=137,
                timestamp=datetime.now().isoformat(),
                node_id=(
                    UUID(node_id)
                    if isinstance(node_id, str) and node_id != "<unset>"
                    else None
                ),
            )
            emit_log_event_sync(
                LogLevel.ERROR,
                f"Error handling introspection request: {e}",
                context=context,
            )

    def _handle_node_discovery_request(
        self, envelope: "ModelEventEnvelope[OnexEvent] | OnexEvent"
    ) -> None:
        """
        Handle NODE_DISCOVERY_REQUEST events.

        Responds with node information for discovery.

        Args:
            envelope: Event envelope containing the discovery request
        """
        # STRICT: Envelope must have payload attribute
        if not hasattr(envelope, "payload"):
            raise ModelOnexError(
                "Envelope missing required 'payload' attribute",
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
                context={"envelope_type": type(envelope).__name__},
            )

        # Extract event from envelope
        event = envelope.payload

        # Check if this event is a discovery request
        try:
            discovery_request_type = create_event_type_from_registry(
                "NODE_DISCOVERY_REQUEST",
            )

            if not is_event_equal(event.event_type, discovery_request_type):
                return

        except Exception:  # catch-all-ok: event handler returns early if type check fails, malformed events shouldn't crash
            # If we can't create the event type, skip
            return

        # Check if we should respond to this request
        if not self._should_respond_to_request(event):
            return

        try:
            # Respond with basic node information
            node_id = getattr(self, "_node_id", None) or "<unset>"
            context = ModelLogContext(
                calling_module=_COMPONENT_NAME,
                calling_function="_handle_node_discovery_request",
                calling_line=170,
                timestamp=datetime.now().isoformat(),
                node_id=(
                    UUID(node_id)
                    if isinstance(node_id, str) and node_id != "<unset>"
                    else None
                ),
            )
            emit_log_event_sync(
                LogLevel.DEBUG,
                f"Handled discovery request for node {node_id}",
                context=context,
            )

        except Exception as e:  # catch-all-ok: discovery request handling errors are logged but shouldn't crash
            node_id = getattr(self, "_node_id", None) or "<unset>"
            context = ModelLogContext(
                calling_module=_COMPONENT_NAME,
                calling_function="_handle_node_discovery_request",
                calling_line=183,
                timestamp=datetime.now().isoformat(),
                node_id=(
                    UUID(node_id)
                    if isinstance(node_id, str) and node_id != "<unset>"
                    else None
                ),
            )
            emit_log_event_sync(
                LogLevel.ERROR,
                f"Error handling discovery request: {e}",
                context=context,
            )

    def _should_respond_to_request(self, event: OnexEvent) -> bool:
        """
        Determine if this node should respond to the given request.

        Args:
            event: The request event

        Returns:
            True if this node should respond
        """
        try:
            # If no metadata, respond to all
            if not event.metadata:
                return True

            # Check node ID filter
            target_node_id = getattr(event.metadata, "target_node_id", None)
            if target_node_id:
                node_id = getattr(self, "_node_id", None) or "<unset>"
                return fnmatch.fnmatch(str(node_id), target_node_id)

            # Check node name filter
            target_node_name = getattr(event.metadata, "target_node_name", None)
            if target_node_name:
                node_name = self.__class__.__name__.lower()
                return fnmatch.fnmatch(node_name, target_node_name)

            # No specific filters, respond
            return True

        except Exception:  # catch-all-ok: filter error defaults to responding, safe fallback for event handling
            # On error, default to responding
            return True

    @staticmethod
    def _filter_introspection_data(
        introspection_data: "ModelNodeIntrospectionData | dict[str, object]",
        requested_types: list[str],
    ) -> dict[str, object]:
        """
        Filter introspection data based on requested types.

        Args:
            introspection_data: Full introspection data (ModelNodeIntrospectionData or dict)
            requested_types: List of requested data types

        Returns:
            Filtered introspection data as dict with requested fields only
        """
        # Convert to dict if it's a Pydantic model
        # Performance optimization: use model_dump(include=...) to only serialize
        # the requested fields, avoiding full model serialization overhead for
        # large introspection data structures
        if hasattr(introspection_data, "model_dump"):
            # Only dump the fields we actually need
            requested_set = set(requested_types)
            data_dict = introspection_data.model_dump(include=requested_set)
        else:
            data_dict = dict(introspection_data)

        filtered_data: dict[str, object] = {}

        for requested_type in requested_types:
            if requested_type in data_dict:
                filtered_data[requested_type] = data_dict[requested_type]

        return filtered_data

    def cleanup_event_handlers(self) -> None:
        """Clean up event handlers."""
        event_bus = getattr(self, "event_bus", None)
        if event_bus and hasattr(event_bus, "unsubscribe"):
            try:
                event_bus.unsubscribe(self._handle_introspection_request)
                event_bus.unsubscribe(self._handle_node_discovery_request)

                node_id = getattr(self, "_node_id", None) or "<unset>"
                context = ModelLogContext(
                    calling_module=_COMPONENT_NAME,
                    calling_function="cleanup_event_handlers",
                    calling_line=248,
                    timestamp=datetime.now().isoformat(),
                    node_id=(
                        UUID(node_id)
                        if isinstance(node_id, str) and node_id != "<unset>"
                        else None
                    ),
                )
                emit_log_event_sync(
                    LogLevel.DEBUG,
                    f"Event handlers cleaned up for node {node_id}",
                    context=context,
                )
            except (
                Exception
            ) as e:  # catch-all-ok: cleanup errors are logged but shouldn't crash
                node_id = getattr(self, "_node_id", None) or "<unset>"
                context = ModelLogContext(
                    calling_module=_COMPONENT_NAME,
                    calling_function="cleanup_event_handlers",
                    calling_line=261,
                    timestamp=datetime.now().isoformat(),
                    node_id=(
                        UUID(node_id)
                        if isinstance(node_id, str) and node_id != "<unset>"
                        else None
                    ),
                )
                emit_log_event_sync(
                    LogLevel.WARNING,
                    f"Error cleaning up event handlers: {e}",
                    context=context,
                )
