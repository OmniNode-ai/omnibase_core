from typing import Any, Dict

from pydantic import Field

"""
Node introspection response model for ONEX nodes.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_node_capability import EnumNodeCapability
from omnibase_core.models.core.model_contract import ModelContract
from omnibase_core.models.core.model_dependencies import ModelDependencies
from omnibase_core.models.core.model_error_codes import ModelErrorCodes
from omnibase_core.models.core.model_event_channels import ModelEventChannels
from omnibase_core.models.core.model_node_introspection_response_config import (
    ModelNodeIntrospectionResponseConfig,
)
from omnibase_core.models.core.model_node_metadata_info import ModelNodeMetadataInfo
from omnibase_core.models.core.model_state_models import ModelStates


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
    introspection_version: str = Field(
        default="1.0.0",
        description="Introspection format version",
    )
