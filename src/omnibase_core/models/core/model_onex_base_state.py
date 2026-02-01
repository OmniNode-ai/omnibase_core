from pydantic import field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import (
    ModelSemVer,
    parse_semver_from_string,
)

from .model_onex_output_state import ModelOnexOutputState

__all__ = [
    "ModelOnexInputState",
    "ModelOnexOutputState",
]

OnexOutputState = ModelOnexOutputState

# === OmniNode:Metadata ===
# author: OmniNode Team
# description: Base state classes for all ONEX nodes with common fields and validators
# === /OmniNode:Metadata ===

"""
Base State Classes for ONEX Nodes

Provides ModelOnexInputState and OnexOutputState base classes that contain all common fields
and validators, dramatically simplifying auto-generated state.py files across all nodes.

This eliminates the need for custom output field models and reduces generated code
complexity by ~85% (from 100+ lines to ~15 lines per node).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from omnibase_core.models.core.model_onex_internal_input_state import (
    ModelOnexInternalInputState,
)


class ModelOnexInputState(BaseModel):
    """
    Base input state class for all ONEX nodes.

    Contains all common fields and validators that every node needs.
    Node-specific state classes should inherit from this and add only
    their specific input fields.
    """

    # Core required fields
    version: ModelSemVer

    # Standard traceability fields (ONEX standard)
    event_id: UUID | None = None
    correlation_id: UUID | None = None
    node_name: str | None = None
    node_version: ModelSemVer | None = None
    timestamp: datetime | None = None

    @field_validator("version", mode="before")
    @classmethod
    def parse_input_version(cls, v: object) -> ModelSemVer:
        """Parse version from string, dict, or ModelSemVer"""
        if isinstance(v, ModelSemVer):
            return v
        if isinstance(v, str):
            return parse_semver_from_string(v)
        if isinstance(v, dict):
            return ModelSemVer(**v)

        raise ModelOnexError(
            error_code=EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH,
            message="version must be a string, dict, or ModelSemVer",
        )

    @field_validator("node_version", mode="before")
    @classmethod
    def parse_input_node_version(cls, v: object) -> ModelSemVer | None:
        """Parse node_version from string, dict, or ModelSemVer"""
        if v is None:
            return v
        if isinstance(v, ModelSemVer):
            return v
        if isinstance(v, str):
            return parse_semver_from_string(v)
        if isinstance(v, dict):
            return ModelSemVer(**v)

        raise ModelOnexError(
            error_code=EnumCoreErrorCode.PARAMETER_TYPE_MISMATCH,
            message="node_version must be a string, dict, or ModelSemVer",
        )

    @field_validator("event_id", "correlation_id")
    @classmethod
    def validate_input_uuid_fields(cls, v: object) -> object:
        """Validate UUID fields - Pydantic handles UUID conversion automatically"""
        # Pydantic automatically converts string UUIDs to UUID objects
        # and validates format, so we just need to handle None
        return v

    @field_validator("timestamp")
    @classmethod
    def validate_input_timestamp(cls, v: object) -> object:
        """Validate timestamp - Pydantic handles datetime conversion automatically"""
        # Pydantic automatically converts ISO8601 strings to datetime objects
        # and validates format, so we just need to handle None
        return v

    def to_internal_state(self) -> ModelOnexInternalInputState:
        """
        Convert boundary input state to internal state with required UUIDs.

        This method handles the conversion from Optional UUID fields to required
        UUID fields by generating UUIDs where needed using the UUID service.

        Returns:
            ModelOnexInternalInputState: Internal state with all required UUIDs populated
        """
        return ModelOnexInternalInputState.from_boundary_state(self)
