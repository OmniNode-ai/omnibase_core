from .model_onex_output_state import ModelOnexOutputState

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
from typing import Any, cast
from uuid import UUID

from pydantic import BaseModel, field_validator

from omnibase_core.models.core.model_onex_internal_input_state import (
    ModelOnexInternalInputState,
)
from omnibase_core.models.core.model_semver import ModelSemVer


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
    def parse_input_version(cls, v: Any) -> ModelSemVer:
        """Parse version from string, dict, or ModelSemVer"""
        if isinstance(v, ModelSemVer):
            return v
        if isinstance(v, str):
            parts = v.split(".")
            if len(parts) == 3:
                return ModelSemVer(
                    major=int(parts[0]), minor=int(parts[1]), patch=int(parts[2])
                )
            raise ValueError(f"Invalid version string format: {v}")
        if isinstance(v, dict):
            return ModelSemVer(**v)
        msg = "version must be a string, dict, or ModelSemVer"
        raise ValueError(msg)

    @field_validator("node_version", mode="before")
    @classmethod
    def parse_input_node_version(cls, v: Any) -> ModelSemVer | None:
        """Parse node_version from string, dict, or ModelSemVer"""
        if v is None:
            return v
        if isinstance(v, ModelSemVer):
            return v
        if isinstance(v, str):
            parts = v.split(".")
            if len(parts) == 3:
                return ModelSemVer(
                    major=int(parts[0]), minor=int(parts[1]), patch=int(parts[2])
                )
            raise ValueError(f"Invalid version string format: {v}")
        if isinstance(v, dict):
            return ModelSemVer(**v)
        msg = "node_version must be a string, dict, or ModelSemVer"
        raise ValueError(msg)

    @field_validator("event_id", "correlation_id")
    @classmethod
    def validate_input_uuid_fields(cls, v: Any) -> UUID | None:
        """Validate UUID fields - Pydantic handles UUID conversion automatically"""
        # Pydantic automatically converts string UUIDs to UUID objects
        # and validates format, so we just need to handle None
        return v if (v is None or isinstance(v, UUID)) else None

    @field_validator("timestamp")
    @classmethod
    def validate_input_timestamp(cls, v: Any) -> datetime | None:
        """Validate timestamp - Pydantic handles datetime conversion automatically"""
        # Pydantic automatically converts ISO8601 strings to datetime objects
        # and validates format, so we just need to handle None
        return v if (v is None or isinstance(v, datetime)) else None

    def to_internal_state(self) -> ModelOnexInternalInputState:
        """
        Convert boundary input state to internal state with required UUIDs.

        This method handles the conversion from Optional UUID fields to required
        UUID fields by generating UUIDs where needed using the UUID service.

        Returns:
            ModelOnexInternalInputState: Internal state with all required UUIDs populated
        """
        from omnibase_core.models.core.model_onex_internal_state import (
            ModelOnexInternalInputState as InternalInputState,
        )

        return cast(
            ModelOnexInternalInputState, InternalInputState.from_boundary_state(self)
        )
