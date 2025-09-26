"""
Workflow Node Model - ONEX Standards Compliant.

Model for node definitions in workflow graphs for the ONEX workflow coordination system.
"""

from typing import Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_node_type import EnumNodeType

# Type aliases for structured data - ZERO TOLERANCE for Any types
ParameterValue = Union[str, int, float, bool, None]
StructuredData = dict[str, ParameterValue]


class ModelWorkflowNode(BaseModel):
    """A node definition in a workflow graph."""

    node_id: UUID = Field(
        default_factory=uuid4, description="Unique identifier for the node"
    )

    node_type: EnumNodeType = Field(..., description="Type of the node")

    node_requirements: StructuredData = Field(
        default_factory=dict, description="Requirements for this node"
    )

    dependencies: list[UUID] = Field(
        default_factory=list, description="List of node IDs this node depends on"
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
