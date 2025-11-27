"""
Node Information Result Model.

Defines the structured result model for node information operations
within the ONEX architecture.
"""

from pydantic import Field

from omnibase_core.models.core.model_base_result import ModelBaseResult
from omnibase_core.models.core.model_node_data import ModelNodeData
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.utils.model_contract_data import ModelContractData


class ModelNodeInfoResult(ModelBaseResult):
    """
    Structured result model for node information operations.

    Contains the results of retrieving detailed information
    about specific ONEX nodes.
    """

    node_name: str = Field(default=..., description="Name of the node")
    node_version: ModelSemVer | None = Field(
        default=None, description="Version of the node"
    )
    node_data: ModelNodeData = Field(
        default_factory=lambda: ModelNodeData(),
        description="Node information data",
    )
    capabilities: list[str] = Field(
        default_factory=list,
        description="Node capabilities",
    )
    contract_data: ModelContractData | None = Field(
        default=None,
        description="Node contract information",
    )
    response_time_ms: float | None = Field(
        default=None,
        description="Node info retrieval time in milliseconds",
    )
    format: str = Field(
        default="dict[str, Any]", description="Format of the node info output"
    )
