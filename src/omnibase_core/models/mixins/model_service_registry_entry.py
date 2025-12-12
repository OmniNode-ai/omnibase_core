import time
from typing import Any
from uuid import UUID


class ModelServiceRegistryEntry:
    """Registry entry for a discovered service/tool."""

    def __init__(
        self,
        node_id: UUID,
        service_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.node_id = node_id
        self.service_name = service_name
        self.metadata = metadata or {}
        self.registered_at = time.time()
        self.last_seen = time.time()
        self.status = "online"
        self.capabilities: list[str] = []
        self.introspection_data: dict[str, Any] | None = None

    def update_last_seen(self) -> None:
        """Update the last seen timestamp."""
        self.last_seen = time.time()

    def set_offline(self) -> None:
        """Mark service as offline."""
        self.status = "offline"

    def update_introspection(self, introspection_data: dict[str, Any]) -> None:
        """Update with introspection data."""
        self.introspection_data = introspection_data
        self.capabilities = introspection_data.get("capabilities", [])
        self.metadata.update(introspection_data.get("metadata", {}))
