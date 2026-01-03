from __future__ import annotations

from pydantic import field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import (
    ModelSemVer,
    parse_semver_from_string,
)

"""
OnexOutputState model.
"""


from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel

from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.models.core.model_output_field import ModelOnexField

if TYPE_CHECKING:
    from omnibase_core.models.core.model_onex_internal_output_state import (
        ModelOnexInternalOutputState,
    )


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
    output_field: ModelOnexField | None = None
    event_id: UUID | None = None
    correlation_id: UUID | None = None
    node_name: str | None = None
    node_version: ModelSemVer | None = None
    timestamp: datetime | None = None

    @field_validator("version", mode="before")
    @classmethod
    def parse_output_version(cls, v: object) -> ModelSemVer:
        """Parse version from string, dict, or ModelSemVer"""
        if isinstance(v, ModelSemVer):
            return v
        if isinstance(v, str):
            return parse_semver_from_string(v)
        if isinstance(v, dict):
            return ModelSemVer(**v)
        msg = "version must be a string, dict, or ModelSemVer"
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=msg,
        )

    @field_validator("node_version", mode="before")
    @classmethod
    def parse_output_node_version(cls, v: object) -> ModelSemVer | None:
        """Parse node_version from string, dict, or ModelSemVer"""
        if v is None:
            return v
        if isinstance(v, ModelSemVer):
            return v
        if isinstance(v, str):
            return parse_semver_from_string(v)
        if isinstance(v, dict):
            return ModelSemVer(**v)
        msg = "node_version must be a string, dict, or ModelSemVer"
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=msg,
        )

    @field_validator("event_id", "correlation_id")
    @classmethod
    def validate_output_uuid_fields(cls, v: object) -> object:
        """Validate UUID fields - Pydantic handles UUID conversion automatically"""
        return v

    @field_validator("timestamp")
    @classmethod
    def validate_output_timestamp(cls, v: object) -> object:
        """Validate timestamp - Pydantic handles datetime conversion automatically"""
        return v

    @classmethod
    def from_internal_state(
        cls,
        internal_state: ModelOnexInternalOutputState,
    ) -> ModelOnexOutputState:
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


# Compatibility alias
OnexOutputState = ModelOnexOutputState
