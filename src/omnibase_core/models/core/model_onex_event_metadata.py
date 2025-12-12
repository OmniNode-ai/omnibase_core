"""
OnexEventMetadata model.
"""

from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types.type_serializable_value import SerializedDict

if TYPE_CHECKING:
    from omnibase_core.models.core.model_node_announce_metadata import (
        ModelNodeAnnounceMetadata,
    )


class ModelOnexEventMetadata(BaseModel):
    input_state: SerializedDict | None = None
    output_state: SerializedDict | None = None
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
        announce: "ModelNodeAnnounceMetadata",
    ) -> "ModelOnexEventMetadata":
        """
        Construct an ModelOnexEventMetadata from a NodeAnnounceModelMetadata, mapping all fields.
        """
        return cls(**announce.model_dump())
