"""
OnexEventMetadata model.
"""

# Forward reference to avoid circular imports
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from omnibase_core.model.core.model_semver import ModelSemVer


class ModelOnexEventMetadata(BaseModel):
    input_state: dict | None = None
    output_state: dict | None = None
    error: str | None = None
    error_type: str | None = None
    error_code: str | None = None
    recoverable: bool | None = None
    node_version: ModelSemVer | None = None
    operation_type: str | None = None
    execution_time_ms: float | None = None
    result_summary: str | None = None
    status: str | None = None
    reason: str | None = None
    registry_id: str | UUID | None = None
    trust_state: str | None = None
    ttl: int | None = None
    model_config = ConfigDict(extra="allow")

    @classmethod
    def from_node_announce(
        cls,
        announce: "NodeAnnounceModelMetadata",
    ) -> "OnexEventModelMetadata":
        """
        Construct an OnexEventModelMetadata from a NodeAnnounceModelMetadata, mapping all fields.
        """
        return cls(**announce.model_dump())
