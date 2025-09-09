# === OmniNode:Metadata ===
# author: OmniNode Team
# description: Auto-connect mixin for ONEX nodes to automatically discover and connect to Kafka event bus
# === /OmniNode:Metadata ===

import json
import time
from typing import TYPE_CHECKING, Any

from omnibase_spi.protocols.core.protocol_logger import ProtocolLogger

from omnibase_core.model.configuration.model_event_bus_config import (
    ModelModelEventBusConfig,
)
from omnibase_core.model.core.model_event_type import create_event_type_from_string
from omnibase_core.model.core.model_onex_event import OnexEvent
from omnibase_core.nodes.node_kafka_event_bus.v1_0_0.registry.registry_bootstrap import (
    BootstrapRegistry,
)

if TYPE_CHECKING:
    from omnibase_core.protocol.protocol_event_bus import ProtocolEventBus


class AutoConnectMixin:
    """
    Mixin for ONEX nodes to automatically connect to Kafka event bus and participate in discovery.

    AUTO-CONNECT PATTERN:
    - Nodes inherit this mixin to get auto-discovery capabilities
    - Uses universal event channels for discovery announcements
    - Handles connection failures gracefully with retries
    - Publishes node announcement after successful connection

    USAGE:
    - Mix into any ONEX node class that needs event bus connectivity
    - Call auto_connect_to_kafka() during node initialization
    - Override get_node_announcement() to customize discovery data

    DISCOVERY FLOW:
    1. Node attempts connection to Kafka using bootstrap registry
    2. On success, publishes announcement to universal discovery channel
    3. Bootstrap registry receives announcement and updates node registry
    4. Node can now participate in full event-driven operations
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._event_bus: ProtocolEventBus | None = None
        self._auto_connect_config: dict[str, Any] | None = None
        self._connection_retries = 0
        self._max_retries = 3
        self._retry_delay = 5.0  # seconds

    def auto_connect_to_kafka(
        self,
        kafka_bootstrap_servers: str = "localhost:9092",
        logger: ProtocolLogger | None = None,
        max_retries: int = 3,
        retry_delay: float = 5.0,
    ) -> bool:
        """
        Automatically connect to Kafka event bus and announce node presence.

        Args:
            kafka_bootstrap_servers: Kafka connection string
            logger: Optional logger for connection operations
            max_retries: Maximum connection retry attempts
            retry_delay: Delay between retry attempts in seconds

        Returns:
            bool: True if connection successful, False otherwise
        """
        self._max_retries = max_retries
        self._retry_delay = retry_delay

        if logger:
            logger.log(
                f"[AutoConnect] Attempting Kafka connection to {kafka_bootstrap_servers}",
            )

        for attempt in range(max_retries + 1):
            try:
                # Create bootstrap registry for minimal connection
                bootstrap_registry = BootstrapRegistry(
                    kafka_bootstrap_servers=kafka_bootstrap_servers,
                    logger=logger,
                )

                if not bootstrap_registry.validate_bootstrap_readiness():
                    if logger:
                        logger.log(
                            f"[AutoConnect] Bootstrap registry not ready, attempt {attempt + 1}/{max_retries + 1}",
                        )
                    if attempt < max_retries:
                        time.sleep(retry_delay)
                        continue
                    return False

                # Create Kafka event bus using bootstrap registry
                kafka_tool = bootstrap_registry.get_tool("tool_kafka")
                if not kafka_tool:
                    if logger:
                        logger.log(
                            "[AutoConnect] Kafka tool not available in bootstrap registry",
                        )
                    return False

                # Create event bus configuration
                config = ModelModelEventBusConfig(
                    backend="kafka",
                    kafka_config=bootstrap_registry.create_kafka_config(),
                )

                # Initialize event bus
                self._event_bus = kafka_tool(config=config, logger=logger)
                self._auto_connect_config = {
                    "kafka_servers": kafka_bootstrap_servers,
                    "connected_at": time.time(),
                    "attempt": attempt + 1,
                }

                if logger:
                    logger.log(
                        f"[AutoConnect] Successfully connected to Kafka on attempt {attempt + 1}",
                    )

                # Publish node announcement to discovery channel
                self._publish_node_announcement(logger)

                return True

            except Exception as e:
                self._connection_retries = attempt + 1
                if logger:
                    logger.log(
                        f"[AutoConnect] Connection attempt {attempt + 1} failed: {e!s}",
                    )

                if attempt < max_retries:
                    if logger:
                        logger.log(
                            f"[AutoConnect] Retrying in {retry_delay} seconds...",
                        )
                    time.sleep(retry_delay)
                else:
                    if logger:
                        logger.log(
                            f"[AutoConnect] All {max_retries + 1} connection attempts failed",
                        )
                    return False

        return False

    def _publish_node_announcement(self, logger: ProtocolLogger | None = None):
        """
        Publish node announcement to universal discovery channel.

        Args:
            logger: Optional logger for announcement operations
        """
        if not self._event_bus:
            if logger:
                logger.log(
                    "[AutoConnect] Cannot publish announcement - no event bus connection",
                )
            return

        try:
            # Get node announcement data
            announcement_data = self.get_node_announcement()

            # Create discovery event
            discovery_event = OnexEvent(
                event_type=create_event_type_from_string("NODE_ANNOUNCEMENT"),
                payload=announcement_data,
                source_node_id=getattr(self, "node_id", "unknown"),
                target_channel="onex.discovery.broadcast",
                correlation_id=f"auto-connect-{int(time.time())}",
            )

            # Publish to universal discovery channel
            self._event_bus.publish(
                "onex.discovery.broadcast",
                discovery_event.model_dump(),
            )

            if logger:
                logger.log(
                    "[AutoConnect] Published node announcement to discovery channel",
                )
                logger.log(
                    f"[AutoConnect] Announcement data: {json.dumps(announcement_data, indent=2)}",
                )

        except Exception as e:
            if logger:
                logger.log(
                    f"[AutoConnect] Failed to publish node announcement: {e!s}",
                )

    def get_node_announcement(self) -> dict[str, Any]:
        """
        Get node announcement data for discovery.

        Override this method in subclasses to customize discovery data.

        Returns:
            dict: Node announcement data
        """
        # Try to get introspection data if available
        introspection_data = {}
        if hasattr(self, "get_introspection_response"):
            try:
                introspection_response = self.get_introspection_response()
                introspection_data = introspection_response.model_dump()
            except Exception:
                pass  # Fallback to basic data if introspection fails

        return {
            "node_id": getattr(self, "node_id", "unknown"),
            "node_type": self.__class__.__name__,
            "connection_info": self._auto_connect_config,
            "introspection": introspection_data,
            "announced_at": time.time(),
            "event_channels": self._get_node_event_channels(),
        }

    def _get_node_event_channels(self) -> dict[str, list[str]]:
        """
        Get event channels for this node.

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

    def get_auto_connect_status(self) -> dict[str, Any]:
        """
        Get auto-connect status information.

        Returns:
            dict: Connection status and configuration
        """
        return {
            "connected": self._event_bus is not None,
            "connection_retries": self._connection_retries,
            "max_retries": self._max_retries,
            "config": self._auto_connect_config,
            "event_bus_type": (
                type(self._event_bus).__name__ if self._event_bus else None
            ),
        }

    def disconnect_from_kafka(self, logger: ProtocolLogger | None = None):
        """
        Disconnect from Kafka event bus.

        Args:
            logger: Optional logger for disconnect operations
        """
        if self._event_bus:
            try:
                # Publish disconnect announcement
                disconnect_event = OnexEvent(
                    event_type=create_event_type_from_string("NODE_DISCONNECT"),
                    payload={"node_id": getattr(self, "node_id", "unknown")},
                    source_node_id=getattr(self, "node_id", "unknown"),
                    target_channel="onex.discovery.broadcast",
                    correlation_id=f"disconnect-{int(time.time())}",
                )

                self._event_bus.publish(
                    "onex.discovery.broadcast",
                    disconnect_event.model_dump(),
                )

                if logger:
                    logger.log("[AutoConnect] Published disconnect announcement")

            except Exception as e:
                if logger:
                    logger.log(
                        f"[AutoConnect] Failed to publish disconnect announcement: {e!s}",
                    )

            finally:
                self._event_bus = None
                self._auto_connect_config = None
                if logger:
                    logger.log("[AutoConnect] Disconnected from Kafka event bus")
