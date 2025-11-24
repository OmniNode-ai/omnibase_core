from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.decorators import allow_dict_str_any
from omnibase_core.models.core.model_contract_metadata import ModelContractMetadata
from omnibase_core.models.primitives.model_semver import ModelSemVer


@allow_dict_str_any("input_state")
@allow_dict_str_any("output_state")
@allow_dict_str_any("definitions")
@allow_dict_str_any("examples")
class ModelGenericContract(BaseModel):
    """
    Generic contract model for ONEX tools.

    This model represents the standard structure of a contract.yaml file.
    """

    # Core contract fields
    contract_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Contract schema version",
    )
    node_name: str = Field(default=..., description="Name of the node/tool")
    node_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Version of the node/tool",
    )
    description: str | None = Field(
        default=None,
        description="Description of what this tool does",
    )

    # Optional metadata
    author: str | None = Field(
        default="ONEX System",
        description="Author of the tool",
    )
    tool_type: str | None = Field(
        default=None,
        description="Type of tool (generation, management, ai, etc.)",
    )
    created_at: str | None = Field(default=None, description="Creation timestamp")

    # Contract structure
    metadata: ModelContractMetadata | None = Field(
        default=None,
        description="Tool metadata and dependencies",
    )

    execution_modes: list[str] | None = Field(
        default=None,
        description="Supported execution modes",
    )

    # Schema definitions
    input_state: dict[str, Any] = Field(default=..., description="Input state schema")
    output_state: dict[str, Any] = Field(default=..., description="Output state schema")
    definitions: dict[str, Any] | None = Field(
        default=None,
        description="Shared schema definitions",
    )

    # Usage examples
    examples: dict[str, Any] | None = Field(
        default=None,
        description="Usage examples for the tool",
    )
