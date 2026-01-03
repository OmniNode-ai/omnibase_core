import time
from uuid import UUID

from omnibase_core.types.type_serializable_value import SerializedDict


class ModelServiceRegistryEntry:
    """Registry entry for a discovered service/tool."""

    def __init__(
        self,
        node_id: UUID,
        service_name: str,
        metadata: SerializedDict | None = None,
    ) -> None:
        self.node_id = node_id
        self.service_name = service_name
        self.metadata: SerializedDict = metadata or {}
        self.registered_at = time.time()
        self.last_seen = time.time()
        self.status = "online"
        self.capabilities: list[str] = []
        self.introspection_data: SerializedDict | None = None

    def update_last_seen(self) -> None:
        """Update the last seen timestamp."""
        self.last_seen = time.time()

    def set_offline(self) -> None:
        """Mark service as offline."""
        self.status = "offline"

    def update_introspection(self, introspection_data: SerializedDict) -> None:
        """Update with introspection data."""
        self.introspection_data = introspection_data
        capabilities = introspection_data.get("capabilities")
        if isinstance(capabilities, list):
            # Type narrow: ensure all items are strings
            self.capabilities = [str(c) for c in capabilities]
        else:
            self.capabilities = []
        metadata_update = introspection_data.get("metadata")
        if isinstance(metadata_update, dict):
            self.metadata.update(metadata_update)
