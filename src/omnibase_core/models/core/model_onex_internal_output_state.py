"""
Internal Output State Model for ONEX.

This model is used for internal processing where UUIDs are guaranteed to exist
and are not Optional. This eliminates the need for null checking and fallback
logic throughout the internal processing pipeline.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_onex_status import EnumOnexStatus

# Import for boundary state conversion
from omnibase_core.models.core.model_onex_output_state import ModelOnexOutputState
from omnibase_core.models.core.model_output_field import ModelOnexField
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelOnexInternalOutputState(BaseModel):
    """
    Internal output state for ONEX processing with required UUIDs.

    This model is used for internal processing where all traceability fields
    are guaranteed to exist. It ensures consistent UUID tracking throughout
    the processing pipeline.

    Use this model for internal functions where you need guaranteed UUID fields.
    """

    # Core required fields
    version: ModelSemVer

    # Required traceability fields (no Optional)
    event_id: UUID = Field(default=..., description="Required event ID for tracking")
    correlation_id: UUID = Field(
        default=...,
        description="Required correlation ID for tracking",
    )
    timestamp: datetime = Field(
        default=..., description="Required timestamp for tracking"
    )

    # Node identification (required for internal processing)
    node_name: str = Field(default=..., description="Required node name for processing")
    node_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Node version for processing (defaults to 1.0.0 if not provided)",
    )

    # Processing results
    status: EnumOnexStatus = Field(default=..., description="Processing status")
    message: str = Field(default=..., description="Processing message")
    output_field: ModelOnexField | None = Field(
        default=None,
        description="Output field with processing results",
    )

    def to_boundary_state(self) -> "ModelOnexOutputState":
        """
        Convert internal state to boundary state for external consumption.

        This method handles the conversion from required UUID fields back to
        Optional UUID fields for external APIs that expect the boundary model.

        Returns:
            ModelOnexOutputState: Boundary state suitable for external consumption
        """
        # Import here to avoid circular imports
        from omnibase_core.models.core.model_onex_base_state import ModelOnexOutputState

        return ModelOnexOutputState(
            version=self.version,
            status=self.status,
            message=self.message,
            output_field=self.output_field,
            event_id=self.event_id,
            correlation_id=self.correlation_id,
            node_name=self.node_name,
            node_version=self.node_version,
            timestamp=self.timestamp,
        )
