"""
Internal Input State Model for ONEX.

This model is used for internal processing where UUIDs are guaranteed to exist
and are not Optional. This eliminates the need for null checking and fallback
logic throughout the internal processing pipeline.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.core.core_uuid_service import UUIDService
from omnibase_core.models.core.model_semver import ModelSemVer, parse_semver_from_string

if TYPE_CHECKING:
    from omnibase_core.models.core.model_onex_base_state import ModelOnexInputState


class ModelOnexInternalInputState(BaseModel):
    """
    Internal input state for ONEX processing with required UUIDs.

    This model is used for internal processing where all traceability fields
    are guaranteed to exist. It's created from boundary models but ensures
    all UUIDs are populated before processing begins.

    Use this model for internal functions where you need guaranteed UUID fields.
    """

    # Core required fields
    version: ModelSemVer

    # Required traceability fields (no Optional)
    event_id: UUID = Field(..., description="Required event ID for tracking")
    correlation_id: UUID = Field(
        ...,
        description="Required correlation ID for tracking",
    )
    timestamp: datetime = Field(..., description="Required timestamp for tracking")

    # Node identification (required for internal processing)
    node_name: str = Field(..., description="Required node name for processing")
    node_version: ModelSemVer = Field(
        ...,
        description="Required node version for processing",
    )

    @classmethod
    def from_boundary_state(
        cls,
        boundary_state: "ModelOnexInputState",
    ) -> "ModelOnexInternalInputState":
        """
        Create internal state from boundary state, ensuring all UUIDs are populated.

        This method handles the conversion from Optional UUID fields to required
        UUID fields by generating UUIDs where needed.

        Args:
            boundary_state: Input state from system boundary (may have Optional UUIDs)

        Returns:
            ModelOnexInternalInputState: Internal state with all required UUIDs populated
        """
        return cls(
            version=boundary_state.version,
            event_id=UUIDService.ensure_uuid(boundary_state.event_id),
            correlation_id=UUIDService.ensure_uuid(boundary_state.correlation_id),
            timestamp=boundary_state.timestamp or datetime.utcnow(),
            node_name=boundary_state.node_name or "unknown",
            node_version=boundary_state.node_version
            or parse_semver_from_string("1.0.0"),
        )
