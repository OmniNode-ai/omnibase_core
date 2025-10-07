from typing import Callable, List, Optional
from uuid import UUID

"""
Mixin for event-driven service registry and tool discovery.

Provides automatic tool discovery, registration, and lifecycle management
through event bus integration. Maintains a live registry of available tools
and their capabilities.
"""

import logging
import time
import traceback
from collections.abc import Callable as CallableABC
from typing import TYPE_CHECKING, Any, Callable, Optional
from uuid import uuid4

if TYPE_CHECKING:
    from omnibase_core.models.core.model_event_envelope import ModelEventEnvelope

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.models.core.model_onex_event import ModelOnexEvent

logger = logging.getLogger(__name__)


from .model_service_registry_entry import MixinServiceRegistryEntry


class MixinServiceRegistry:
    """
    Mixin for event-driven service registry and tool discovery.

    Provides automatic tool discovery, registration, and lifecycle management
    through event bus integration. Services using this mixin become service
    registries that maintain live catalogs of available tools.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the service registry mixin."""
        # Extract mixin-specific kwargs before passing to super()
        introspection_timeout = kwargs.pop("introspection_timeout", 30)
        service_ttl = kwargs.pop("service_ttl", 300)
        auto_cleanup_interval = kwargs.pop("auto_cleanup_interval", 60)

        super().__init__(*args, **kwargs)

        # Service registry
        self.service_registry: dict[str, MixinServiceRegistryEntry] = {}
        self.discovery_callbacks: list[Callable[..., Any]] = []

        # Configuration
        self.introspection_timeout = introspection_timeout
        self.service_ttl = service_ttl
        self.auto_cleanup_interval = auto_cleanup_interval

        # State
        self.registry_started = False
        self.cleanup_task: Any = None  # asyncio.TimerHandle or None
        self._event_handlers_setup = False

        # Don't setup event handlers during init - defer until start_service_registry

    def _setup_registry_event_handlers(self) -> None:
        """Setup event handlers for service lifecycle events."""
        logger.info(
            f"🔧 Setting up registry event handlers - event_bus: {hasattr(self, 'event_bus')}, value: {getattr(self, 'event_bus', None)}",
        )

        if hasattr(self, "event_bus") and self.event_bus:
            try:
                # Listen for node start events (new tools coming online)
                self.event_bus.subscribe("core.node.start", self._handle_node_start)
                logger.info("✅ Subscribed to core.node.start")

                # Listen for node stop/failure events (tools going offline)
                self.event_bus.subscribe("core.node.stop", self._handle_node_stop)
                logger.info("✅ Subscribed to core.node.stop")

                self.event_bus.subscribe("core.node.failure", self._handle_node_failure)
                logger.info("✅ Subscribed to core.node.failure")

                # Listen for introspection responses
                self.event_bus.subscribe(
                    "core.discovery.introspection_response",
                    self._handle_introspection_response,
                )
                logger.info("✅ Subscribed to core.discovery.introspection_response")

                # Listen for discovery requests (realtime requests from other hubs/services)
                self.event_bus.subscribe(
                    "core.discovery.realtime_request",
                    self._handle_discovery_request,
                )
                logger.info("✅ Subscribed to core.discovery.realtime_request")

                logger.info(
                    "🔔 Service registry event handlers registered successfully!",
                )

            except Exception as e:
                logger.exception(f"❌ Failed to setup registry event handlers: {e}")
                import traceback

                traceback.print_exc()
        else:
            logger.error(
                f"❌ Cannot setup event handlers - event_bus not available: hasattr={hasattr(self, 'event_bus')}, event_bus={getattr(self, 'event_bus', None)}",
            )

    def start_service_registry(self, domain_filter: str | None = None) -> None:
        """
        Start the service registry with optional domain filtering.

        Args:
            domain_filter: Optional domain filter (e.g., "generation", "ai")
        """
        if self.registry_started:
            return

        self.domain_filter = domain_filter
        self.registry_started = True

        # Setup event handlers now that event bus should be available
        if not self._event_handlers_setup:
            self._setup_registry_event_handlers()
            self._event_handlers_setup = True

        emit_log_event(
            LogLevel.INFO,
            "Starting service registry",
            {
                "domain_filter": domain_filter,
                "node_id": getattr(self, "node_id", "unknown"),
            },
        )

        # Start cleanup task
        if hasattr(self, "_schedule_cleanup"):
            self._schedule_cleanup()

        # Send initial discovery request
        self._send_discovery_request()

        logger.info(f"🚀 Service registry started for domain: {domain_filter or 'all'}")

    def stop_service_registry(self) -> None:
        """Stop the service registry."""
        self.registry_started = False

        if self.cleanup_task:
            self.cleanup_task.cancel()

        logger.info("🛑 Service registry stopped")

    def _send_discovery_request(self) -> None:
        """Send a discovery request to find active tools."""
        if not hasattr(self, "event_bus") or not self.event_bus:
            return

        correlation_id = uuid4()

        try:
            # Import the required models
            from omnibase_core.models.core.model_onex_event import ModelOnexEvent

            # Create the discovery event
            discovery_event = ModelOnexEvent(
                event_type="core.discovery.realtime_request",
                node_id=getattr(self, "node_id", uuid4()),
                correlation_id=correlation_id,
                data={
                    "request_type": "tool_discovery",
                    "domain_filter": getattr(self, "domain_filter", None),
                    "capabilities_required": [],
                },
            )

            # Create event envelope
            envelope = ModelEventEnvelope.create_direct(
                payload=discovery_event,
                destination="broadcast://all",
                source_node_id=getattr(self, "node_id", f"registry_{uuid4().hex[:8]}"),
                correlation_id=correlation_id,
                metadata={
                    "request_type": "tool_discovery",
                    "domain_filter": getattr(self, "domain_filter", None),
                },
            )

            logger.info(f"🔍 Sending discovery request envelope: {envelope}")
            self.event_bus.publish(envelope)

            emit_log_event(
                LogLevel.INFO,
                "Discovery request sent",
                {"correlation_id": correlation_id},
            )

        except Exception as e:
            logger.exception(f"❌ Failed to send discovery request: {e}")

            traceback.print_exc()

    def _handle_node_start(self, envelope: "ModelEventEnvelope") -> None:
        """Handle node start events - new tools coming online."""
        try:
            # Extract event data from envelope (ENVELOPE-ONLY FLOW)
            event_data = (
                envelope.payload.data
                if hasattr(envelope, "payload") and hasattr(envelope.payload, "data")
                else {}
            )
            event_data = event_data if event_data is not None else {}
            node_id = (
                event_data.get("node_name") or envelope.payload.node_id
                if hasattr(envelope, "payload")
                else None
            )
            if not node_id:
                return

            # Skip if this is our own start event
            if node_id == getattr(self, "node_id", None):
                return

            # Check domain filter if set
            if hasattr(self, "domain_filter") and self.domain_filter:
                metadata = event_data.get("metadata", {})
                service_domain = metadata.get("domain")
                if service_domain and service_domain != self.domain_filter:
                    return

            # Register or update service
            service_name = event_data.get("node_name", node_id)

            # Convert node_id to UUID if it's a string, or keep as is if already UUID
            from uuid import UUID as UUIDType

            if isinstance(node_id, str):
                try:
                    node_id_uuid = UUIDType(node_id)
                except (ValueError, AttributeError):
                    # If not a valid UUID string, generate a new UUID
                    node_id_uuid = uuid4()
            elif isinstance(node_id, UUID):
                node_id_uuid = node_id
            else:
                # Fallback for any other type
                node_id_uuid = uuid4()

            # Use string representation for dict key
            node_id_str = str(node_id_uuid)

            if node_id_str not in self.service_registry:
                entry = MixinServiceRegistryEntry(
                    node_id=node_id_uuid,
                    service_name=service_name,
                    metadata=event_data.get("metadata", {}),
                )
                self.service_registry[node_id_str] = entry

                emit_log_event(
                    LogLevel.INFO,
                    f"New tool discovered: {service_name}",
                    {"node_id": node_id_str, "service_name": service_name},
                )

                # Send introspection request to get tool capabilities
                self._send_introspection_request(node_id)

                # Call discovery callbacks
                for callback in self.discovery_callbacks:
                    try:
                        callback("tool_discovered", entry)
                    except Exception as e:
                        logger.exception(f"Discovery callback error: {e}")
            else:
                # Update existing entry
                self.service_registry[node_id_str].update_last_seen()

        except Exception as e:
            logger.exception(f"❌ Error handling node start event: {e}")

    def _handle_node_stop(self, envelope: "ModelEventEnvelope") -> None:
        """Handle node stop events - tools going offline."""
        try:
            # Extract event data from envelope (ENVELOPE-ONLY FLOW)
            event_data = (
                envelope.payload.data
                if hasattr(envelope, "payload") and hasattr(envelope.payload, "data")
                else {}
            )
            event_data = event_data if event_data is not None else {}
            node_id = (
                event_data.get("node_name") or envelope.payload.node_id
                if hasattr(envelope, "payload")
                else None
            )
            if node_id:
                # Ensure node_id is string for dict key
                node_id_str = (
                    str(node_id) if isinstance(node_id, UUID) else str(node_id)
                )

                if node_id_str in self.service_registry:
                    self.service_registry[node_id_str].set_offline()

                    emit_log_event(
                        LogLevel.INFO,
                        f"Tool went offline: {self.service_registry[node_id_str].service_name}",
                        {"node_id": node_id_str},
                    )

                    # Call discovery callbacks
                    for callback in self.discovery_callbacks:
                        try:
                            callback("tool_offline", self.service_registry[node_id_str])
                        except Exception as e:
                            logger.exception(f"Discovery callback error: {e}")

        except Exception as e:
            logger.exception(f"❌ Error handling node stop event: {e}")

    def _handle_node_failure(self, envelope: "ModelEventEnvelope") -> None:
        """Handle node failure events - tools failing."""
        # Same logic as stop for now
        self._handle_node_stop(envelope)

    def _send_introspection_request(self, node_id: UUID | str) -> None:
        """Send introspection request to a specific node."""
        if not hasattr(self, "event_bus") or not self.event_bus:
            return

        correlation_id = uuid4()

        try:
            # Create the introspection event
            introspection_event = ModelOnexEvent(
                event_type="core.discovery.node_introspection",
                node_id=getattr(self, "node_id", uuid4()),
                correlation_id=correlation_id,
                data={
                    "target_node_id": str(node_id),
                    "requested_info": ["capabilities", "metadata", "health_status"],
                },
            )

            # Create event envelope
            envelope = ModelEventEnvelope.create_direct(
                payload=introspection_event,
                destination=f"node://{node_id}",
                source_node_id=getattr(self, "node_id", f"registry_{uuid4().hex[:8]}"),
                correlation_id=correlation_id,
                metadata={"target_node_id": node_id, "request_type": "introspection"},
            )

            self.event_bus.publish(envelope)

            emit_log_event(
                LogLevel.DEBUG,
                f"Introspection request sent to {node_id}",
                {"target_node_id": node_id, "correlation_id": correlation_id},
            )

        except Exception as e:
            logger.exception(
                f"❌ Failed to send introspection request to {node_id}: {e}",
            )

    def _handle_introspection_response(self, envelope: "ModelEventEnvelope") -> None:
        """Handle introspection responses from tools."""
        try:
            # Extract event data from envelope (ENVELOPE-ONLY FLOW)
            node_id = envelope.payload.node_id if hasattr(envelope, "payload") else None
            if node_id:
                # Ensure node_id is string for dict key
                node_id_str = (
                    str(node_id) if isinstance(node_id, UUID) else str(node_id)
                )

                if node_id_str in self.service_registry:
                    introspection_data = (
                        envelope.payload.data
                        if hasattr(envelope, "payload")
                        and hasattr(envelope.payload, "data")
                        else {}
                    )
                    introspection_data = (
                        introspection_data if introspection_data is not None else {}
                    )
                    self.service_registry[node_id_str].update_introspection(
                        introspection_data
                    )

                    emit_log_event(
                        LogLevel.DEBUG,
                        f"Updated introspection data for {node_id_str}",
                        {
                            "node_id": node_id_str,
                            "capabilities_count": len(
                                introspection_data.get("capabilities", []),
                            ),
                        },
                    )

        except Exception as e:
            logger.exception(f"❌ Error handling introspection response: {e}")

    def _handle_discovery_request(self, envelope: "ModelEventEnvelope") -> None:
        """Handle discovery requests from other hubs/services."""
        try:
            # Extract event data from envelope (ENVELOPE-ONLY FLOW)
            event_data = (
                envelope.payload.data
                if hasattr(envelope, "payload") and hasattr(envelope.payload, "data")
                else {}
            )
            event_data = event_data if event_data is not None else {}
            logger.info(f"📡 Received discovery request: {envelope}")

            # Extract request details
            request_type = event_data.get("request_type", "unknown")
            domain_filter = event_data.get("domain_filter")
            correlation_id = (
                envelope.correlation_id if hasattr(envelope, "correlation_id") else None
            )

            # If domain filter is specified and doesn't match our domain, ignore
            if domain_filter and hasattr(self, "domain_filter") and self.domain_filter:
                if domain_filter != self.domain_filter:
                    logger.debug(
                        f"🔍 Ignoring discovery request for domain '{domain_filter}' (we are '{self.domain_filter}')",
                    )
                    return

            # Respond with our available tools/services
            if request_type == "tool_discovery":
                response_data = {
                    "hub_domain": getattr(self, "domain_filter", "unknown"),
                    "available_tools": [
                        {
                            "service_name": entry.service_name,
                            "node_id": entry.node_id,
                            "status": entry.status,
                            "capabilities": getattr(entry, "capabilities", []),
                        }
                        for entry in self.service_registry.values()
                    ],
                    "hub_status": "online",
                    "response_to": correlation_id,
                }

                # Send discovery response
                if hasattr(self, "event_bus") and self.event_bus:
                    # Create event and wrap in envelope
                    from omnibase_core.models.core.model_onex_event import (
                        ModelOnexEvent,
                    )

                    response_event = ModelOnexEvent(
                        event_type="core.discovery.response",
                        node_id=getattr(self, "node_id", uuid4()),
                        correlation_id=correlation_id,
                        data=response_data,
                    )

                    envelope = ModelEventEnvelope.create_broadcast(
                        payload=response_event,
                        source_node_id=getattr(
                            self, "node_id", f"registry_{uuid4().hex[:8]}"
                        ),
                        correlation_id=correlation_id,
                    )

                    self.event_bus.publish(envelope)
                    logger.info(
                        f"📤 Sent discovery response with {len(self.service_registry)} tools",
                    )
                else:
                    logger.warning(
                        "⚠️ Cannot send discovery response - no event bus available",
                    )

        except Exception as e:
            logger.exception(f"❌ Error handling discovery request: {e}")

    def get_registered_tools(
        self,
        status_filter: str | None = None,
    ) -> list[MixinServiceRegistryEntry]:
        """
        Get list[Any]of registered tools.

        Args:
            status_filter: Optional status filter ("online", "offline")

        Returns:
            List of MixinServiceRegistryEntry objects
        """
        tools = list(self.service_registry.values())

        if status_filter:
            tools = [t for t in tools if t.status == status_filter]

        return tools

    def get_tool_by_name(self, service_name: str) -> MixinServiceRegistryEntry | None:
        """Get tool by service name."""
        for entry in self.service_registry.values():
            if entry.service_name == service_name:
                return entry
        return None

    def get_tools_by_capability(
        self, capability: str
    ) -> list[MixinServiceRegistryEntry]:
        """Get tools that have a specific capability."""
        matching_tools = []
        for entry in self.service_registry.values():
            if capability in entry.capabilities and entry.status == "online":
                matching_tools.append(entry)
        return matching_tools

    def add_discovery_callback(self, callback: Callable[..., Any]) -> None:
        """
        Add a callback for discovery events.

        Callback signature: callback(event_type: str, entry: ServiceRegistryEntry)
        Event types: 'tool_discovered', 'tool_offline'
        """
        self.discovery_callbacks.append(callback)

    def cleanup_stale_entries(self) -> None:
        """Clean up stale registry entries based on TTL."""
        current_time = time.time()
        stale_entries = []

        for node_id, entry in self.service_registry.items():
            if (
                entry.status == "online"
                and (current_time - entry.last_seen) > self.service_ttl
            ):
                entry.set_offline()
                stale_entries.append(node_id)

        if stale_entries:
            emit_log_event(
                LogLevel.INFO,
                f"Marked {len(stale_entries)} stale entries as offline",
                {"stale_entries": stale_entries},
            )

    def _schedule_cleanup(self) -> None:
        """Schedule periodic cleanup of stale entries."""
        if hasattr(self, "event_loop") and self.event_loop:
            try:
                self.cleanup_task = self.event_loop.call_later(
                    self.auto_cleanup_interval,
                    self._cleanup_and_reschedule,
                )
            except Exception as e:
                logger.debug(f"Could not schedule cleanup task: {e}")

    def _cleanup_and_reschedule(self) -> None:
        """Cleanup and reschedule next cleanup."""
        try:
            self.cleanup_stale_entries()
        except Exception as e:
            logger.exception(f"❌ Error during cleanup: {e}")
        finally:
            if self.registry_started:
                self._schedule_cleanup()

    def get_registry_stats(self) -> dict[str, Any]:
        """Get registry statistics."""
        online_count = len(
            [e for e in self.service_registry.values() if e.status == "online"],
        )
        offline_count = len(
            [e for e in self.service_registry.values() if e.status == "offline"],
        )

        return {
            "total_services": len(self.service_registry),
            "online_services": online_count,
            "offline_services": offline_count,
            "domain_filter": getattr(self, "domain_filter", None),
            "registry_started": self.registry_started,
        }
