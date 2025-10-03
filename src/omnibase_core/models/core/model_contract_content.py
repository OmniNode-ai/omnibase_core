"""Contract content model for ContractLoader."""

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.models.metadata.model_semver import ModelSemVer


class ModelContractContent(BaseModel):
    """Parsed contract content structure."""

    contract_version: ModelSemVer = Field(description="Contract version")
    node_name: str = Field(description="Node name")
    node_type: EnumNodeType = Field(description="Node type")
    tool_specification: "ModelToolSpecification" = Field(
        description="Tool specification"
    )
    input_state: "ModelYamlSchemaObject" = Field(description="Input state schema")
    output_state: "ModelYamlSchemaObject" = Field(description="Output state schema")
    definitions: "ModelContractDefinitions" = Field(description="Contract definitions")
    dependencies: list[Any] | None = Field(
        default=None, description="Contract dependencies"
    )

    model_config = {
        "arbitrary_types_allowed": True,
    }


# Import here to avoid circular dependency
from omnibase_core.models.core.model_contract_definitions import (
    ModelContractDefinitions,
)
from omnibase_core.models.core.model_tool_specification import ModelToolSpecification
from omnibase_core.models.core.model_yaml_schema_object import ModelYamlSchemaObject

ModelContractContent.model_rebuild()
