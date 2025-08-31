# === OmniNode:Metadata ===
# author: OmniNode Team
# description: Discovery responder mixin for ONEX nodes to respond to discovery broadcasts
# === /OmniNode:Metadata ===

import time
from datetime import datetime
from typing import Any

from omnibase_core.core.core_errors import CoreErrorCode, OnexError
from omnibase_core.core.decorators import allow_dict_str_any
from omnibase_core.model.core.model_onex_event import (
    DiscoveryRequestModelMetadata,
    DiscoveryResponseModelMetadata,
    OnexEvent,
)
from omnibase_core.protocol.protocol_event_bus import ProtocolEventBus
from omnibase_core.protocol.protocol_logger import ProtocolLogger


class DiscoveryResponderMixin:
    """
    Mixin for ONEX nodes to respond to discovery broadcasts.

    DISCOVERY RESPONDER PATTERN:
    - All nodes listen to 'onex.discovery.broadcast' channel
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._discovery_active = False
        self._last_response_time = 0
        self._response_throttle = 1.0  # Minimum seconds between responses
        self._discovery_stats = {
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
    ):
        """
        Start responding to discovery broadcasts.

        Args:
            event_bus: Event bus to listen on
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
            raise OnexError(
                msg,
                CoreErrorCode.DISCOVERY_SETUP_FAILED,
            )

    def stop_discovery_responder(self, logger: ProtocolLogger | None = None):
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

    @allow_dict_str_any(
        "Discovery request event data requires flexible dictionary structure",
    )
    def _handle_discovery_request(self, event_data: dict[str, Any]):
        """
        Handle incoming discovery requests.

        Args:
            event_data: Discovery request event data
        """
        try:
            # Parse discovery request
            event = OnexEvent(**event_data)

            if not is_event_equal(event.event_type, "DISCOVERY_REQUEST"):
                return  # Not a discovery request

            self._discovery_stats["requests_received"] += 1
            self._discovery_stats["last_request_time"] = time.time()

            # Check rate limiting
            current_time = time.time()
            if current_time - self._last_response_time < self._response_throttle:
                self._discovery_stats["throttled_requests"] += 1
                return  # Throttled

            # Extract request metadata
            request_metadata = event.metadata
            if not isinstance(request_metadata, DiscoveryRequestModelMetadata):
                return  # Invalid request format

            # Check if we match filter criteria
            if not self._matches_discovery_criteria(request_metadata):
                return  # Doesn't match criteria

            # Generate discovery response
            self._send_discovery_response(event, request_metadata)

            self._last_response_time = current_time
            self._discovery_stats["responses_sent"] += 1

        except Exception:
            # Silently handle errors to avoid disrupting discovery
            pass

    def _matches_discovery_criteria(
        self,
        request: DiscoveryRequestModelMetadata,
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

    @allow_dict_str_any("Filter criteria requires flexible dictionary structure")
    def _matches_custom_criteria(self, filter_criteria: dict[str, Any]) -> bool:
        """
        Check custom filter criteria.

        Override this method in subclasses for custom filtering logic.

        Args:
            filter_criteria: Custom filter criteria

        Returns:
            bool: True if node matches criteria, False otherwise
        """
        # Default implementation accepts all
        return True

    def _send_discovery_response(
        self,
        original_event: OnexEvent,
        request: DiscoveryRequestModelMetadata,
    ):
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
            response_metadata = DiscoveryResponseModelMetadata(
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
                event_type=create_event_type_from_string("DISCOVERY_RESPONSE"),
                node_id=getattr(self, "node_id", "unknown"),
                correlation_id=original_event.correlation_id,
                metadata=response_metadata,
            )

            # Publish response (assuming we have access to event bus)
            if hasattr(self, "_event_bus") and self._event_bus:
                self._event_bus.publish(
                    "onex.discovery.response",
                    response_event.model_dump(),
                )

        except Exception:
            # Log error but don't disrupt discovery
            pass

    @allow_dict_str_any("Introspection data requires flexible dictionary structure")
    def _get_discovery_introspection(self) -> dict[str, Any]:
        """
        Get introspection data for discovery response.

        Returns:
            dict: Node introspection data
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
            list: List of capabilities supported by the node
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
            dict: Event channels (subscribes_to, publishes_to)
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

    @allow_dict_str_any("Discovery stats require flexible dictionary structure")
    def get_discovery_stats(self) -> dict[str, Any]:
        """
        Get discovery responder statistics.

        Returns:
            dict: Discovery statistics
        """
        return {
            **self._discovery_stats,
            "active": self._discovery_active,
            "throttle_seconds": self._response_throttle,
            "last_response_time": self._last_response_time,
        }

    def reset_discovery_stats(self):
        """
        Reset discovery responder statistics.
        """
        self._discovery_stats = {
            "requests_received": 0,
            "responses_sent": 0,
            "throttled_requests": 0,
            "last_request_time": None,
        }
