"""WebSocket Manager Utility

Handles WebSocket connection management and real-time broadcasting.
Follows ONEX utility patterns with strong typing and single responsibility.
"""

import json
from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.models.model_websocket_config import ModelWebSocketConfig
from omnibase_core.models.model_websocket_message_data import ModelWebSocketMessageData

try:
    from fastapi import WebSocket, WebSocketDisconnect

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    WebSocket = None
    WebSocketDisconnect = None


class ModelWebSocketMessage(BaseModel):
    """Model for WebSocket messages."""

    message_type: str = Field(
        description="Type of message (capture, hook_event, stats, etc.)",
    )
    data: ModelWebSocketMessageData = Field(description="Message payload data")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Message creation timestamp",
    )


class ModelConnectionStats(BaseModel):
    """Model for WebSocket connection statistics."""

    active_connections: int = Field(description="Number of active connections")
    total_connections: int = Field(description="Total connections since start")
    messages_sent: int = Field(description="Total messages broadcast")
    send_errors: int = Field(description="Number of send errors")
    disconnections: int = Field(description="Number of disconnections")


class UtilityWebSocketManager:
    """WebSocket connection management utility.

    Responsibilities:
    - Connection lifecycle management
    - Real-time event broadcasting
    - Client connection tracking
    - Message serialization and delivery
    """

    def __init__(self):
        """Initialize WebSocket manager."""
        if not FASTAPI_AVAILABLE:
            self.enabled = False
            return

        # Connection management
        self.active_connections: list[WebSocket] = []
        self.enabled = True

        # Statistics tracking
        self._total_connections = 0
        self._messages_sent = 0
        self._send_errors = 0
        self._disconnections = 0

    async def add_connection(self, websocket: WebSocket) -> bool:
        """Add a new WebSocket connection.

        Args:
            websocket: WebSocket connection to add

        Returns:
            True if connection added successfully
        """
        if not self.enabled:
            return False

        try:
            await websocket.accept()
            self.active_connections.append(websocket)
            self._total_connections += 1

            return True

        except Exception:
            return False

    def remove_connection(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection.

        Args:
            websocket: WebSocket connection to remove
        """
        if not self.enabled:
            return

        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self._disconnections += 1

    async def broadcast_message(
        self,
        message_type: str,
        data,  # Accept either ModelWebSocketMessageData or dict
        exclude_connection: WebSocket | None = None,
    ) -> int:
        """Broadcast a message to all connected clients.

        Args:
            message_type: Type of message being sent
            data: Message payload data
            exclude_connection: Optional connection to exclude from broadcast

        Returns:
            Number of successful sends
        """
        if not self.enabled or not self.active_connections:
            return 0

        # Prepare payload (support Pydantic models and plain dicts)
        try:
            if hasattr(data, "model_dump"):
                payload_data = data.model_dump(exclude_none=True, mode="json")
            elif isinstance(data, dict):
                payload_data = data
            else:
                # Best-effort fallback
                payload_data = getattr(data, "__dict__", {})
        except Exception:
            payload_data = {}

        message_json = json.dumps(
            {
                "type": message_type,
                "data": payload_data,
                "timestamp": datetime.now().isoformat(),
            },
        )

        # Send to all connections
        successful_sends = 0
        disconnected_connections = []

        for connection in self.active_connections:
            if exclude_connection and connection == exclude_connection:
                continue

            try:
                await connection.send_text(message_json)
                successful_sends += 1

            except Exception:
                disconnected_connections.append(connection)
                self._send_errors += 1

        # Clean up disconnected connections
        for conn in disconnected_connections:
            self.remove_connection(conn)

        self._messages_sent += successful_sends

        if successful_sends > 0:
            pass

        return successful_sends

    async def send_to_connection(
        self,
        websocket: WebSocket,
        message_type: str,
        data,
    ) -> bool:
        """Send a message to a specific connection.

        Args:
            websocket: Target WebSocket connection
            message_type: Type of message being sent
            data: Message payload data

        Returns:
            True if sent successfully
        """
        if not self.enabled:
            return False

        try:
            # Prepare payload (support Pydantic models and plain dicts)
            if hasattr(data, "model_dump"):
                payload_data = data.model_dump(exclude_none=True, mode="json")
            elif isinstance(data, dict):
                payload_data = data
            else:
                payload_data = getattr(data, "__dict__", {})

            message_json = json.dumps(
                {
                    "type": message_type,
                    "data": payload_data,
                    "timestamp": datetime.now().isoformat(),
                },
            )

            await websocket.send_text(message_json)
            self._messages_sent += 1
            return True

        except Exception:
            self._send_errors += 1
            return False

    async def broadcast_capture_event(
        self,
        capture_data: ModelWebSocketMessageData,
    ) -> int:
        """Broadcast a tool capture event.

        Args:
            capture_data: Tool capture data to broadcast

        Returns:
            Number of successful sends
        """
        return await self.broadcast_message("capture", capture_data)

    async def broadcast_hook_event(self, hook_data: ModelWebSocketMessageData) -> int:
        """Broadcast a hook event.

        Args:
            hook_data: Hook event data to broadcast

        Returns:
            Number of successful sends
        """
        return await self.broadcast_message("hook_event", hook_data)

    async def broadcast_stats_update(
        self,
        stats_data: ModelWebSocketMessageData,
    ) -> int:
        """Broadcast statistics update.

        Args:
            stats_data: Statistics data to broadcast

        Returns:
            Number of successful sends
        """
        return await self.broadcast_message("stats", stats_data)

    async def send_initial_state(
        self,
        websocket: WebSocket,
        initial_data: ModelWebSocketMessageData,
    ) -> bool:
        """Send initial state to a newly connected client.

        Args:
            websocket: WebSocket connection for new client
            initial_data: Initial state data to send

        Returns:
            True if sent successfully
        """
        return await self.send_to_connection(websocket, "connected", initial_data)

    async def handle_connection_lifecycle(
        self,
        websocket: WebSocket,
        initial_data: ModelWebSocketMessageData | None = None,
    ) -> None:
        """Handle complete WebSocket connection lifecycle.

        Args:
            websocket: WebSocket connection to manage
            initial_data: Optional initial data to send
        """
        if not self.enabled:
            return

        # Add connection
        if not await self.add_connection(websocket):
            return

        try:
            # Send initial state if provided
            if initial_data:
                await self.send_initial_state(websocket, initial_data)

            # Keep connection alive
            while True:
                try:
                    # Wait for messages (ping/pong)
                    await websocket.receive_text()
                except Exception:
                    break

        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            # Ensure connection is cleaned up
            self.remove_connection(websocket)

    def get_connection_stats(self) -> ModelConnectionStats:
        """Get WebSocket connection statistics.

        Returns:
            Current connection statistics
        """
        return ModelConnectionStats(
            active_connections=len(self.active_connections) if self.enabled else 0,
            total_connections=self._total_connections,
            messages_sent=self._messages_sent,
            send_errors=self._send_errors,
            disconnections=self._disconnections,
        )

    def get_active_connection_count(self) -> int:
        """Get count of active connections.

        Returns:
            Number of active WebSocket connections
        """
        return len(self.active_connections) if self.enabled else 0

    def is_enabled(self) -> bool:
        """Check if WebSocket manager is enabled.

        Returns:
            True if WebSocket functionality is available
        """
        return self.enabled

    def cleanup_stale_connections(self) -> int:
        """Clean up any stale or broken connections.

        Returns:
            Number of connections cleaned up
        """
        if not self.enabled:
            return 0

        stale_connections = []

        for connection in self.active_connections:
            try:
                # Try to check connection state (this is platform-specific)
                # For now, we'll rely on send failures to detect stale connections
                pass
            except Exception:
                stale_connections.append(connection)

        # Remove stale connections
        for conn in stale_connections:
            self.remove_connection(conn)

        if stale_connections:
            pass

        return len(stale_connections)

    def get_configuration(self) -> ModelWebSocketConfig:
        """Get WebSocket manager configuration.

        Returns:
            Configuration model
        """
        return ModelWebSocketConfig(
            enabled=self.enabled,
            fastapi_available=FASTAPI_AVAILABLE,
            active_connections=len(self.active_connections) if self.enabled else 0,
            max_connections="unlimited",  # Could be configurable
        )
