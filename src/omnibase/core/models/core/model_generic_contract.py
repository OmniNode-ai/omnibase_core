"""
Generic contract model that matches the standard ONEX contract.yaml structure.

This model can be used to load and validate any ONEX tool contract.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from omnibase.core.models.model_semver import ModelSemVer
from omnibase.decorators import allow_dict_str_any


class ModelContractMetadata(BaseModel):
    """Metadata section of the contract."""

    dependencies: Optional[Dict[str, List[str]]] = Field(
        default=None, description="Tool dependencies"
    )
    related_docs: Optional[Dict[str, List[str]]] = Field(
        default=None, description="Related documentation"
    )
    consumers: Optional[Dict[str, List[str]]] = Field(
        default=None, description="Known consumers of this tool"
    )


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
    contract_version: ModelSemVer = Field(..., description="Contract schema version")
    node_name: str = Field(..., description="Name of the node/tool")
    node_version: ModelSemVer = Field(..., description="Version of the node/tool")
    description: Optional[str] = Field(
        default=None, description="Description of what this tool does"
    )

    # Optional metadata
    author: Optional[str] = Field(
        default="ONEX System", description="Author of the tool"
    )
    tool_type: Optional[str] = Field(
        default=None, description="Type of tool (generation, management, ai, etc.)"
    )
    created_at: Optional[str] = Field(default=None, description="Creation timestamp")

    # Contract structure
    metadata: Optional[ModelContractMetadata] = Field(
        default=None, description="Tool metadata and dependencies"
    )

    execution_modes: Optional[List[str]] = Field(
        default=None, description="Supported execution modes"
    )

    # Schema definitions
    input_state: Dict[str, Any] = Field(..., description="Input state schema")
    output_state: Dict[str, Any] = Field(..., description="Output state schema")
    definitions: Optional[Dict[str, Any]] = Field(
        default=None, description="Shared schema definitions"
    )

    # Usage examples
    examples: Optional[Dict[str, Any]] = Field(
        default=None, description="Usage examples for the tool"
    )

    class Config:
        """Pydantic configuration."""

        extra = "allow"  # Allow additional fields for extensibility
