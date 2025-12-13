"""
Node introspection response model for ONEX nodes.
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_node_capability import EnumNodeCapability
from omnibase_core.models.core.model_contract import ModelContract
from omnibase_core.models.core.model_dependencies import ModelDependencies
from omnibase_core.models.core.model_error_codes import ModelErrorCodes
from omnibase_core.models.core.model_event_channels import ModelEventChannels
from omnibase_core.models.core.model_state_models import ModelStates
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.node_metadata.model_node_metadata_info import (
    ModelNodeMetadataInfo,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelNodeIntrospectionResponse(BaseModel):
    """
    Canonical response model for ONEX node introspection.

    This is the standardized format that all ONEX nodes must return
    when called with the --introspect command.
    """

    node_metadata: ModelNodeMetadataInfo = Field(
        default=...,
        description="Node metadata and identification",
    )
    contract: ModelContract = Field(
        default=...,
        description="Node contract and interface specification",
    )
    state_models: ModelStates = Field(
        default=...,
        description="Input and output state model specifications",
    )
    error_codes: ModelErrorCodes = Field(
        default=...,
        description="Error codes and exit code mapping",
    )
    dependencies: ModelDependencies = Field(
        default=...,
        description="Runtime and optional dependencies",
    )
    capabilities: list[EnumNodeCapability] = Field(
        default_factory=list,
        description="Node capabilities",
    )
    event_channels: ModelEventChannels | None = Field(
        default=None,
        description="Event channels this node subscribes to and publishes to",
    )
    introspection_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Introspection format version",
    )

    @field_validator("introspection_version", mode="before")
    @classmethod
    def validate_introspection_version(cls, v: Any) -> ModelSemVer:
        """Validate and convert introspection_version to ModelSemVer."""
        if isinstance(v, ModelSemVer):
            return v
        if isinstance(v, dict):
            return ModelSemVer(**v)
        if isinstance(v, str):
            from omnibase_core.models.primitives.model_semver import (
                parse_semver_from_string,
            )

            return parse_semver_from_string(v)
        msg = "introspection_version must be ModelSemVer, dict, or str"
        raise ModelOnexError(message=msg, error_code=EnumCoreErrorCode.VALIDATION_ERROR)
