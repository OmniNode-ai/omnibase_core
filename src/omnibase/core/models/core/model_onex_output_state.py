"""
OnexOutputState model.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, field_validator

from omnibase.core.models.model_semver import ModelSemVer
from omnibase.enums.enum_onex_status import EnumOnexStatus
from omnibase.model.core.model_output_field import ModelOnexField


class ModelOnexOutputState(BaseModel):
    """
    Base output state class for all ONEX nodes.

    Contains all common output fields including the standardized output_field
    that uses ModelOnexField for all node-specific output data.

    Node-specific state classes should inherit from this and typically
    don't need to add any additional fields (everything goes in output_field.data).
    """

    version: ModelSemVer
    status: EnumOnexStatus
    message: str
    output_field: Optional[ModelOnexField] = None
    event_id: Optional[UUID] = None
    correlation_id: Optional[UUID] = None
    node_name: Optional[str] = None
    node_version: Optional[ModelSemVer] = None
    timestamp: Optional[datetime] = None

    @field_validator("version", mode="before")
    @classmethod
    def parse_output_version(cls, v):
        """Parse version from string, dict, or ModelSemVer"""
        if isinstance(v, ModelSemVer):
            return v
        if isinstance(v, str):
            return ModelSemVer.parse(v)
        if isinstance(v, dict):
            return ModelSemVer(**v)
        raise ValueError("version must be a string, dict, or ModelSemVer")

    @field_validator("node_version", mode="before")
    @classmethod
    def parse_output_node_version(cls, v):
        """Parse node_version from string, dict, or ModelSemVer"""
        if v is None:
            return v
        if isinstance(v, ModelSemVer):
            return v
        if isinstance(v, str):
            return ModelSemVer.parse(v)
        if isinstance(v, dict):
            return ModelSemVer(**v)
        raise ValueError("node_version must be a string, dict, or ModelSemVer")

    @field_validator("event_id", "correlation_id")
    @classmethod
    def validate_output_uuid_fields(cls, v):
        """Validate UUID fields - Pydantic handles UUID conversion automatically"""
        return v

    @field_validator("timestamp")
    @classmethod
    def validate_output_timestamp(cls, v):
        """Validate timestamp - Pydantic handles datetime conversion automatically"""
        return v

    @classmethod
    def from_internal_state(
        cls, internal_state: "ModelOnexInternalOutputState"
    ) -> "ModelOnexOutputState":
        """
        Create boundary output state from internal state.

        This method handles the conversion from required UUID fields back to
        Optional UUID fields for external APIs that expect the boundary model.

        Args:
            internal_state: Internal state with required UUIDs

        Returns:
            ModelOnexOutputState: Boundary state suitable for external consumption
        """
        return cls(
            version=internal_state.version,
            status=internal_state.status,
            message=internal_state.message,
            output_field=getattr(internal_state, "output_field", None),
            event_id=internal_state.event_id,
            correlation_id=internal_state.correlation_id,
            node_name=internal_state.node_name,
            node_version=internal_state.node_version,
            timestamp=internal_state.timestamp,
        )


# Backward compatibility alias
OnexOutputState = ModelOnexOutputState
