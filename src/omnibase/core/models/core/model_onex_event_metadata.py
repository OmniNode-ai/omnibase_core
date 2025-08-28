"""
OnexEventMetadata model.
"""

# Forward reference to avoid circular imports
from typing import TYPE_CHECKING, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from omnibase.core.models.model_semver import ModelSemVer

if TYPE_CHECKING:
    from omnibase.model.core.model_log_entry import ModelLogEntry


class ModelOnexEventMetadata(BaseModel):
    input_state: Optional[dict] = None
    output_state: Optional[dict] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    error_code: Optional[str] = None
    recoverable: Optional[bool] = None
    node_version: Optional[ModelSemVer] = None
    operation_type: Optional[str] = None
    execution_time_ms: Optional[float] = None
    result_summary: Optional[str] = None
    status: Optional[str] = None
    reason: Optional[str] = None
    registry_id: Optional[Union[str, UUID]] = None
    trust_state: Optional[str] = None
    ttl: Optional[int] = None
    # Structured logging support
    log_entry: Optional["ModelLogEntry"] = None
    model_config = ConfigDict(extra="allow")

    @classmethod
    def from_node_announce(
        cls, announce: "NodeAnnounceModelMetadata"
    ) -> "OnexEventModelMetadata":
        """
        Construct an OnexEventModelMetadata from a NodeAnnounceModelMetadata, mapping all fields.
        """
        return cls(**announce.model_dump())
