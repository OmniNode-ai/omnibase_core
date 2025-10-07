# === OmniNode:Metadata ===
# author: OmniNode Team
# description: Discovery responder mixin for ONEX nodes to respond to discovery broadcasts
# === /OmniNode:Metadata ===

import time
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional

from omnibase_spi import ProtocolLogger
from omnibase_spi.protocols.event_bus import ProtocolEventBus

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.core.model_discovery_request_response import (
    ModelDiscoveryRequestModelMetadata,
    ModelDiscoveryResponseModelMetadata,
)
from omnibase_core.models.core.model_event_type import (
    create_event_type_from_registry,
    is_event_equal,
)
from omnibase_core.models.core.model_onex_event import ModelOnexEvent as OnexEvent

if TYPE_CHECKING:
    from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope


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

    def start_discovery_responder(
        self,
        event_bus: ProtocolEventBus,
        logger: ProtocolLogger | None = None,
        response_throttle: float = 1.0,
    ) -> None:
        """
        Start responding to discovery broadcasts.

        Args:
            event_bus: Event bus to list[Any]en on
            logger: Optional logger for discovery operations
            response_throttle: Minimum seconds between responses (rate limiting)
        """
        if self._discovery_active:
            if logger:
                logger.log("[DiscoveryResponder] Discovery responder already active")
            return

        self._response_throttle = response_throttle

        try:
            # Subscribe to discovery broadcast channel
            event_bus.subscribe(
                "onex.discovery.broadcast",
                self._handle_discovery_request,
            )

            self._discovery_active = True

            if logger:
                logger.log(
                    f"[DiscoveryResponder] Started discovery responder with {response_throttle}s throttle",
                )
                logger.log(
                    f"[DiscoveryResponder] Node ID: {getattr(self, 'node_id', 'unknown')}",
                )

        except Exception as e:
            if logger:
                logger.log(
                    f"[DiscoveryResponder] Failed to start discovery responder: {e!s}",
                )
            msg = f"Failed to start discovery responder: {e!s}"
            raise ModelOnexError(
                EnumCoreErrorCode.DISCOVERY_SETUP_FAILED,
            )

    def stop_discovery_responder(self, logger: ProtocolLogger | None = None) -> None:
        """
        Stop responding to discovery broadcasts.

        Args:
            logger: Optional logger for discovery operations
        """
        if not self._discovery_active:
            return

        self._discovery_active = False

        if logger:
            logger.log("[DiscoveryResponder] Stopped discovery responder")
            logger.log(f"[DiscoveryResponder] Stats: {self._discovery_stats}")

    def _handle_discovery_request(self, envelope: "ModelEventEnvelope[Any]") -> None:
        """
        Handle incoming discovery requests.

        Args:
            envelope: Event envelope containing the discovery request
        """
        try:
            # Extract event from envelope
            event = envelope.payload if hasattr(envelope, "payload") else envelope

            if not hasattr(event, "event_type") or not is_event_equal(event.event_type, "DISCOVERY_REQUEST"):
                return  # Not a discovery request

            self._discovery_stats["requests_received"] = self._discovery_stats.get("requests_received", 0) + 1
            self._discovery_stats["last_request_time"] = time.time()

            # Check rate limiting
            current_time = time.time()
            if current_time - self._last_response_time < self._response_throttle:
                self._discovery_stats["throttled_requests"] = self._discovery_stats.get("throttled_requests", 0) + 1
                return  # Throttled

            # Extract request metadata
            request_metadata = event.metadata
            if not isinstance(request_metadata, ModelDiscoveryRequestModelMetadata):
                return  # Invalid request format

            # Check if we match filter criteria
            if not self._matches_discovery_criteria(request_metadata):
                return  # Doesn't match criteria

            # Generate discovery response
            self._send_discovery_response(event, request_metadata)

            self._last_response_time = current_time
            self._discovery_stats["responses_sent"] = self._discovery_stats.get("responses_sent", 0) + 1

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

    def _send_discovery_response(
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
            response_metadata = ModelDiscoveryResponseModelMetadata(
                request_id=request.request_id,
                node_id=getattr(self, "node_id", "unknown"),
                introspection=introspection_data,
                health_status=self.get_health_status(),
                capabilities=self.get_discovery_capabilities(),
                node_type=self.__class__.__name__,
                version=self._get_node_version(),
                event_channels=self._get_discovery_event_channels(),
                response_time_ms=(time.time() - response_start) * 1000,
            )

            response_event = OnexEvent(
                event_type=create_event_type_from_registry("DISCOVERY_RESPONSE"),
                node_id=getattr(self, "node_id", "unknown"),
                correlation_id=original_event.correlation_id,
                metadata=response_metadata,
            )

            # Publish response (assuming we have access to event bus)
            if hasattr(self, "_event_bus") and self._event_bus:
                # Local import to avoid circular dependency
                from omnibase_core.models.events.model_event_envelope import (
                    ModelEventEnvelope,
                )

                # Wrap in envelope before publishing
                envelope = ModelEventEnvelope.create_broadcast(
                    payload=response_event,
                    source_node_id=getattr(self, "node_id", "unknown"),
                    correlation_id=original_event.correlation_id,
                )
                self._event_bus.publish(envelope)

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
            "timestamp": datetime.utcnow().isoformat(),
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
