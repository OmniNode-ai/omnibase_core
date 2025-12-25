from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.core.model_contract_metadata import ModelContractMetadata
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelGenericContract(BaseModel):
    """Generic contract model for ONEX tools.

    This model represents the standard structure of a contract.yaml file.
    It may be nested in other Pydantic models or used with pytest-xdist
    parallel test execution. The from_attributes=True setting ensures
    proper instance recognition across worker processes.
    """

    model_config = ConfigDict(from_attributes=True)

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
    input_state: dict[str, ModelSchemaValue] = Field(
        default=..., description="Input state schema"
    )
    output_state: dict[str, ModelSchemaValue] = Field(
        default=..., description="Output state schema"
    )
    definitions: dict[str, ModelSchemaValue] | None = Field(
        default=None,
        description="Shared schema definitions",
    )

    # Usage examples
    examples: dict[str, ModelSchemaValue] | None = Field(
        default=None,
        description="Usage examples for the tool",
    )
