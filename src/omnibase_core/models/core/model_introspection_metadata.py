"""
Model for complete introspection metadata.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_introspection_contract_info import (
    ModelIntrospectionContractInfo,
)
from omnibase_core.models.core.model_introspection_node_info import (
    ModelIntrospectionNodeInfo,
)
from omnibase_core.models.core.model_introspection_runtime_info import (
    ModelIntrospectionRuntimeInfo,
)
from omnibase_core.models.core.model_introspection_validation import (
    ModelIntrospectionValidation,
)


class ModelIntrospectionMetadata(BaseModel):
    """Complete introspection metadata for a tool."""

    node_info: ModelIntrospectionNodeInfo = Field(description="Node information")
    capabilities: dict[str, bool] = Field(description="Tool capabilities")
    contract_info: ModelIntrospectionContractInfo = Field(
        description="Contract information",
    )
    runtime_info: ModelIntrospectionRuntimeInfo = Field(
        description="Runtime information",
    )
    dependencies: dict[str, list[str]] = Field(description="Tool dependencies")
    validation: ModelIntrospectionValidation = Field(
        description="Validation information",
    )
