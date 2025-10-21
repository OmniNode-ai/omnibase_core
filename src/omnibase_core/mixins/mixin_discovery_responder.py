# === OmniNode:Metadata ===
# author: OmniNode Team
# description: Discovery responder mixin for ONEX nodes to respond to discovery broadcasts
# === /OmniNode:Metadata ===

import asyncio
import json
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Optional, cast

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.models.core.model_discovery_request_response import (
    ModelDiscoveryRequestModelMetadata,
    ModelDiscoveryResponseModelMetadata,
)
from omnibase_core.models.core.model_event_type import (
    create_event_type_from_registry,
    is_event_equal,
)
from omnibase_core.models.core.model_onex_event import ModelOnexEvent as OnexEvent
from omnibase_core.primitives.model_semver import ModelSemVer
from omnibase_spi.protocols.event_bus import ProtocolEventBus

if TYPE_CHECKING:
    from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
    from omnibase_spi.protocols.types.protocol_event_bus_types import (
        ProtocolEventMessage,
    )


class MixinDiscoveryResponder:
    """
    Mixin for ONEX nodes to respond to discovery broadcasts.

    DISCOVERY RESPONDER PATTERN:
    - All nodes list[Any]en to 'onex.discovery.broadcast' channel
    - Respond to DISCOVERY_REQUEST events with introspection data
    - Include health status, capabilities, and full introspection
    - Rate limiting prevents discovery spam

    USAGE:
    - Mix into any ONEX node class that should participate in discovery
    - Call start_discovery_responder() during node initialization
    - Override get_discovery_capabilities() to customize capabilities
    - Override get_health_status() to provide current health

    RESPONSE CONTENT:
    - Full introspection data from node
    - Current health status and capabilities
    - Event channels and version information
    - Response time metrics
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._discovery_active = False
        self._last_response_time: float = 0.0
        self._response_throttle = 1.0  # Minimum seconds between responses
        self._discovery_stats: dict[str, int | float | None] = {
            "requests_received": 0,
            "responses_sent": 0,
            "throttled_requests": 0,
            "last_request_time": None,
        }
        self._discovery_event_bus: ProtocolEventBus | None = None
        self._discovery_unsubscribe: Any = None  # Callable to unsubscribe

    async def start_discovery_responder(
        self,
        event_bus: ProtocolEventBus,
        response_throttle: float = 1.0,
    ) -> None:
        """
        Start responding to discovery broadcasts.

        Args:
            event_bus: Event bus to listen on
            response_throttle: Minimum seconds between responses (rate limiting)
        """
        if self._discovery_active:
            emit_log_event(
                LogLevel.INFO,
                "Discovery responder already active",
                {"component": "DiscoveryResponder"},
            )
            return

        self._response_throttle = response_throttle
        self._discovery_event_bus = event_bus

        try:
            # Get node_id for group_id
            node_id = getattr(self, "node_id", "discovery-responder")
            group_id = f"discovery-{node_id}"

            # Subscribe to discovery broadcast channel
            # Create wrapper for protocol message -> envelope conversion
            self._discovery_unsubscribe = await event_bus.subscribe(
                topic="onex.discovery.broadcast",
                group_id=group_id,
                on_message=self._on_discovery_message,
            )

            self._discovery_active = True

            emit_log_event(
                LogLevel.INFO,
                f"Started discovery responder with {response_throttle}s throttle",
                {
                    "component": "DiscoveryResponder",
                    "node_id": node_id,
                    "response_throttle": response_throttle,
                },
            )

        except Exception as e:
            emit_log_event(
                LogLevel.ERROR,
                f"Failed to start discovery responder: {e!s}",
                {"component": "DiscoveryResponder", "error": str(e)},
            )
            msg = f"Failed to start discovery responder: {e!s}"
            raise ModelOnexError(
                EnumCoreErrorCode.DISCOVERY_SETUP_FAILED,
            )

    async def stop_discovery_responder(self) -> None:
        """
        Stop responding to discovery broadcasts.
        """
        if not self._discovery_active:
            return

        self._discovery_active = False

        # Unsubscribe from event bus
        if self._discovery_unsubscribe:
            try:
                await self._discovery_unsubscribe()
            except Exception:
                pass  # Ignore errors during cleanup

        emit_log_event(
            LogLevel.INFO,
            "Stopped discovery responder",
            {"component": "DiscoveryResponder", "stats": self._discovery_stats},
        )

    async def _on_discovery_message(self, message: "ProtocolEventMessage") -> None:
        """
        Adapter method to convert ProtocolEventMessage to ModelEventEnvelope.

        Args:
            message: Low-level protocol message from event bus
        """
        try:
            # Import here to avoid circular dependencies
            from omnibase_core.models.events.model_event_envelope import (
                ModelEventEnvelope,
            )

            # Deserialize the envelope from message value
            envelope_dict = json.loads(message.value.decode("utf-8"))
            envelope: ModelEventEnvelope[Any] = ModelEventEnvelope(**envelope_dict)

            # Acknowledge message receipt
            await message.ack()

            # Handle the discovery request
            await self._handle_discovery_request(envelope)

        except Exception:
            # Silently handle errors to avoid disrupting discovery
            pass

    async def _handle_discovery_request(
        self, envelope: "ModelEventEnvelope[Any]"
    ) -> None:
        """
        Handle incoming discovery requests.

        Args:
            envelope: Event envelope containing the discovery request
        """
        try:
            # Extract event from envelope and cast to OnexEvent for type safety
            event = envelope.payload if hasattr(envelope, "payload") else envelope
            # Type cast for mypy - event is ModelOnexEvent after extraction
            onex_event = cast(OnexEvent, event)

            if not hasattr(onex_event, "event_type") or not is_event_equal(
                onex_event.event_type, "DISCOVERY_REQUEST"
            ):
                return  # Not a discovery request

            # Type-safe increment (get returns int|float|None, but default ensures int)
            current_requests = self._discovery_stats.get("requests_received", 0)
            self._discovery_stats["requests_received"] = (
                current_requests if isinstance(current_requests, int) else 0
            ) + 1
            self._discovery_stats["last_request_time"] = time.time()

            # Check rate limiting
            current_time = time.time()
            if current_time - self._last_response_time < self._response_throttle:
                current_throttled = self._discovery_stats.get("throttled_requests", 0)
                self._discovery_stats["throttled_requests"] = (
                    current_throttled if isinstance(current_throttled, int) else 0
                ) + 1
                return  # Throttled

            # Extract request metadata
            request_metadata = onex_event.metadata
            if not isinstance(request_metadata, ModelDiscoveryRequestModelMetadata):
                return  # Invalid request format

            # Check if we match filter criteria
            if not self._matches_discovery_criteria(request_metadata):  # type: ignore[unreachable]
                return  # Doesn't match criteria

            # Generate discovery response
            await self._send_discovery_response(onex_event, request_metadata)

            self._last_response_time = current_time
            current_responses = self._discovery_stats.get("responses_sent", 0)
            self._discovery_stats["responses_sent"] = (
                current_responses if isinstance(current_responses, int) else 0
            ) + 1

        except Exception:
            # Silently handle errors to avoid disrupting discovery
            pass

    def _matches_discovery_criteria(
        self, request: ModelDiscoveryRequestModelMetadata
    ) -> bool:
        """
        Check if this node matches the discovery criteria.

        Args:
            request: Discovery request metadata

        Returns:
            bool: True if node matches criteria, False otherwise
        """
        # Check node type filter
        if request.node_types:
            node_type = self.__class__.__name__
            if node_type not in request.node_types:
                return False

        # Check capability filter
        if request.requested_capabilities:
            node_capabilities = self.get_discovery_capabilities()
            for required_capability in request.requested_capabilities:
                if required_capability not in node_capabilities:
                    return False

        # Check custom filter criteria
        if request.filter_criteria:
            if not self._matches_custom_criteria(request.filter_criteria):
                return False

        return True

    def _matches_custom_criteria(self, filter_criteria: dict[str, Any]) -> bool:
        """
        Check custom filter criteria.

        Override this method in subclasses for custom filtering logic.

        Args:
            filter_criteria: Custom filter criteria (dict[str, Any] required for flexible structure)

        Returns:
            bool: True if node matches criteria, False otherwise
        """
        # Default implementation accepts all
        return True

    async def _send_discovery_response(
        self,
        original_event: OnexEvent,
        request: ModelDiscoveryRequestModelMetadata,
    ) -> None:
        """
        Send discovery response back to requester.

        Args:
            original_event: Original discovery request event
            request: Request metadata
        """
        try:
            response_start = time.time()

            # Get node introspection data
            introspection_data = self._get_discovery_introspection()

            # Create discovery response
            # Get node_id as UUID or generate a temporary one
            from uuid import UUID, uuid4

            node_id_value: UUID
            if hasattr(self, "node_id"):
                node_id_attr = self.node_id
                if isinstance(node_id_attr, UUID):
                    node_id_value = node_id_attr
                elif isinstance(node_id_attr, str):
                    node_id_value = UUID(node_id_attr)
                else:
                    node_id_value = uuid4()
            else:
                node_id_value = uuid4()

            # Get version as ModelSemVer
            version_value = self._get_node_version()
            if version_value is None:
                version_semver = ModelSemVer(major=0, minor=0, patch=0)
            else:
                # Parse version string like "1.2.3"
                parts = version_value.split(".")
                try:
                    major = int(parts[0]) if len(parts) > 0 else 0
                    minor = int(parts[1]) if len(parts) > 1 else 0
                    patch = int(parts[2]) if len(parts) > 2 else 0
                    version_semver = ModelSemVer(major=major, minor=minor, patch=patch)
                except (ValueError, IndexError):
                    version_semver = ModelSemVer(major=0, minor=0, patch=0)

            # Get event channels as list
            channels_dict = self._get_discovery_event_channels()
            # Flatten the dict to a list of channel names
            event_channels_list: list[str] = []
            if channels_dict:
                for key, values in channels_dict.items():
                    if isinstance(values, list):
                        event_channels_list.extend(values)

            response_metadata = ModelDiscoveryResponseModelMetadata(
                request_id=request.request_id,
                node_id=node_id_value,
                introspection=introspection_data,
                health_status=self.get_health_status(),
                capabilities=self.get_discovery_capabilities(),
                node_type=self.__class__.__name__,
                version=version_semver,
                event_channels=event_channels_list,
                response_time_ms=(time.time() - response_start) * 1000,
            )

            # Use data field for discovery metadata instead of metadata field
            response_event = OnexEvent(
                event_type=create_event_type_from_registry("DISCOVERY_RESPONSE"),
                node_id=node_id_value,
                correlation_id=original_event.correlation_id,
                data=response_metadata.model_dump(),
            )

            # Publish response (assuming we have access to event bus)
            if self._discovery_event_bus:
                # Local import to avoid circular dependency
                from omnibase_core.models.events.model_event_envelope import (
                    ModelEventEnvelope,
                )

                # Wrap in envelope before publishing
                envelope = ModelEventEnvelope.create_broadcast(
                    payload=response_event,
                    source_node_id=getattr(self, "node_id", uuid4()),
                    correlation_id=original_event.correlation_id,
                )

                # Serialize envelope to bytes for protocol event bus
                envelope_bytes = json.dumps(envelope.model_dump()).encode("utf-8")

                # Publish to event bus (protocol requires topic, key, value, headers)
                await self._discovery_event_bus.publish(
                    topic="onex.discovery.response",
                    key=None,
                    value=envelope_bytes,
                )

        except Exception:
            # Log error but don't disrupt discovery
            pass

    def _get_discovery_introspection(self) -> dict[str, Any]:
        """
        Get introspection data for discovery response.

        Returns:
            dict[str, Any]: Node introspection data (dict[str, Any] required for flexible structure)
        """
        if hasattr(self, "get_introspection_response"):
            try:
                introspection_response = self.get_introspection_response()
                return introspection_response.model_dump()
            except Exception:
                pass

        # Fallback to basic introspection
        return {
            "node_id": getattr(self, "node_id", "unknown"),
            "node_type": self.__class__.__name__,
            "capabilities": self.get_discovery_capabilities(),
            "health_status": self.get_health_status(),
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def get_discovery_capabilities(self) -> list[str]:
        """
        Get capabilities supported by this node for discovery.

        Override this method in subclasses to provide specific capabilities.

        Returns:
            list[Any]: List of capabilities supported by the node
        """
        capabilities = ["discovery", "introspection"]

        # Add capabilities based on available methods
        if hasattr(self, "run"):
            capabilities.append("execution")
        if hasattr(self, "bind"):
            capabilities.append("binding")
        if hasattr(self, "get_introspection_response"):
            capabilities.append("full_introspection")
        if hasattr(self, "handle_event"):
            capabilities.append("event_handling")

        return capabilities

    def get_health_status(self) -> str:
        """
        Get current health status of the node.

        Override this method in subclasses to provide specific health checks.

        Returns:
            str: Health status ('healthy', 'degraded', 'unhealthy')
        """
        # Default implementation - always healthy
        # Subclasses should implement actual health checks
        return "healthy"

    def _get_node_version(self) -> str | None:
        """
        Get version of the node.

        Returns:
            str: Node version if available
        """
        if hasattr(self, "version"):
            return self.version
        if hasattr(self, "node_version"):
            return self.node_version
        return None

    def _get_discovery_event_channels(self) -> dict[str, list[str]]:
        """
        Get event channels for discovery response.

        Returns:
            dict[str, Any]: Event channels (subscribes_to, publishes_to)
        """
        if hasattr(self, "get_event_channels"):
            try:
                channels = self.get_event_channels()
                return channels.model_dump()
            except Exception:
                pass

        # Fallback to universal channels
        return {
            "subscribes_to": ["onex.discovery.broadcast"],
            "publishes_to": ["onex.discovery.response"],
        }

    def get_discovery_stats(self) -> dict[str, Any]:
        """
        Get discovery responder statistics.

        Returns:
            dict[str, Any]: Discovery statistics (dict[str, Any] required for flexible structure)
        """
        return {
            **self._discovery_stats,
            "active": self._discovery_active,
            "throttle_seconds": self._response_throttle,
            "last_response_time": self._last_response_time,
        }

    def reset_discovery_stats(self) -> None:
        """
        Reset discovery responder statistics.
        """
        self._discovery_stats = {
            "requests_received": 0,
            "responses_sent": 0,
            "throttled_requests": 0,
            "last_request_time": None,
        }
